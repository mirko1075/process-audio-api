from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import subprocess
import time
import threading
import socket

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, process, ignore_dirs, ignore_files, debounce_time=1):
        self.process = process
        self.ignore_dirs = ignore_dirs
        self.ignore_files = ignore_files
        self.debounce_time = debounce_time
        self.last_event_time = 0
        self.lock = threading.Lock()

    def on_any_event(self, event):
        # Ignore changes in specified directories or files
        if any(ignored in event.src_path for ignored in self.ignore_dirs):
            return
        if any(event.src_path.endswith(ignored) for ignored in self.ignore_files):
            return

        with self.lock:
            current_time = time.time()
            if current_time - self.last_event_time < self.debounce_time:
                return  # Ignore rapid consecutive changes
            self.last_event_time = current_time

            print(f"Change detected: {event.src_path}")

            # Terminate the existing process only if it is still running
            if self.process.poll() is None:
                print("Terminating existing process...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()

            # Ensure the port is free before restarting the process
            wait_for_port_to_be_free(5000)

            # Start a new process
            self.process = subprocess.Popen(["python", "app.py"])

def is_port_in_use(port):
    """
    Check if a port is already in use.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def wait_for_port_to_be_free(port, retries=5, delay=1):
    """
    Wait for a port to be free before proceeding.
    """
    for _ in range(retries):
        if not is_port_in_use(port):
            return
        print(f"Waiting for port {port} to be free...")
        time.sleep(delay)
    raise RuntimeError(f"Port {port} is still in use after {retries} retries.")

if __name__ == "__main__":
    path = "."  # Directory to watch
    ignore_dirs = ["./venv", "__pycache__", ".git", 'tmp']  # Directories to ignore
    ignore_files = [".env"]  # Files to ignore
    debounce_time = 3  # Debounce time to avoid frequent restarts

    # Check if the port is free before starting
    port = 5000
    wait_for_port_to_be_free(port)

    # Start the initial process
    process = subprocess.Popen(["python", "app.py"])

    # Configure watchdog
    event_handler = ChangeHandler(process, ignore_dirs, ignore_files, debounce_time)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        process.terminate()
    observer.join()
