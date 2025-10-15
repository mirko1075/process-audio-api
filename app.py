"""Flask entrypoint for the AI transcription backend."""
from __future__ import annotations

from api import create_app

app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
