import pathlib
import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, 
                            QCheckBox, QLineEdit, QProgressBar,
                            QMessageBox, QFrame, QDialog, QScrollArea,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QAbstractItemView)
from PyQt6.QtCore import Qt, QTimer
import datetime
from core.playlist_loader import PlaylistInfoThread


class PlaylistSelectionDialog(QDialog):
    """Dialog for selecting videos from a playlist"""
    
    def __init__(self, playlist_info, parent=None):
        super().__init__(parent)
        self.playlist_info = playlist_info
        self.selected_entries = []
        
        self.setWindowTitle(f"Select Videos - {playlist_info.get('title', 'Playlist')}")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.populate_playlist()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Header info
        header_layout = QVBoxLayout()
        
        title_label = QLabel(f"📋 {self.playlist_info.get('title', 'Unknown Playlist')}")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 5px;")
        header_layout.addWidget(title_label)
        
        count_label = QLabel(f"📊 {len(self.playlist_info.get('entries', []))} videos found")
        header_layout.addWidget(count_label)
        
        layout.addLayout(header_layout)
        
        # Selection controls
        controls_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("✅ Select All")
        self.select_none_btn = QPushButton("❌ Select None")
        
        controls_layout.addWidget(self.select_all_btn)
        controls_layout.addWidget(self.select_none_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Videos table
        self.videos_table = QTableWidget()
        self.videos_table.setColumnCount(4)
        self.videos_table.setHorizontalHeaderLabels(["Select", "Title", "Duration", "Uploader"])
        
        # Configure table
        header = self.videos_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.videos_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.videos_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.videos_table)
        
        # Dialog buttons
        buttons_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("🚀 Download Selected")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #d1d5db;
                color: #6b7280;
            }
        """)
        self.download_btn.setEnabled(False)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(self.download_btn)
        
        layout.addLayout(buttons_layout)
        
        # Connect signals
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_none_btn.clicked.connect(self.select_none)
        self.download_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
    def populate_playlist(self):
        """Populate the playlist table"""
        entries = self.playlist_info.get('entries', [])
        self.videos_table.setRowCount(len(entries))
        
        for row, entry in enumerate(entries):
            # Skip None entries (unavailable videos)
            if entry is None:
                continue
                
            # Checkbox for selection
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.update_download_button)
            self.videos_table.setCellWidget(row, 0, checkbox)
            
            # Title
            title = entry.get('title', 'Unknown Title')
            if len(title) > 60:
                title = title[:57] + "..."
            title_item = QTableWidgetItem(title)
            title_item.setToolTip(entry.get('title', 'Unknown Title'))
            self.videos_table.setItem(row, 1, title_item)
            
            # Duration
            # Duration
            duration = entry.get('duration', 0)
            if duration:
                # Convert to int first to handle float values
                duration = int(duration)
                minutes, seconds = divmod(duration, 60)
                duration_str = f"{minutes:02d}:{seconds:02d}"
            else:
                duration_str = "Unknown"
            self.videos_table.setItem(row, 2, QTableWidgetItem(duration_str))
            
            # Uploader
            uploader = entry.get('uploader', 'Unknown')
            if len(uploader) > 20:
                uploader = uploader[:17] + "..."
            uploader_item = QTableWidgetItem(uploader)
            uploader_item.setToolTip(entry.get('uploader', 'Unknown'))
            self.videos_table.setItem(row, 3, uploader_item)
            
    def select_all(self):
        """Select all videos"""
        for row in range(self.videos_table.rowCount()):
            checkbox = self.videos_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
                
    def select_none(self):
        """Deselect all videos"""
        for row in range(self.videos_table.rowCount()):
            checkbox = self.videos_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
                
    def update_download_button(self):
        """Update download button state based on selection"""
        selected_count = 0
        for row in range(self.videos_table.rowCount()):
            checkbox = self.videos_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
                
        self.download_btn.setEnabled(selected_count > 0)
        self.download_btn.setText(f"🚀 Download Selected ({selected_count})")
        
    def get_selected_entries(self):
        """Get list of selected playlist entries"""
        selected = []
        entries = self.playlist_info.get('entries', [])
        
        for row in range(self.videos_table.rowCount()):
            checkbox = self.videos_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked() and row < len(entries):
                if entries[row] is not None:  # Skip unavailable videos
                    selected.append(entries[row])
                    
        return selected


class PlaylistLoadingDialog(QDialog):
    """Dialog showing playlist loading progress"""
    
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.playlist_info = None
        
        self.setWindowTitle("Loading Playlist...")
        self.setModal(True)
        self.setFixedSize(450, 280)
        
        self.init_ui()
        self.start_loading()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("📋 Loading Playlist Information")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # URL display
        url_display = self.url
        if len(url_display) > 50:
            url_display = url_display[:47] + "..."
        url_label = QLabel(f"🔗 {url_display}")
        url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        url_label.setWordWrap(True)
        url_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(url_label)
        
        # Progress information frame
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.Box)
        info_layout = QVBoxLayout(info_frame)
        
        # Playlist stats
        self.total_items_label = QLabel("📊 Total items: Discovering...")
        self.total_items_label.setStyleSheet("font-weight: bold; color: #2563eb;")
        info_layout.addWidget(self.total_items_label)
        
        self.loaded_items_label = QLabel("✅ Loaded: 0")
        self.loaded_items_label.setStyleSheet("color: #059669;")
        info_layout.addWidget(self.loaded_items_label)
        
        self.remaining_items_label = QLabel("⏳ Remaining: Unknown")
        self.remaining_items_label.setStyleSheet("color: #dc2626;")
        info_layout.addWidget(self.remaining_items_label)
        
        layout.addWidget(info_frame)
        
        # Main progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("🔍 Discovering playlist structure...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Speed/time info
        self.speed_label = QLabel("⚡ Speed: Calculating...")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self.speed_label)
        
        # Cancel button
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_loading)
        layout.addWidget(self.cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def start_loading(self):
        """Start loading playlist information"""
        self.loading_thread = PlaylistInfoThread(self.url)
        self.loading_thread.info_loaded.connect(self.on_info_loaded)
        self.loading_thread.loading_failed.connect(self.on_loading_failed)
        self.loading_thread.progress_updated.connect(self.on_progress_updated)
        self.loading_thread.start()
        
    def cancel_loading(self):
        """Cancel playlist loading"""
        if hasattr(self, 'loading_thread') and self.loading_thread.isRunning():
            self.loading_thread.cancel()
        self.reject()
        
    def on_progress_updated(self, total_items, loaded_items, current_title):
        """Update progress display"""
        if total_items > 0:
            progress = int((loaded_items / total_items) * 100)
            self.progress_bar.setValue(progress)
            
            # Update labels
            self.total_items_label.setText(f"📊 Total items: {total_items}")
            self.loaded_items_label.setText(f"✅ Loaded: {loaded_items}")
            self.remaining_items_label.setText(f"⏳ Remaining: {total_items - loaded_items}")
            
            # Update status
            if current_title:
                display_title = current_title[:40] + "..." if len(current_title) > 40 else current_title
                self.status_label.setText(f"🎵 Loading: {display_title}")
            else:
                self.status_label.setText(f"📥 Processing item {loaded_items} of {total_items}")
                
            # Calculate and show speed
            if hasattr(self, 'loading_thread'):
                elapsed = self.loading_thread.get_elapsed_time()
                if elapsed > 0 and loaded_items > 0:
                    speed = loaded_items / elapsed
                    remaining_time = (total_items - loaded_items) / speed if speed > 0 else 0
                    
                    self.speed_label.setText(f"⚡ Speed: {speed:.1f} items/sec | ETA: {remaining_time:.0f}s")
        else:
            # Still discovering
            self.total_items_label.setText("📊 Total items: Discovering...")
            self.loaded_items_label.setText(f"✅ Found: {loaded_items}")
            self.status_label.setText("🔍 Scanning playlist structure...")
            
    def on_info_loaded(self, playlist_info):
        """Handle successful playlist loading"""
        self.playlist_info = playlist_info
        self.progress_bar.setValue(100)
        self.status_label.setText("✅ Playlist loaded successfully!")
        
        # Small delay to show completion
        QTimer.singleShot(500, self.accept)
        
    def on_loading_failed(self, error):
        """Handle playlist loading failure"""
        QMessageBox.critical(self, "Loading Failed", f"Failed to load playlist:\n{error}")
        self.reject()





class HistoryDialog(QDialog):
    """Dialog showing download history"""
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        
        self.setWindowTitle("Download History")
        self.setModal(True)
        self.resize(700, 400)
        
        self.init_ui()
        self.populate_history()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("📋 Download History")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Status", "Filename", "Date", "URL"])
        
        # Configure table
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.doubleClicked.connect(self.copy_url)
        
        layout.addWidget(self.history_table)
        
        # Info label
        info_label = QLabel("💡 Double-click any row to copy URL to clipboard")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Clear History")
        clear_btn.clicked.connect(self.clear_history)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        buttons_layout.addWidget(clear_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
    def populate_history(self):
        """Populate history table"""
        history = self.settings_manager.get("download_history", [])
        self.history_table.setRowCount(len(history))
        
        for row, entry in enumerate(history):
            # Status
            status_icon = "✅" if entry.get("success", True) else "❌"
            self.history_table.setItem(row, 0, QTableWidgetItem(status_icon))
            
            # Filename
            filename = entry.get("filename", "Unknown")
            if len(filename) > 50:
                filename = filename[:47] + "..."
            filename_item = QTableWidgetItem(filename)
            filename_item.setToolTip(entry.get("filename", "Unknown"))
            self.history_table.setItem(row, 1, filename_item)
            
            # Date
            timestamp = entry.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.datetime.fromisoformat(timestamp)
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = "Unknown"
            else:
                date_str = "Unknown"
            self.history_table.setItem(row, 2, QTableWidgetItem(date_str))
            
            # URL
            url = entry.get("url", "")
            if len(url) > 60:
                display_url = url[:57] + "..."
            else:
                display_url = url
            url_item = QTableWidgetItem(display_url)
            url_item.setToolTip(url)
            self.history_table.setItem(row, 3, url_item)
            
    def copy_url(self, index):
        """Copy URL to clipboard"""
        row = index.row()
        history = self.settings_manager.get("download_history", [])
        
        if row < len(history):
            url = history[row].get("url", "")
            if url:
                clipboard = QApplication.clipboard()
                clipboard.setText(url)
                
                # Show temporary message
                QMessageBox.information(self, "Copied", f"URL copied to clipboard!")
                
    def clear_history(self):
        """Clear download history"""
        reply = QMessageBox.question(
            self, 
            "Clear History", 
            "Are you sure you want to clear all download history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.set("download_history", [])
            self.populate_history()


class InfoDialog(QDialog):
    """Dialog showing supported platforms and contact info"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Supported Platforms & Info")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("ℹ️ DownloadStation Information")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Create tabs or scrollable content
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Contact Information Section
        contact_frame = QFrame()
        contact_frame.setFrameStyle(QFrame.Shape.Box)
        contact_layout = QVBoxLayout(contact_frame)
        
        contact_title = QLabel("👨‍💻 Developer Contact")
        contact_title.setStyleSheet("font-size: 14px; font-weight: bold; margin: 5px;")
        contact_layout.addWidget(contact_title)
        
        # Email with copy button
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("📧 Email:"))
        email_input = QLineEdit("adichriz@gmail.com")
        email_input.setReadOnly(True)
        email_copy_btn = QPushButton("Copy")
        email_copy_btn.clicked.connect(lambda: self.copy_to_clipboard("adichriz@gmail.com"))
        email_layout.addWidget(email_input)
        email_layout.addWidget(email_copy_btn)
        contact_layout.addLayout(email_layout)
        
        contact_layout.addWidget(QLabel("💬 For bug reports, feature requests, or support questions"))
        
        scroll_layout.addWidget(contact_frame)
        
        # Supported Platforms Section
        platforms_frame = QFrame()
        platforms_frame.setFrameStyle(QFrame.Shape.Box)
        platforms_layout = QVBoxLayout(platforms_frame)
        
        platforms_title = QLabel("🌐 Supported Video Platforms")
        platforms_title.setStyleSheet("font-size: 14px; font-weight: bold; margin: 5px;")
        platforms_layout.addWidget(platforms_title)
        
        # Popular platforms
        popular_label = QLabel("🔥 Popular Platforms:")
        popular_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        platforms_layout.addWidget(popular_label)
        
        popular_platforms = [
            "• YouTube (videos, playlists, live streams)",
            "• Vimeo", "• Dailymotion", "• Facebook (public videos)",
            "• Instagram (videos, stories, reels)", "• TikTok",
            "• Twitter/X (videos)", "• Reddit (videos)",
            "• SoundCloud", "• Bandcamp"
        ]
        
        for platform in popular_platforms:
            label = QLabel(platform)
            label.setStyleSheet("margin-left: 15px;")
            platforms_layout.addWidget(label)
        
        # Educational platforms
        edu_label = QLabel("🎓 Educational Platforms:")
        edu_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        platforms_layout.addWidget(edu_label)
        
        edu_platforms = [
            "• Coursera", "• Udemy", "• Khan Academy",
            "• edX", "• LinkedIn Learning"
        ]
        
        for platform in edu_platforms:
            label = QLabel(platform)
            label.setStyleSheet("margin-left: 15px;")
            platforms_layout.addWidget(label)
        
        # Entertainment platforms
        entertainment_label = QLabel("🎬 Entertainment & News:")
        entertainment_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        platforms_layout.addWidget(entertainment_label)
        
        entertainment_platforms = [
            "• Twitch (VODs, clips)", "• BBC iPlayer",
            "• CNN", "• ESPN", "• Metacafe"
        ]
        
        for platform in entertainment_platforms:
            label = QLabel(platform)
            label.setStyleSheet("margin-left: 15px;")
            platforms_layout.addWidget(label)
        
        # Regional platforms
        regional_label = QLabel("🌍 Regional Platforms:")
        regional_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        platforms_layout.addWidget(regional_label)
        
        regional_platforms = [
            "• Bilibili (China)", "• Niconico (Japan)",
            "• VK (Russia)", "• And 1000+ more platforms!"
        ]
        
        for platform in regional_platforms:
            label = QLabel(platform)
            label.setStyleSheet("margin-left: 15px;")
            platforms_layout.addWidget(label)
        
        # Note
        note_label = QLabel("📝 Note: Some platforms may require login or have geographical restrictions.")
        note_label.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        platforms_layout.addWidget(note_label)
        
        scroll_layout.addWidget(platforms_frame)
        
        # App Info Section
        app_info_frame = QFrame()
        app_info_frame.setFrameStyle(QFrame.Shape.Box)
        app_info_layout = QVBoxLayout(app_info_frame)
        
        app_title = QLabel("📱 About DownloadStation")
        app_title.setStyleSheet("font-size: 14px; font-weight: bold; margin: 5px;")
        app_info_layout.addWidget(app_title)
        
        app_info = [
            "🚀 Fast and reliable video/audio downloads",
            "🎵 Support for audio-only downloads (MP3)",
            "📋 Playlist support with video selection",
            "⚙️ Multiple quality options",
            "🔄 Progress tracking with speed and ETA",
            "📁 Easy file management and access"
        ]
        
        for info in app_info:
            label = QLabel(info)
            label.setStyleSheet("margin-left: 15px;")
            app_info_layout.addWidget(label)
        
        scroll_layout.addWidget(app_info_frame)
        
        # Set scroll area
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Show temporary feedback
        sender = self.sender()
        original_text = sender.text()
        sender.setText("Copied!")
        
        # Reset after 1 second
        QTimer.singleShot(1000, lambda: self.reset_button(sender, original_text))
        
    def reset_button(self, button, original_text):
        """Reset button appearance"""
        button.setText(original_text)


