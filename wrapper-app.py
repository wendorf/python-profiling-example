#!/usr/bin/env python
"""
Wrapper script to run the Flask app with Gunicorn in a way that Scalene can profile.

This allows you to profile the real production setup with Scalene:
    scalene --cpu --html --profile-interval=15 --outfile=/tmp/scalene.html wrapper-app.py
"""
import os
from gunicorn.app.base import BaseApplication
from app import app


class StandaloneApplication(BaseApplication):
    """Gunicorn application that loads the Flask app in the main process."""

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        """Load Gunicorn configuration from options."""
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        """Return the WSGI application."""
        return self.application


if __name__ == "__main__":
    # Configuration for Gunicorn
    options = {
        'bind': f'0.0.0.0:{os.environ.get("PORT", 8000)}',
        'workers': 1,  # Single worker so Scalene can profile it
        'threads': 4,  # Use threads for concurrency
        'worker_class': 'gthread',
        'timeout': 120,
        'accesslog': '-',
        'errorlog': '-',
    }

    print(f"Starting Gunicorn with {options['workers']} worker, {options['threads']} threads on {options['bind']}")
    StandaloneApplication(app, options).run()
