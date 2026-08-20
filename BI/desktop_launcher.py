import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

# Setup base directory depending on PyInstaller bundle or raw Python
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BI.settings')

import django
django.setup()

from django.core.management import call_command
from BI.wsgi import application
from waitress import serve

def open_browser():
    """Opens local browser window to APEX BI Studio after server starts."""
    time.sleep(1.5)
    print("Opening APEX BI Studio in default browser: http://127.0.0.1:8000/")
    webbrowser.open("http://127.0.0.1:8000/")

def main():
    print("================================================================================")
    print("            APEX BI STUDIO — DESKTOP STANDALONE APPLICATION ENGINE             ")
    print("================================================================================")
    print("1. Running database migrations...")
    try:
        call_command('migrate', interactive=False)
        print("   Database schema synchronized OK.")
    except Exception as e:
        print(f"   Database migration note: {e}")

    print("2. Launching background browser thread...")
    threading.Thread(target=open_browser, daemon=True).start()

    print("3. Starting embedded production WSGI server on http://127.0.0.1:8000/ ...")
    print("Press Ctrl+C in this console to stop the server.")
    serve(application, host='127.0.0.1', port=8000, threads=6)

if __name__ == '__main__':
    main()