class DonateDialog(QDialog):
    """Dialog showing donation information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Support DownloadStation")
        self.setFixedSize(400, 350)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("💝 Support DownloadStation")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Message
        message = QLabel("If you find DownloadStation useful, consider supporting the development!")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Donation options
        donate_frame = QFrame()
        donate_frame.setFrameStyle(QFrame.Shape.Box)
        donate_layout = QVBoxLayout(donate_frame)
        
        # MTN
        mtn_layout = QHBoxLayout()
        mtn_layout.addWidget(QLabel("📱 MTN Mobile Money:"))
        mtn_number = QLineEdit("0599784780")
        mtn_number.setReadOnly(True)
        mtn_copy_btn = QPushButton("Copy")
        mtn_copy_btn.clicked.connect(lambda: self.copy_to_clipboard("0599784780"))
        mtn_layout.addWidget(mtn_number)
        mtn_layout.addWidget(mtn_copy_btn)
        donate_layout.addLayout(mtn_layout)

        # Telecel
        telecel_layout = QHBoxLayout()
        telecel_layout.addWidget(QLabel("📱 Telecel Cash:"))
        telecel_number = QLineEdit("0502961714")
        telecel_number.setReadOnly(True)
        telecel_copy_btn = QPushButton("Copy")
        telecel_copy_btn.clicked.connect(lambda: self.copy_to_clipboard("0502961714"))
        telecel_layout.addWidget(telecel_number)
        telecel_layout.addWidget(telecel_copy_btn)
        donate_layout.addLayout(telecel_layout)

        # Mail
        mail_layout = QHBoxLayout()
        mail_layout.addWidget(QLabel("✉️ Mail:"))
        mail_address = QLineEdit("adichriz@gmail.com")
        mail_address.setReadOnly(True)
        mail_copy_btn = QPushButton("Copy")
        mail_copy_btn.clicked.connect(lambda: self.copy_to_clipboard("adichriz@gmail.com"))
        mail_layout.addWidget(mail_address)
        mail_layout.addWidget(mail_copy_btn)
        donate_layout.addLayout(mail_layout)

        layout.addWidget(donate_frame)

        # Thank you message
        thanks = QLabel("Thank you for your support! 🙏\nEvery contribution helps improve DownloadStation Application.")
        thanks.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thanks.setWordWrap(True)
        layout.addWidget(thanks)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Show temporary feedback
        sender = self.sender()
        original_text = sender.text()
        sender.setText("Copied!")
        
        # Reset after 1 second
        QTimer.singleShot(1000, lambda: self.reset_button(sender, original_text))
        
    def reset_button(self, button, original_text):
        """Reset button appearance"""
        button.setText(original_text)
        button.setStyleSheet("")
