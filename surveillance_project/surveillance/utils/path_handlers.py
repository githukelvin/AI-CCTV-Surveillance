import os
from django.conf import settings
from pathlib import Path


def get_media_url(file_path):
    """Convert a filesystem path to a media URL"""
    # If path is already a URL, return it
    if file_path.startswith('/media/'):
        return file_path

    # Convert full filesystem path to media URL
    if isinstance(file_path, str):
        file_path = Path(file_path)

    # Get path relative to MEDIA_ROOT
    try:
        relative_path = file_path.relative_to(settings.MEDIA_ROOT)
    except ValueError:
        # If file_path isn't under MEDIA_ROOT, try to extract the path after 'media'
        parts = file_path.parts
        if 'media' in parts:
            media_index = parts.index('media')
            relative_path = Path(*parts[media_index + 1:])
        else:
            relative_path = file_path

    # Convert to URL format
    url_path = f'/media/{relative_path}'
    return url_path


def get_filesystem_path(url_path):
    """Convert a media URL to filesystem path"""
    # If path is already a filesystem path, return it
    if not url_path.startswith('/media/'):
        return url_path

    # Remove '/media/' prefix and convert to filesystem path
    relative_path = url_path.replace('/media/', '', 1)
    return os.path.join(settings.MEDIA_ROOT, relative_path)