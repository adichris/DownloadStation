import pathlib
import os
from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import datetime


class PlaylistInfoThread(QThread):
    """Thread for loading playlist information"""
    
    info_loaded = pyqtSignal(dict)
    loading_failed = pyqtSignal(str)
    progress_updated = pyqtSignal(int, int, str)  # total_items, loaded_items, current_title
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.is_cancelled = False
        self.start_time = None
        
    def get_elapsed_time(self):
        """Get elapsed time since start"""
        if self.start_time:
            return (datetime.datetime.now() - self.start_time).total_seconds()
        return 0
        
    def run(self):
        """Load playlist information with progress tracking"""
        self.start_time = datetime.datetime.now()
        
        try:
            # First pass: Get playlist structure with flat extraction
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # Get basic info only
                'ignoreerrors': True,
                'no_check_certificate': True,
                'extractor_retries': 2,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.is_cancelled:
                    return
                
                self.progress_updated.emit(0, 0, "Discovering playlist...")
                
                info = ydl.extract_info(self.url, download=False)
                
                if self.is_cancelled:
                    return
                
                if info.get('_type') == 'playlist' and 'entries' in info:
                    entries = info['entries']
                    total_entries = len(entries)
                    
                    # Filter and prepare entries without detailed extraction
                    valid_entries = []
                    loaded_count = 0
                    
                    for i, entry in enumerate(entries):
                        if self.is_cancelled:
                            return
                            
                        if entry is not None and entry.get('id'):
                            # Create a complete entry with the information we have
                            enhanced_entry = {
                                'id': entry.get('id'),
                                'video_id': entry.get('id'),  # Ensure video_id is set
                                'title': entry.get('title', f'Video {i+1}'),
                                'duration': entry.get('duration'),
                                'uploader': entry.get('uploader', 'Unknown'),
                                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                                'webpage_url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                                '_type': 'url',
                                'ie_key': 'Youtube'
                            }
                            
                            valid_entries.append(enhanced_entry)
                            loaded_count += 1
                            
                            # Update progress
                            title = entry.get('title', f'Video {i+1}')
                            self.progress_updated.emit(total_entries, loaded_count, title)
                            self.msleep(20)  # Small delay for UI updates
                    
                    # Update the info with prepared entries
                    info['entries'] = valid_entries
                    
                    if not self.is_cancelled:
                        self.progress_updated.emit(total_entries, loaded_count, "Finalizing...")
                        self.info_loaded.emit(info)
                else:
                    # Single video case
                    if not self.is_cancelled:
                        playlist_info = {
                            'title': info.get('title', 'Single Video'),
                            'entries': [info],
                            '_type': 'playlist'
                        }
                        self.info_loaded.emit(playlist_info)
                    
        except Exception as e:
            if not self.is_cancelled:
                self.loading_failed.emit(f"Error loading playlist: {str(e)}")
                
                
    def cancel(self):
        """Cancel loading"""
        self.is_cancelled = True

