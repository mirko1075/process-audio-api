"""Compatibility shim package so code can import `core` while the real package
is still located in `flask_app`.

This sets the package __path__ to the existing `flask_app` directory so
`import core.services.video_transcription` will load from `flask_app/services`.
"""
import os
import importlib

# Point core package path to the existing flask_app directory
_here = os.path.dirname(__file__)
_flask_app_path = os.path.abspath(os.path.join(_here, '..', 'flask_app'))
if os.path.isdir(_flask_app_path):
    __path__ = [_flask_app_path]

# Re-export top-level symbols from flask_app for convenience
try:
    _mod = importlib.import_module('flask_app')
    for _name in dir(_mod):
        if _name.startswith('_'):
            continue
        try:
            globals()[_name] = getattr(_mod, _name)
        except Exception:
            # ignore attributes that can't be copied
            pass
except Exception:
    # if flask_app isn't importable yet, don't fail import of core
    pass

__all__ = [n for n in globals() if not n.startswith('_')]
