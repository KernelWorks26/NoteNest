import sys
import sqlite3
import os
import pickle
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QListWidget, QMessageBox, QLabel,
    QTabWidget, QMenuBar, QStatusBar, QFileDialog, QInputDialog, QMainWindow, QMenu, QHBoxLayout, QToolBar
)
from PyQt6.QtGui import (
    QAction, QTextDocument, QTextCursor, QTextCharFormat, QColor, QTextFormat, QFont, QIcon
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtCore import Qt
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

class NestNote(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.setWindowTitle("NestNote - Your Feature-Rich Note-Taking Application")
        self.setGeometry(100, 100, 1000, 700)

        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout
        self.layout = QVBoxLayout(self.central_widget)

        # Initialize Text Editor
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText("Type your notes here...")
        self.set_default_text_color()  # Set default text color to black

        # Initialize Buttons
        self.save_button = QPushButton("Save Note")
        self.sync_button = QPushButton("Sync with Google Drive")
        self.delete_button = QPushButton("Delete Note")
        self.clear_button = QPushButton("New Note")
        self.export_button = QPushButton("Export as PDF")
        self.search_button = QPushButton("Search Notes")

        # Initialize Notes List
        self.note_list = QListWidget()

        # Create Menu Bar and Toolbar
        self.create_menu_bar()
        self.create_toolbar()

        # Tab Widget
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Notes Tab
        self.notes_tab = QWidget()
        self.notes_layout = QVBoxLayout(self.notes_tab)
        self.tabs.addTab(self.notes_tab, "Notes")

        # Add Widgets to Notes Tab
        self.notes_layout.addWidget(QLabel("Saved Notes:"))
        self.notes_layout.addWidget(self.note_list)
        self.notes_layout.addWidget(self.text_editor)

        # Button Layout
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.sync_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addWidget(self.clear_button)
        self.button_layout.addWidget(self.export_button)
        self.button_layout.addWidget(self.search_button)
        self.notes_layout.addLayout(self.button_layout)

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

    def set_default_text_color(self):
        """Set the default text color to black in the QTextEdit."""
        cursor = self.text_editor.textCursor()
        format = QTextCharFormat()
        format.setForeground(QColor("black"))
        cursor.setCharFormat(format)
        self.text_editor.setTextCursor(cursor)

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

        print_action = QAction("Print Note", self)
        print_action.triggered.connect(self.print_note)
        file_menu.addAction(print_action)

        backup_action = QAction("Backup Notes", self)
        backup_action.triggered.connect(self.backup_notes)
        file_menu.addAction(backup_action)

        restore_action = QAction("Restore Notes", self)
        restore_action.triggered.connect(self.restore_notes)
        file_menu.addAction(restore_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("Edit")
        undo_action = QAction("Undo", self)
        undo_action.triggered.connect(self.text_editor.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(self.text_editor.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cut", self)
        cut_action.triggered.connect(self.text_editor.cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.text_editor.copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self.text_editor.paste)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        search_action = QAction("Search Notes", self)
        search_action.triggered.connect(self.search_notes)
        edit_menu.addAction(search_action)

        # View Menu
        view_menu = menubar.addMenu("View")
        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)

        # Format Menu
        format_menu = menubar.addMenu("Format")
        bold_action = QAction("Bold", self)
        bold_action.triggered.connect(self.set_bold)
        format_menu.addAction(bold_action)

        italic_action = QAction("Italic", self)
        italic_action.triggered.connect(self.set_italic)
        format_menu.addAction(italic_action)

        underline_action = QAction("Underline", self)
        underline_action.triggered.connect(self.set_underline)
        format_menu.addAction(underline_action)

        format_menu.addSeparator()

        font_action = QAction("Change Font", self)
        font_action.triggered.connect(self.change_font)
        format_menu.addAction(font_action)

        color_action = QAction("Change Text Color", self)
        color_action.triggered.connect(self.change_text_color)
        format_menu.addAction(color_action)

        # Tools Menu
        tools_menu = menubar.addMenu("Tools")
        sync_action = QAction("Sync with Google Drive", self)
        sync_action.triggered.connect(self.sync_to_drive)
        tools_menu.addAction(sync_action)

        # Help Menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About NestNote", self)
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

        docs_action = QAction("Documentation", self)
        docs_action.triggered.connect(self.documentation)
        help_menu.addAction(docs_action)

    def create_toolbar(self):
        toolbar = QToolBar("Toolbar")
        self.addToolBar(toolbar)

        # Add actions to the toolbar
        toolbar.addAction("Bold", self.set_bold)
        toolbar.addAction("Italic", self.set_italic)
        toolbar.addAction("Underline", self.set_underline)
        toolbar.addSeparator()
        toolbar.addAction("Change Font", self.change_font)
        toolbar.addAction("Change Text Color", self.change_text_color)

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
                color: black;
            }
            QPushButton {
                color: white;
                border: none;
                padding: 8px 12px;
                font-size: 14px;
                min-width: 80px;
                max-width: 120px;
                border-radius: 4px;
            }
            QPushButton#save_button {
                background-color: #4CAF50;
            }
            QPushButton#save_button:hover {
                background-color: #45a049;
            }
            QPushButton#sync_button {
                background-color: #2196F3;
            }
            QPushButton#sync_button:hover {
                background-color: #1e88e5;
            }
            QPushButton#delete_button {
                background-color: #f44336;
            }
            QPushButton#delete_button:hover {
                background-color: #e53935;
            }
            QPushButton#clear_button {
                background-color: #9C27B0;
            }
            QPushButton#clear_button:hover {
                background-color: #8E24AA;
            }
            QPushButton#export_button {
                background-color: #FF9800;
            }
            QPushButton#export_button:hover {
                background-color: #FB8C00;
            }
            QPushButton#search_button {
                background-color: #607D8B;
            }
            QPushButton#search_button:hover {
                background-color: #546E7A;
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

        # Assign object names to buttons for styling
        self.save_button.setObjectName("save_button")
        self.sync_button.setObjectName("sync_button")
        self.delete_button.setObjectName("delete_button")
        self.clear_button.setObjectName("clear_button")
        self.export_button.setObjectName("export_button")
        self.search_button.setObjectName("search_button")

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

    def print_note(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            document = QTextDocument()
            document.setPlainText(self.text_editor.toPlainText())
            document.print_(printer)

    def backup_notes(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Backup Notes", "", "SQLite Database (*.db)")
        if file_name:
            try:
                with open(file_name, 'wb') as backup_file:
                    for line in self.conn.iterdump():
                        backup_file.write(f"{line}\n".encode('utf-8'))
                self.status_bar.showMessage(f"Notes backed up to {file_name}", 3000)
            except Exception as e:
                QMessageBox.warning(self, "Backup Error", f"Failed to backup notes: {str(e)}")

    def restore_notes(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Restore Notes", "", "SQLite Database (*.db)")
        if file_name:
            try:
                self.conn.close()
                os.remove("notes.db")
                os.rename(file_name, "notes.db")
                self.db_connect()
                self.load_notes()
                self.status_bar.showMessage(f"Notes restored from {file_name}", 3000)
            except Exception as e:
                QMessageBox.warning(self, "Restore Error", f"Failed to restore notes: {str(e)}")

    def search_notes(self):
        search_text, ok = QInputDialog.getText(self, "Search Notes", "Enter search term:")
        if ok and search_text:
            self.cursor.execute("SELECT title FROM notes WHERE content LIKE ?", (f"%{search_text}%",))
            results = self.cursor.fetchall()
            self.note_list.clear()
            for note in results:
                self.note_list.addItem(note[0])
            self.status_bar.showMessage(f"Found {len(results)} notes matching '{search_text}'", 3000)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def zoom_in(self):
        self.text_editor.zoomIn(1)

    def zoom_out(self):
        self.text_editor.zoomOut(1)

    def set_bold(self):
        cursor = self.text_editor.textCursor()
        format = QTextCharFormat()
        format.setFontWeight(QFont.Weight.Bold if cursor.charFormat().fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal)
        cursor.mergeCharFormat(format)
        self.text_editor.setFocus()

    def set_italic(self):
        cursor = self.text_editor.textCursor()
        format = QTextCharFormat()
        format.setFontItalic(not cursor.charFormat().fontItalic())
        cursor.mergeCharFormat(format)
        self.text_editor.setFocus()

    def set_underline(self):
        cursor = self.text_editor.textCursor()
        format = QTextCharFormat()
        format.setFontUnderline(not cursor.charFormat().fontUnderline())
        cursor.mergeCharFormat(format)
        self.text_editor.setFocus()

    def change_font(self):
        font, ok = QFontDialog.getFont(self.text_editor.font(), self)
        if ok:
            self.text_editor.setFont(font)

    def change_text_color(self):
        color = QColorDialog.getColor(self.text_editor.textColor(), self)
        if color.isValid():
            self.text_editor.setTextColor(color)

    def about(self):
        QMessageBox.about(self, "About NestNote", "NestNote - A feature-rich note-taking application inspired by OneNote.")

    def documentation(self):
        QMessageBox.information(self, "Documentation", "Documentation is under development.")

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NestNote()
    window.show()
    sys.exit(app.exec())