import sys
import os
from cx_Freeze import setup, Executable

build_exe_options = {
    "include_msvcrt": True,
}

base = "Win32GUI" if sys.platform == "win32" else None

setup(
    name="DownloadStation",
    version="1.0.0",
    description="Video and Audio Downloader",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",
            base=base,
            target_name="DownloadStation.exe"
        )
    ]
)