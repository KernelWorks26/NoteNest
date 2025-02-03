import sys
import sqlite3
import os
import pickle
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QListWidget, QMessageBox, QLabel
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

# Google Drive authentication and service setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDS = None

def authenticate_google_drive():
    global CREDS
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            CREDS = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not CREDS or not CREDS.valid:
        if CREDS and CREDS.expired and CREDS.refresh_token:
            CREDS.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            CREDS = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(CREDS, token)

    try:
        # Build the Drive API client
        service = build('drive', 'v3', credentials=CREDS)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')

# Google Drive file upload function
def upload_file_to_drive(file_path, file_name):
    service = authenticate_google_drive()
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype='application/text')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File ID: {file["id"]}')
    return file["id"]

class TuxNote(QWidget):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.setWindowTitle("TuxNote - Open Source Note Taking with Google Drive Sync")
        self.setGeometry(100, 100, 700, 500)

        # Layout
        self.layout = QVBoxLayout()

        # Notes List
        self.label = QLabel("Saved Notes:")
        self.note_list = QListWidget()

        # Text Editor
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText("Type your notes here...")

        # Buttons
        self.save_button = QPushButton("Save Note")
        self.sync_button = QPushButton("Sync with Google Drive")
        self.delete_button = QPushButton("Delete Note")
        self.clear_button = QPushButton("New Note")

        # Add Widgets to Layout
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.note_list)
        self.layout.addWidget(self.text_editor)
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.sync_button)
        self.layout.addWidget(self.delete_button)
        self.layout.addWidget(self.clear_button)

        self.setLayout(self.layout)

        # Database setup
        self.db_connect()
        self.load_notes()

        # Event Listeners
        self.save_button.clicked.connect(self.save_note)
        self.sync_button.clicked.connect(self.sync_to_drive)
        self.delete_button.clicked.connect(self.delete_note)
        self.clear_button.clicked.connect(self.new_note)
        self.note_list.itemClicked.connect(self.load_selected_note)

    def db_connect(self):
        """Connect to SQLite database and create table if not exists"""
        self.conn = sqlite3.connect("notes.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                content TEXT
            )
        """)
        self.conn.commit()

    def load_notes(self):
        """Load notes from the database into the list"""
        self.note_list.clear()
        self.cursor.execute("SELECT title FROM notes")
        for note in self.cursor.fetchall():
            self.note_list.addItem(note[0])

    def save_note(self):
        """Save or update a note in the database"""
        note_title = self.text_editor.toPlainText().split("\n")[0]  # First line as title
        note_content = self.text_editor.toPlainText()

        if note_title.strip() == "":
            QMessageBox.warning(self, "Error", "Note title cannot be empty!")
            return

        try:
            self.cursor.execute("INSERT OR REPLACE INTO notes (title, content) VALUES (?, ?)", (note_title, note_content))
            self.conn.commit()
            self.load_notes()
            QMessageBox.information(self, "Success", "Note saved successfully!")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "A note with this title already exists!")

    def sync_to_drive(self):
        """Sync the current note to Google Drive"""
        note_title = self.text_editor.toPlainText().split("\n")[0]
        note_content = self.text_editor.toPlainText()

        if note_title.strip() == "":
            QMessageBox.warning(self, "Error", "Note title cannot be empty!")
            return

        # Save the note temporarily as a text file
        temp_file = f"{note_title}.txt"
        with open(temp_file, 'w') as file:
            file.write(note_content)

        # Upload to Google Drive
        try:
            file_id = upload_file_to_drive(temp_file, note_title)
            QMessageBox.information(self, "Sync Success", f"Note synced to Google Drive with ID {file_id}!")
            os.remove(temp_file)
        except Exception as e:
            QMessageBox.warning(self, "Sync Error", f"Failed to sync to Google Drive: {str(e)}")

    def load_selected_note(self):
        """Load selected note into editor"""
        selected_item = self.note_list.currentItem()
        if selected_item:
            note_title = selected_item.text()
            self.cursor.execute("SELECT content FROM notes WHERE title = ?", (note_title,))
            note_content = self.cursor.fetchone()
            if note_content:
                self.text_editor.setText(note_content[0])

    def delete_note(self):
        """Delete selected note"""
        selected_item = self.note_list.currentItem()
        if selected_item:
            note_title = selected_item.text()
            confirm = QMessageBox.question(self, "Delete", f"Are you sure you want to delete '{note_title}'?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                self.cursor.execute("DELETE FROM notes WHERE title = ?", (note_title,))
                self.conn.commit()
                self.load_notes()
                self.text_editor.clear()
                QMessageBox.information(self, "Success", "Note deleted successfully!")

    def new_note(self):
        """Clear the text editor for a new note"""
        self.text_editor.clear()

    def closeEvent(self, event):
        """Close database connection when exiting"""
        self.conn.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TuxNote()
    window.show()
    sys.exit(app.exec())
