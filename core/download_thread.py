
import pathlib
import os
from PyQt6.QtCore import QThread, pyqtSignal
import yt_dlp
import datetime
import sys


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for cx_Freeze"""
    if getattr(sys, 'frozen', False):
        # Running in a bundle
        base_path = os.path.dirname(sys.executable)
    else:
        # Running in development
        base_path = os.path.dirname(__file__)
    
    return os.path.join(base_path, relative_path)


    
    
class DownloadThread(QThread):
    """Simple download thread"""
    
    progress_updated = pyqtSignal(int, str, str, str)  # progress, speed, file_size, eta
    download_completed = pyqtSignal(str, str)     # filename, file_path
    download_failed = pyqtSignal(str)        # error message
    
    def __init__(self, url, output_path, is_audio_only=False, quality="720p", no_playlist=True, playlist_entries=None):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.is_audio_only = is_audio_only
        self.quality = quality
        self.no_playlist = no_playlist
        self.playlist_entries = playlist_entries or []
        self.is_cancelled = False
        self._ydl = None  # Store reference to yt-dlp instance
        self.downloaded_files = []  # Track downloaded files
    
    def log_download(self, url, success):
        with open(pathlib.Path.cwd() / "logs/history.log", "a") as f:
            f.write(f"{datetime.datetime.now()} - {url} - {'Success' if success else 'Failed'}\n")
        
    def run(self):
        """Run the download"""
        try:
            # Setup yt-dlp options
            ydl_opts = {
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'noplaylist': self.no_playlist,
                'quiet': True,
                'no_warnings': True,
            }
            if self.is_audio_only:
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                    if self.quality == "Best":
                        ydl_opts['format'] = 'best[ext=mp4]/best'
                    elif self.quality == "1080p":
                        ydl_opts['format'] = 'best[height<=1080][ext=mp4]/best[height<=1080]/best[ext=mp4]/best'
                    elif self.quality == "720p":
                        ydl_opts['format'] = 'best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best'
                    elif self.quality == "480p":
                        ydl_opts['format'] = 'best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best'
                    else:
                        ydl_opts['format'] = 'best[ext=mp4]/best'
                    
            ffmpeg_path = get_resource_path("ffmpeg.exe")
            if os.path.exists(ffmpeg_path):
                ydl_opts['ffmpeg_location'] = ffmpeg_path
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._ydl = ydl  # Store reference for cancellation
                
                if self.is_cancelled:
                    return
                
           # Handle playlist entries or single URL
            if self.playlist_entries:
                # Download selected playlist entries
                for entry in self.playlist_entries:
                    if self.is_cancelled:
                        break
                    
                    # Use the prepared URL from playlist loading
                    video_url = entry.get('url') or entry.get('webpage_url')
                    
                    if video_url:
                        try:
                            # Create individual ydl options for each video to ensure quality is applied
                            individual_opts = ydl_opts.copy()
                            individual_opts['noplaylist'] = True  # Ensure no playlist processing
                            
                            with yt_dlp.YoutubeDL(individual_opts) as individual_ydl:
                                individual_ydl.download([video_url])
                        except Exception as e:
                            self.download_failed.emit(f"Failed to download {video_url}: {e}")
                            
                            # Fallback: try with video ID if URL fails
                            video_id = entry.get('id') or entry.get('video_id')
                            if video_id:
                                fallback_url = f"https://www.youtube.com/watch?v={video_id}"
                                try:
                                    individual_opts = ydl_opts.copy()
                                    individual_opts['noplaylist'] = True
                                    with yt_dlp.YoutubeDL(individual_opts) as fallback_ydl:
                                        fallback_ydl.download([fallback_url])
                                except Exception as e2:
                                    self.download_failed.emit(f"Fallback download also failed: {e2}")
                
                
                if not self.is_cancelled and self.downloaded_files:
                    first_file = self.downloaded_files[0]
                    self.download_completed.emit(f"{len(self.playlist_entries)} videos from playlist", first_file)    
                    
            else:
                    
                    info = ydl.extract_info(self.url, download=False)                    
                    if not self.is_cancelled:
                        ydl.download([self.url])
                        filename = info.get('title', 'Unknown')
                        if not self.is_cancelled and self.downloaded_files:
                            self.download_completed.emit(filename, self.downloaded_files[0])
                        else:
                            error_msg = "Download completed but no files were found. This may indicate a download failure or file access issue."
                            self.download_failed.emit(error_msg)
                                
        except Exception as e:
            if not self.is_cancelled:
                self.download_failed.emit(str(e))
        finally:
            self._ydl = None
    
    def progress_hook(self, d):
        """Handle progress updates"""
        if d['status'] == 'downloading' and not self.is_cancelled:
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            speed = d.get('speed', 0) or 0
            eta = d.get('eta', 0) or 0
            
            if total > 0:
                progress = int((downloaded / total) * 100)
            else:
                progress = 0
            
            speed_text = self.format_speed(speed)
            file_size_text = self.format_file_size(total) if total > 0 else "Unknown"
            eta_text = self.format_eta(eta) if eta > 0 else "Unknown"
            
            self.progress_updated.emit(progress, speed_text, file_size_text, eta_text)
            
        elif d['status'] == 'finished':
            # Track completed files
            filepath = d.get('filename', '')
            if filepath and filepath not in self.downloaded_files:
                self.downloaded_files.append(filepath)
    
    def format_speed(self, speed):
        """Format download speed"""
        if speed < 1024:
            return f"{speed:.0f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        else:
            return f"{speed / (1024 * 1024):.1f} MB/s"
    
    def format_file_size(self, size):
        """Format file size"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    
    def format_eta(self, eta):
        """Format estimated time of arrival"""
        if eta < 60:
            return f"{eta:.0f}s"
        elif eta < 3600:
            minutes = eta // 60
            seconds = eta % 60
            return f"{minutes:.0f}m {seconds:.0f}s"
        else:
            hours = eta // 3600
            minutes = (eta % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"
    
    def cancel(self):
        """Cancel download"""
        self.is_cancelled = True
        # Force terminate the thread if it's running
        if self.isRunning():
            self.terminate()
            self.wait(2000)  # Wait up to 2 seconds for clean termination
