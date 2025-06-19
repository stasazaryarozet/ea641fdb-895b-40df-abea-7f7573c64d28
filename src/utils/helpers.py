"""
Helper utilities for Tilda migration agent
"""

import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse


def generate_file_hash(content: bytes) -> str:
    """Generate MD5 hash for file content"""
    return hashlib.md5(content).hexdigest()


def get_file_extension(url: str, content_type: str = None) -> str:
    """Get file extension from URL or content type"""
    # Try to get from URL
    parsed = urlparse(url)
    path = parsed.path
    if '.' in path:
        return path.split('.')[-1].lower()
    
    # Try to get from content type
    if content_type:
        mime_type, _ = mimetypes.parse_header(content_type)
        extension = mimetypes.guess_extension(mime_type)
        if extension:
            return extension[1:]  # Remove leading dot
    
    return 'bin'


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    import re
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + ('.' + ext if ext else '')
    
    return filename or 'file'


def create_directory_structure(base_path: Path, structure: Dict[str, Any]):
    """Create directory structure"""
    for name, content in structure.items():
        path = base_path / name
        if isinstance(content, dict):
            path.mkdir(parents=True, exist_ok=True)
            create_directory_structure(path, content)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)


def merge_configs(default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge user configuration with defaults"""
    merged = default_config.copy()
    
    def merge_dicts(d1, d2):
        for key, value in d2.items():
            if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
                merge_dicts(d1[key], value)
            else:
                d1[key] = value
    
    merge_dicts(merged, user_config)
    return merged


def validate_url(url: str) -> bool:
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_file_size_display(size_bytes: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def create_backup(file_path: Path) -> Path:
    """Create backup of file"""
    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
    if file_path.exists():
        import shutil
        shutil.copy2(file_path, backup_path)
    return backup_path


def restore_backup(backup_path: Path) -> bool:
    """Restore file from backup"""
    original_path = backup_path.with_suffix('')
    if backup_path.exists():
        import shutil
        shutil.copy2(backup_path, original_path)
        return True
    return False 