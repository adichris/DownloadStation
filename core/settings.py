import pathlib
import os
import datetime
import json


class SettingsManager:
    """Manage application settings and user preferences"""
    
    def __init__(self):
        self.settings_file = pathlib.Path.cwd() / "settings.json"
        path_ = os.path.join(os.path.expanduser('~'), 'Downloads', "DownloadStation")
        if not os.path.exists(path_):
            path_ = os.mkdir(path_)
        self.default_settings = {
            "download_path":path_,
            "audio_only": False,
            "single_video_only": True,
            "quality": "720p",
            "window_geometry": {
                "x": 200,
                "y": 200,
                "width": 700,
                "height": 500
            },
            "recent_urls": [],
            "download_history": []
        }
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load settings from file"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to handle new settings
                    settings = self.default_settings.copy()
                    settings.update(loaded_settings)
                    return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        return self.default_settings.copy()
    
    def save_settings(self):
        """Save settings to file"""
        try:
            # Ensure directory exists
            self.settings_file.parent.mkdir(exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key, default=None):
        """Get setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set setting value"""
        self.settings[key] = value
        self.save_settings()
    
    def add_recent_url(self, url):
        """Add URL to recent list"""
        recent_urls = self.settings.get("recent_urls", [])
        
        # Remove if already exists
        if url in recent_urls:
            recent_urls.remove(url)
        
        # Add to beginning
        recent_urls.insert(0, url)
        
        # Keep only last 10
        recent_urls = recent_urls[:10]
        
        self.set("recent_urls", recent_urls)
    
    def add_download_history(self, url, filename, success=True):
        """Add download to history"""
        history = self.settings.get("download_history", [])
        
        entry = {
            "url": url,
            "filename": filename,
            "timestamp": datetime.datetime.now().isoformat(),
            "success": success
        }
        
        history.insert(0, entry)
        
        # Keep only last 50 entries
        history = history[:50]
        
        self.set("download_history", history)
