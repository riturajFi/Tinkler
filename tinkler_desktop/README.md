Tinkler Desktop is a minimal Electron shell for the local Tinkler backend.

Usage:

1. Install dependencies:
   `npm install --prefix tinkler_desktop`
2. Start the desktop app:
   `npm --prefix tinkler_desktop start`

The app attempts to start the local backend automatically by running:
`.venv/bin/python -m tinkler_backend`

If your backend is already running, the desktop app will connect to it instead.
