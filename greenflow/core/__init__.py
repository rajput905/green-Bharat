# core/__init__.py
# Re-exports AppSettings and settings for convenience
from .config import AppSettings, settings

__all__ = ['AppSettings', 'settings']
