import os
import sys
import tempfile

def get_default_temp_dir():
    """OSに応じたデフォルトの一時ディレクトリを取得"""
    if sys.platform == 'win32':
        return os.path.join(os.environ.get('LOCALAPPDATA', tempfile.gettempdir()), 'Mpeg4Toolbox', 'temp')
    elif sys.platform == 'darwin':
        return os.path.join(os.path.expanduser('~/Library/Application Support/Mpeg4Toolbox'), 'temp')
    else:  # Linux/Unix
        return os.path.join(os.path.expanduser('~/.local/share/Mpeg4Toolbox'), 'temp')

def format_duration(seconds):
    """秒数をH:M:S形式に変換"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def format_bitrate(bitrate):
    """ビットレートを適切な単位で表示"""
    if bitrate >= 1000000:
        return f"{bitrate/1000000:.2f} Mbps"
    else:
        return f"{bitrate/1000:.1f} kbps"
