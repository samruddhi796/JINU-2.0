import threading
import webview
import time
import os
import sys
from backend.server import run_server
from backend.watcher import start_watcher

def start_backend():
    print("Starting FastAPI backend...")
    run_server()

if __name__ == '__main__':
    # Start the Watcher Agent
    start_watcher()

    # Start the backend server in a background thread
    # daemon=True ensures the thread dies when the main program exits
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    # Give the backend a moment to start
    time.sleep(1)

    # Path to the frontend
    frontend_path = os.path.join(os.path.dirname(__file__), 'frontend', 'index.html')
    
    # Create the PyWebView window
    print("Starting JINU 2.0 UI...")
    webview.create_window(
        title='JINU', 
        url=frontend_path,
        width=400, 
        height=600,
        min_size=(350, 500)
    )
    
    # Start the webview event loop
    webview.start()
