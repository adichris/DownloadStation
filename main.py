import pathlib
import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.main_window import DownloadStation, check_ffmpeg, show_ffmpeg_warning
from PyQt6.QtGui import QIcon


if __name__ == '__main__':
    app = QApplication(sys.argv)
    BASE_DIR = pathlib.Path(__file__).resolve().parent
    app.setApplicationName("DownloadStation")
    app.setWindowIcon(QIcon(str(BASE_DIR /  "logo.png")))
    window = DownloadStation()
    window.show()

    # Check for FFmpeg
    if not check_ffmpeg():
        show_ffmpeg_warning()
    
    sys.exit(app.exec())

