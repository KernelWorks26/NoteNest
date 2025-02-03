import sys
import sqlite3
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QListWidget, QMessageBox, QLabel

class TuxNote(QWidget):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.setWindowTitle("TuxNote - Open Source Note Taking")
        self.setGeometry(100, 100, 700, 500)

        # Layout
        self.layout = QVBoxLayout()

        # Notes List
        self.label = QLabel("Saved Notes:")
        self.note_list = QListWidget()

        # Text Editor
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText("Type your notes here...")  # Makes it clear where to type

        # Buttons
        self.save_button = QPushButton("Save Note")
        self.delete_button = QPushButton("Delete Note")
        self.clear_button = QPushButton("New Note")

        # Add Widgets to Layout
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.note_list)
        self.layout.addWidget(self.text_editor)
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.delete_button)
        self.layout.addWidget(self.clear_button)

        self.setLayout(self.layout)

        # Database setup
        self.db_connect()
        self.load_notes()

        # Event Listeners
        self.save_button.clicked.connect(self.save_note)
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

