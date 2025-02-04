import sys
import sqlite3
import os
import pickle
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QListWidget, QMessageBox, QLabel,
    QTabWidget, QMenuBar, QStatusBar, QFileDialog, QInputDialog, QMainWindow, QMenu
)
from PyQt6.QtGui import QAction, QTextDocument, QTextCursor, QTextCharFormat, QColor
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# Google Drive authentication and service setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDS = None

def authenticate_google_drive():
    global CREDS
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            CREDS = pickle.load(token)
    if not CREDS or not CREDS.valid:
        if CREDS and CREDS.expired and CREDS.refresh_token:
            CREDS.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            CREDS = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(CREDS, token)

    try:
        service = build('drive', 'v3', credentials=CREDS)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')

def upload_file_to_drive(file_path, file_name):
    service = authenticate_google_drive()
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype='application/text')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File ID: {file["id"]}')
    return file["id"]

class TuxNote(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.setWindowTitle("TuxNote - Open Source Note Taking with Google Drive Sync")
        self.setGeometry(100, 100, 800, 600)

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout
        self.layout = QVBoxLayout(self.central_widget)

        # Menu Bar
        self.create_menu_bar()

        # Tab Widget
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Notes Tab
        self.notes_tab = QWidget()
        self.notes_layout = QVBoxLayout(self.notes_tab)
        self.tabs.addTab(self.notes_tab, "Notes")

        # Notes List
        self.label = QLabel("Saved Notes:")
        self.note_list = QListWidget()
        self.notes_layout.addWidget(self.label)
        self.notes_layout.addWidget(self.note_list)

        # Text Editor
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText("Type your notes here...")
        self.notes_layout.addWidget(self.text_editor)

        # Buttons
        self.save_button = QPushButton("Save Note")
        self.sync_button = QPushButton("Sync with Google Drive")
        self.delete_button = QPushButton("Delete Note")
        self.clear_button = QPushButton("New Note")
        self.export_button = QPushButton("Export as PDF")
        self.search_button = QPushButton("Search Notes")

        # Add Buttons to Layout
        self.notes_layout.addWidget(self.save_button)
        self.notes_layout.addWidget(self.sync_button)
        self.notes_layout.addWidget(self.delete_button)
        self.notes_layout.addWidget(self.clear_button)
        self.notes_layout.addWidget(self.export_button)
        self.notes_layout.addWidget(self.search_button)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Database setup
        self.db_connect()
        self.load_notes()

        # Event Listeners
        self.save_button.clicked.connect(self.save_note)
        self.sync_button.clicked.connect(self.sync_to_drive)
        self.delete_button.clicked.connect(self.delete_note)
        self.clear_button.clicked.connect(self.new_note)
        self.note_list.itemClicked.connect(self.load_selected_note)
        self.export_button.clicked.connect(self.export_pdf)
        self.search_button.clicked.connect(self.search_notes)

        # Apply Stylesheet
        self.apply_stylesheet()

    def create_menu_bar(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("File")
        new_note_action = QAction("New Note", self)
        new_note_action.triggered.connect(self.new_note)
        file_menu.addAction(new_note_action)

        save_note_action = QAction("Save Note", self)
        save_note_action.triggered.connect(self.save_note)
        file_menu.addAction(save_note_action)

        export_pdf_action = QAction("Export as PDF", self)
        export_pdf_action.triggered.connect(self.export_pdf)
        file_menu.addAction(export_pdf_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("Edit")
        search_action = QAction("Search Notes", self)
        search_action.triggered.connect(self.search_notes)
        edit_menu.addAction(search_action)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                font-size: 14px;
            }
            QLabel {
                font-size: 16px;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
            }
            QTabBar::tab {
                background: #f0f0f0;
                padding: 10px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
            }
        """)

    def db_connect(self):
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
        self.note_list.clear()
        self.cursor.execute("SELECT title FROM notes")
        for note in self.cursor.fetchall():
            self.note_list.addItem(note[0])

    def save_note(self):
        note_title = self.text_editor.toPlainText().split("\n")[0]
        note_content = self.text_editor.toPlainText()

        if note_title.strip() == "":
            QMessageBox.warning(self, "Error", "Note title cannot be empty!")
            return

        try:
            self.cursor.execute("INSERT OR REPLACE INTO notes (title, content) VALUES (?, ?)", (note_title, note_content))
            self.conn.commit()
            self.load_notes()
            self.status_bar.showMessage("Note saved successfully!", 3000)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "A note with this title already exists!")

    def sync_to_drive(self):
        note_title = self.text_editor.toPlainText().split("\n")[0]
        note_content = self.text_editor.toPlainText()

        if note_title.strip() == "":
            QMessageBox.warning(self, "Error", "Note title cannot be empty!")
            return

        temp_file = f"{note_title}.txt"
        with open(temp_file, 'w') as file:
            file.write(note_content)

        try:
            file_id = upload_file_to_drive(temp_file, note_title)
            self.status_bar.showMessage(f"Note synced to Google Drive with ID {file_id}!", 3000)
            os.remove(temp_file)
        except Exception as e:
            QMessageBox.warning(self, "Sync Error", f"Failed to sync to Google Drive: {str(e)}")

    def load_selected_note(self):
        selected_item = self.note_list.currentItem()
        if selected_item:
            note_title = selected_item.text()
            self.cursor.execute("SELECT content FROM notes WHERE title = ?", (note_title,))
            note_content = self.cursor.fetchone()
            if note_content:
                self.text_editor.setText(note_content[0])

    def delete_note(self):
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
                self.status_bar.showMessage("Note deleted successfully!", 3000)

    def new_note(self):
        self.text_editor.clear()

    def export_pdf(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export PDF", "", "PDF Files (*.pdf)")
        if file_name:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_name)
            document = QTextDocument()
            document.setPlainText(self.text_editor.toPlainText())
            document.print_(printer)
            self.status_bar.showMessage(f"Note exported as PDF to {file_name}", 3000)

    def search_notes(self):
        search_text, ok = QInputDialog.getText(self, "Search Notes", "Enter search term:")
        if ok and search_text:
            self.cursor.execute("SELECT title FROM notes WHERE content LIKE ?", (f"%{search_text}%",))
            results = self.cursor.fetchall()
            self.note_list.clear()
            for note in results:
                self.note_list.addItem(note[0])
            self.status_bar.showMessage(f"Found {len(results)} notes matching '{search_text}'", 3000)

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TuxNote()
    window.show()
    sys.exit(app.exec())