import pathlib
import subprocess
import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, 
                            QComboBox, QCheckBox, QLineEdit, QFileDialog,
                            QListWidget, QListWidgetItem,
                            QMessageBox, QFrame, QDialog)
from PyQt6.QtCore import Qt, QTimer
from plyer import notification
from .widgets import CustomTextEdit, DownloadItem
from .dialogs import HistoryDialog, InfoDialog, DonateDialog, PlaylistLoadingDialog, PlaylistSelectionDialog
from core.download_thread import DownloadThread
from core.settings import SettingsManager


def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def show_ffmpeg_warning():
    """Show warning about missing FFmpeg"""
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle("FFmpeg Not Found")
    msg.setText("FFmpeg is required for audio conversion.")
    msg.setInformativeText(
        "Please install FFmpeg:\n"
        "1. Download from https://ffmpeg.org/download.html\n"
        "2. Add to system PATH\n"
        "3. Restart DownloadStation"
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()


class DownloadStation(QMainWindow):
    """Simple DownloadStation main window"""
    
    def __init__(self):
        super().__init__()
        self.download_threads = []
        self.downloads_count = 0
        self.settings_manager = SettingsManager()
        
        self.init_ui()
        self.setup_connections()
        self.load_user_preferences()
        
        # Timer for UI updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("DownloadStation")
        
        # Load window geometry from settings
        geometry = self.settings_manager.get("window_geometry", {})
        self.setGeometry(
            geometry.get("x", 200),
            geometry.get("y", 200),
            geometry.get("width", 700),
            geometry.get("height", 500)
        )
        self.setMinimumSize(600, 400)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with title and donate button
        header_layout = QHBoxLayout()
        
        title = QLabel("DownloadStation")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Info button
        self.info_button = QPushButton("ℹ️ Info")
        self.info_button.setToolTip("Supported platforms and contact information")
        self.info_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                margin-right: 10px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        header_layout.addWidget(self.info_button)
        
        # Donate button
        self.donate_button = QPushButton("💝 Donate")
        self.donate_button.setToolTip("Support DownloadStation development")
        self.donate_button.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff5252;
            }
        """)
        header_layout.addWidget(self.donate_button)
        
        layout.addLayout(header_layout)
        
        # URL input section
        url_frame = self.create_url_section()
        layout.addWidget(url_frame)
        
        # Options section
        options_frame = self.create_options_section()
        layout.addWidget(options_frame)
        
        # Downloads section
        downloads_frame = self.create_downloads_section()
        layout.addWidget(downloads_frame)
        
        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
    def create_url_section(self):
        """Create URL input section"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        layout = QVBoxLayout(frame)
        
        layout.addWidget(QLabel("📥 Enter URLs (one per line):"))
        
        # Use custom text edit that handles plain text paste
        self.url_input = CustomTextEdit()
        self.url_input.setMaximumHeight(100)
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...\nhttps://soundcloud.com/...")
        layout.addWidget(self.url_input)
        
        # Recent URLs dropdown (if any)
        recent_urls = self.settings_manager.get("recent_urls", [])
        if recent_urls:
            recent_layout = QHBoxLayout()
            recent_layout.addWidget(QLabel("📌 Recent:"))
            
            self.recent_combo = QComboBox()
            self.recent_combo.addItem("Select recent URL...")
            self.recent_combo.addItems([url[:60] + "..." if len(url) > 60 else url for url in recent_urls])
            self.recent_combo.currentTextChanged.connect(self.on_recent_url_selected)
            recent_layout.addWidget(self.recent_combo)
            recent_layout.addStretch()
            
            layout.addLayout(recent_layout)
        
        # URL buttons
        url_buttons = QHBoxLayout()
        
        self.paste_button = QPushButton("📋 Paste")
        self.clear_button = QPushButton("🗑 Clear")
        self.history_button = QPushButton("📋 History")
        
        url_buttons.addWidget(self.paste_button)
        url_buttons.addWidget(self.clear_button)
        url_buttons.addWidget(self.history_button)
        url_buttons.addStretch()
        
        layout.addLayout(url_buttons)
        
        return frame
        
    def create_options_section(self):
        """Create options section"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        layout = QVBoxLayout(frame)
        
        layout.addWidget(QLabel("⚙️ Download Options:"))
        
        options_grid = QHBoxLayout()
        
        # Download type
        self.audio_only_checkbox = QCheckBox("Audio Only (MP3)")
        options_grid.addWidget(self.audio_only_checkbox)
        
        # Playlist option
        self.no_playlist_checkbox = QCheckBox("Single Video Only")
        self.no_playlist_checkbox.setToolTip("Download only the specific video, not the entire playlist")
        self.no_playlist_checkbox.setChecked(True)  # Default to single video
        options_grid.addWidget(self.no_playlist_checkbox)
        
        # Quality
        options_grid.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1080p", "720p", "480p", "Best"])
        self.quality_combo.setCurrentText("720p")
        options_grid.addWidget(self.quality_combo)
        
        # Download path
        options_grid.addWidget(QLabel("Save to:"))
        self.path_input = QLineEdit()
        self.path_input.setText(self.settings_manager.get("download_path", os.path.join(os.path.expanduser('~'), 'Downloads')))
        self.path_input.setReadOnly(True)
        options_grid.addWidget(self.path_input)
        
        self.browse_button = QPushButton("📁")
        self.browse_button.setMaximumWidth(40)
        options_grid.addWidget(self.browse_button)
        
        layout.addLayout(options_grid)
        
        # Download button
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("🚀 Start Download")
        self.download_button.setMinimumHeight(40)
        self.download_button.setMinimumWidth(120)
        
        button_layout.addStretch()
        button_layout.addWidget(self.download_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return frame
        
    def create_downloads_section(self):
        """Create downloads list section"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        layout = QVBoxLayout(frame)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("📋 Downloads:"))
        
        self.clear_completed_button = QPushButton("Clear Completed")
        self.clear_completed_button.setMaximumWidth(120)
        header_layout.addWidget(self.clear_completed_button)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Downloads list
        self.downloads_list = QListWidget()
        self.downloads_list.setMaximumHeight(200)
        layout.addWidget(self.downloads_list)
        
        return frame
        
    def setup_connections(self):
        """Setup signal connections"""
        self.paste_button.clicked.connect(self.paste_urls)
        self.clear_button.clicked.connect(self.clear_urls)
        self.history_button.clicked.connect(self.show_history_dialog)
        self.browse_button.clicked.connect(self.browse_path)
        self.download_button.clicked.connect(self.start_downloads)
        self.clear_completed_button.clicked.connect(self.clear_completed)
        self.info_button.clicked.connect(self.show_info_dialog)
        self.donate_button.clicked.connect(self.show_donate_dialog)
        
        # Audio checkbox disables quality selection
        self.audio_only_checkbox.toggled.connect(self.on_audio_toggle)
        
        # Save settings when values change
        self.audio_only_checkbox.toggled.connect(self.save_user_preferences)
        self.no_playlist_checkbox.toggled.connect(self.save_user_preferences)
        self.quality_combo.currentTextChanged.connect(self.save_user_preferences)
        
    def load_user_preferences(self):
        """Load user preferences from settings"""
        # Load audio only preference
        self.audio_only_checkbox.setChecked(self.settings_manager.get("audio_only", False))
        
        # Load single video only preference
        self.no_playlist_checkbox.setChecked(self.settings_manager.get("single_video_only", True))
        
        # Load quality preference
        quality = self.settings_manager.get("quality", "720p")
        index = self.quality_combo.findText(quality)
        if index >= 0:
            self.quality_combo.setCurrentIndex(index)
        
        # Update UI based on loaded preferences
        self.on_audio_toggle(self.audio_only_checkbox.isChecked())
        
    def save_user_preferences(self):
        """Save user preferences to settings"""
        self.settings_manager.set("audio_only", self.audio_only_checkbox.isChecked())
        self.settings_manager.set("single_video_only", self.no_playlist_checkbox.isChecked())
        self.settings_manager.set("quality", self.quality_combo.currentText())
        
    def on_recent_url_selected(self, text):
        """Handle recent URL selection"""
        if text and text != "Select recent URL...":
            recent_urls = self.settings_manager.get("recent_urls", [])
            # Find the full URL
            for url in recent_urls:
                if url.startswith(text[:20]):  # Match beginning
                    current = self.url_input.toPlainText()
                    if current:
                        self.url_input.setPlainText(current + '\n' + url)
                    else:
                        self.url_input.setPlainText(url)
                    break
                    
    def show_history_dialog(self):
        """Show download history dialog"""
        dialog = HistoryDialog(self.settings_manager, self)
        dialog.exec()
        
    def show_info_dialog(self):
        """Show information dialog"""
        dialog = InfoDialog(self)
        dialog.exec()
        
    def show_donate_dialog(self):
        """Show donation dialog"""
        dialog = DonateDialog(self)
        dialog.exec()
        
    def on_audio_toggle(self, checked):
        """Handle audio only toggle"""
        self.quality_combo.setEnabled(not checked)
        
    def paste_urls(self):
        """Paste URLs from clipboard as plain text"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()  # Get plain text, not rich text
        if text:
            current = self.url_input.toPlainText()
            if current:
                self.url_input.setPlainText(current + '\n' + text)
            else:
                self.url_input.setPlainText(text)
                
    def clear_urls(self):
        """Clear URL input"""
        self.url_input.clear()
        
    def browse_path(self):
        """Browse for download directory"""
        path = QFileDialog.getExistingDirectory(self, "Select Download Directory", self.path_input.text())
        if path:
            self.path_input.setText(path)
            self.settings_manager.set("download_path", path)
            
    def get_urls(self):
        """Get list of URLs from input"""
        text = self.url_input.toPlainText().strip()
        if not text:
            return []
            
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        urls = []
        
        for line in lines:
            # Simple URL validation
            if line.startswith(('http://', 'https://')) and len(line) > 10:
                urls.append(line)
                
        return urls
        
    def is_playlist_url(self, url):
        """Check if URL contains playlist information"""
        return 'list=' in url or 'playlist' in url.lower()
        
    def start_downloads(self):
        """Start downloading URLs"""
        urls = self.get_urls()
        
        if not urls:
            QMessageBox.warning(self, "No URLs", "Please enter at least one valid URL.")
            return
            
        download_path = self.path_input.text()
        if not os.path.exists(download_path):
            QMessageBox.warning(self, "Invalid Path", "Download directory does not exist.")
            return
            
        is_audio = self.audio_only_checkbox.isChecked()
        quality = self.quality_combo.currentText()
        no_playlist = self.no_playlist_checkbox.isChecked()
        
        # Process each URL
        for url in urls:
            # Add to recent URLs
            self.settings_manager.add_recent_url(url)
            
            if not no_playlist and self.is_playlist_url(url):
                # Handle playlist URL with selection dialog
                self.handle_playlist_url(url, download_path, is_audio, quality)
            else:
                # Handle single video
                self.add_download(url, download_path, is_audio, quality, no_playlist)
                
        # Clear URLs after starting
        self.url_input.clear()
        
    def handle_playlist_url(self, url, download_path, is_audio, quality):
        """Handle playlist URL with selection dialog"""
        # Show loading dialog
        loading_dialog = PlaylistLoadingDialog(url, self)
        
        if loading_dialog.exec() == QDialog.DialogCode.Accepted:
            playlist_info = loading_dialog.playlist_info
            
            if playlist_info and playlist_info.get('entries'):
                # Show selection dialog
                selection_dialog = PlaylistSelectionDialog(playlist_info, self)
                
                if selection_dialog.exec() == QDialog.DialogCode.Accepted:
                    selected_entries = selection_dialog.get_selected_entries()
                    
                    if selected_entries:
                        # Add download for selected entries
                        self.add_playlist_download(url, download_path, is_audio, quality, selected_entries)
                    else:
                        QMessageBox.information(self, "No Selection", "No videos were selected for download.")
            else:
                QMessageBox.warning(self, "Empty Playlist", "The playlist appears to be empty or unavailable.")
        
    def add_download(self, url, path, is_audio, quality, no_playlist=True, playlist_entries=None):
        """Add a new download"""
        # Create download item
        if playlist_entries:
            display_text = f"Playlist: {len(playlist_entries)} videos"
            item_widget = DownloadItem(display_text, is_audio, is_playlist=True)
        else:
            item_widget = DownloadItem(url, is_audio)
            
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        
        self.downloads_list.addItem(item)
        self.downloads_list.setItemWidget(item, item_widget)
        
        # Create and start download thread
        thread = DownloadThread(url, path, is_audio, quality, no_playlist, playlist_entries)
        thread.progress_updated.connect(item_widget.update_progress)
        thread.download_completed.connect(lambda filename, filepath: self.on_download_completed(item_widget, filename, filepath))
        thread.download_failed.connect(lambda error: self.on_download_failed(item_widget, error))
        
        # Connect cancel signal to remove item
        item_widget.cancel_requested.connect(lambda: self.cancel_download(item_widget, thread, item))
        
        self.download_threads.append(thread)
        thread.start()
        
        self.downloads_count += 1
        
    def add_playlist_download(self, url, path, is_audio, quality, selected_entries):
        """Add a playlist download with selected entries"""
        self.add_download(url, path, is_audio, quality, no_playlist=False, playlist_entries=selected_entries)
        
    def cancel_download(self, item_widget, thread, list_item):
        """Cancel download and remove from list"""
        # Cancel the thread
        thread.cancel()
        
        # Remove from thread list
        if thread in self.download_threads:
            self.download_threads.remove(thread)
        
        # Remove from UI list
        row = self.downloads_list.row(list_item)
        if row >= 0:
            self.downloads_list.takeItem(row)
        
        # Show notification
        try:
            notification.notify(
                title="Download Cancelled",
                message=f"Cancelled: {item_widget.url}",
                app_name="DownloadStation",
                timeout=2
            )
        except:
            pass
        
    def on_download_completed(self, item_widget, filename, filepath):
        """Handle download completion"""
        item_widget.set_completed(filename, filepath)
        
        # Add to download history
        self.settings_manager.add_download_history(item_widget.url, filename, success=True)
        
        # Show notification
        try:
            notification.notify(
                title="Download Complete",
                message=f"Downloaded: {filename}",
                app_name="DownloadStation",
                timeout=3
            )
        except:
            pass
            
    def on_download_failed(self, item_widget, error):
        """Handle download failure"""
        # Add to download history as failed
        self.settings_manager.add_download_history(item_widget.url, "Failed", success=False)
        
        # Show notification
        try:
            notification.notify(
                title="Download Failed",
                message=f"Failed to download: {item_widget.url}",
                app_name="DownloadStation",
                timeout=3
            )
        except:
            pass
        item_widget.set_failed(error)
        
    def clear_completed(self):
        """Clear completed downloads from list"""
        for i in range(self.downloads_list.count() - 1, -1, -1):
            item = self.downloads_list.item(i)
            widget = self.downloads_list.itemWidget(item)
            if widget and widget.is_completed():
                self.downloads_list.takeItem(i)
                
    def update_status(self):
        """Update status bar"""
        active = len([t for t in self.download_threads if t.isRunning()])
        total = self.downloads_count
        
        if active > 0:
            self.status_label.setText(f"Downloading... ({active} active, {total} total)")
        else:
            self.status_label.setText(f"Ready ({total} downloads completed)")

    def closeEvent(self, event):
        """Handle window close event with proper cleanup"""
        # Check if there are active downloads
        active_downloads = [t for t in self.download_threads if t.isRunning()]
        
        if active_downloads:
            reply = QMessageBox.question(
                self,
                "Active Downloads",
                f"There are {len(active_downloads)} active downloads. Do you want to:\n\n"
                "• Cancel all downloads and exit\n"
                "• Continue downloads in background\n"
                "• Return to application",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Yes:
                # Cancel all downloads
                self.cancel_all_downloads()
            # If No, let downloads continue in background
        
        # Save window geometry
        geometry = self.geometry()
        self.settings_manager.set("window_geometry", {
            "x": geometry.x(),
            "y": geometry.y(), 
            "width": geometry.width(),
            "height": geometry.height()
        })
        
        # Clean up temporary files and logs
        self.cleanup_on_exit()
        
        event.accept()

    def cancel_all_downloads(self):
        """Cancel all running download threads"""
        for thread in self.download_threads:
            if thread.isRunning():
                thread.cancel()
        
        # Wait for threads to finish (with timeout)
        for thread in self.download_threads:
            if thread.isRunning():
                thread.wait(3000)  # Wait up to 3 seconds
                if thread.isRunning():
                    thread.terminate()

    def cleanup_on_exit(self):
        """Clean up temporary files and logs on exit"""
        try:
            # Clean up old log files (keep last 100 entries)
            self.cleanup_logs()
            
            # Clean up any temporary download files
            self.cleanup_temp_files()
            
            # Save final settings
            self.settings_manager.save_settings()
            
        except Exception as e:
            print(f"Cleanup error: {e}")

    def cleanup_logs(self):
        """Clean up old log entries"""
        log_file = pathlib.Path.cwd() / "logs/history.log"
        
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                # Keep only last 100 lines
                if len(lines) > 100:
                    with open(log_file, 'w') as f:
                        f.writelines(lines[-100:])
                        
            except Exception as e:
                print(f"Log cleanup error: {e}")

    def cleanup_temp_files(self):
        """Clean up temporary download files"""
        try:
            # Look for incomplete download files (.part, .tmp, etc.)
            download_path = self.path_input.text()
            
            if os.path.exists(download_path):
                for file in pathlib.Path(download_path).glob("*.part"):
                    try:
                        file.unlink()
                    except:
                        pass
                        
                for file in pathlib.Path(download_path).glob("*.tmp"):
                    try:
                        file.unlink()
                    except:
                        pass
                        
        except Exception as e:
            print(f"Temp file cleanup error: {e}")
    
    def cancel_all_active_downloads(self):
        """Cancel all downloads with user confirmation"""
        active_downloads = [t for t in self.download_threads if t.isRunning()]
        
        if not active_downloads:
            QMessageBox.information(self, "No Active Downloads", "There are no active downloads to cancel.")
            return
        
        reply = QMessageBox.question(
            self,
            "Cancel Downloads",
            f"Cancel {len(active_downloads)} active download(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cancel_all_downloads()
            
            # Clear UI of cancelled downloads
            for i in range(self.downloads_list.count() - 1, -1, -1):
                item = self.downloads_list.item(i)
                widget = self.downloads_list.itemWidget(item)
                if widget and not widget.is_completed():
                    self.downloads_list.takeItem(i)
