import pathlib
import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                            QProgressBar, QMessageBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
import subprocess
import platform




class CustomTextEdit(QTextEdit):
    """Custom QTextEdit that handles Ctrl+V as plain text"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Override Ctrl+V shortcut
        self.paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        self.paste_shortcut.activated.connect(self.paste_plain_text)
        
    def paste_plain_text(self):
        """Paste as plain text instead of rich text"""
        clipboard = QApplication.clipboard()
        plain_text = clipboard.text()
        
        if plain_text:
            # Get current cursor position
            cursor = self.textCursor()
            
            # Insert plain text at cursor position
            cursor.insertText(plain_text)
            
    def insertFromMimeData(self, source):
        """Override to handle drag and drop as plain text"""
        if source.hasText():
            cursor = self.textCursor()
            cursor.insertText(source.text())
        else:
            super().insertFromMimeData(source)


class DownloadItem(QWidget):
    """Widget for individual download item"""
    
    cancel_requested = pyqtSignal()
    
    def __init__(self, url, is_audio, is_playlist=False):
        super().__init__()
        self.url = url
        self.is_audio = is_audio
        self.is_playlist = is_playlist
        self.completed = False
        self.failed = False
        self.cancelled = False
        self.file_path = None
        
        self.init_ui()
        self.setup_context_menu()
        
    def setup_context_menu(self):
        """Setup context menu for completed downloads"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def show_context_menu(self, position):
        """Show context menu"""
        if not self.completed or not self.file_path:
            return
            
        menu = QMenu(self)
        
        # Open file action
        open_action = menu.addAction("📂 Open File")
        open_action.triggered.connect(self.open_file)
        
        # Show in file manager action
        location_action = menu.addAction("📁 Show in File Manager")
        location_action.triggered.connect(self.show_in_file_manager)
        
        # Copy URL action
        copy_url_action = menu.addAction("📋 Copy URL")
        copy_url_action.triggered.connect(self.copy_url)
        
        menu.exec(self.mapToGlobal(position))
        
    def open_file(self):
        """Open the downloaded file"""
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.warning(self, "File Not Found", "The downloaded file could not be found.")
            return
            
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(self.file_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", self.file_path])
            else:  # Linux
                subprocess.run(["xdg-open", self.file_path])
        except Exception as e:
            QMessageBox.warning(self, "Cannot Open File", f"Failed to open file: {str(e)}")
            
    def show_in_file_manager(self):
        """Show file in file manager"""
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.warning(self, "File Not Found", "The downloaded file could not be found.")
            return
            
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", "/select,", self.file_path])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", "-R", self.file_path])
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(self.file_path)])
        except Exception as e:
            QMessageBox.warning(self, "Cannot Show Location", f"Failed to show file location: {str(e)}")
            
    def copy_url(self):
        """Copy URL to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.url)
        
        # Show temporary feedback
        original_text = self.status_label.text()
        self.status_label.setText("📋 URL copied to clipboard!")
        QTimer.singleShot(2000, lambda: self.status_label.setText(original_text))
        
    def mouseDoubleClickEvent(self, event):
        """Handle double click to open file"""
        if self.completed and self.file_path:
            self.open_file()
        super().mouseDoubleClickEvent(event)
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Top row - URL and type
        top_layout = QHBoxLayout()
        
        # Shorten URL for display
        display_url = self.url
        if len(display_url) > 60:
            display_url = display_url[:57] + "..."
            
        self.url_label = QLabel(display_url)
        
        # Type label with playlist indicator
        if self.is_playlist:
            type_label = QLabel("📋 Playlist" + (" (Audio)" if self.is_audio else " (Video)"))
        else:
            type_label = QLabel("🎵 Audio" if self.is_audio else "🎬 Video")
        
        self.cancel_button = QPushButton("❌")
        self.cancel_button.setMaximumSize(25, 25)
        self.cancel_button.setToolTip("Cancel download")
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        
        top_layout.addWidget(self.url_label)
        top_layout.addWidget(type_label)
        top_layout.addStretch()
        top_layout.addWidget(self.cancel_button)
        
        layout.addLayout(top_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)        
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Starting...")
        layout.addWidget(self.status_label)
        
    def on_cancel_clicked(self):
        """Handle cancel button click"""
        self.cancelled = True
        self.status_label.setText("🚫 Cancelling...")
        self.cancel_button.setEnabled(False)
        self.cancel_requested.emit()
        
    def update_progress(self, progress, speed, file_size, eta):
        """Update download progress"""
        if not self.cancelled:
            self.progress_bar.setValue(progress)
            status_text = f"⬇️ Downloading... {speed}"
            if file_size != "Unknown":
                status_text += f" | Size: {file_size}"
            if eta != "Unknown":
                status_text += f" | ETA: {eta}"
            self.status_label.setText(status_text)
        
    def set_completed(self, filename, file_path):
        """Set download as completed"""
        if not self.cancelled:
            self.completed = True
            self.file_path = file_path
            self.progress_bar.setValue(100)
            self.status_label.setText(f"✅ Completed: {filename} (Double-click to open)")
            self.cancel_button.hide()
            
            # Add visual indication that file is clickable
            self.setStyleSheet("""
                DownloadItem:hover {
                    background-color: #f0f0f0;
                    border-radius: 5px;
                }
            """)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def set_failed(self, error):
        """Set download as failed"""
        if not self.cancelled:
            self.failed = True
            self.status_label.setText(f"❌ Failed: {error}")
            self.cancel_button.hide()
        
    def is_completed(self):
        """Check if download is completed or failed"""
        return self.completed or self.failed or self.cancelled
