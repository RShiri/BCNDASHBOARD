import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class MatchCacheHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".json") and "match_" in event.src_path and "_cache" in event.src_path:
            print(f"New match cache detected: {event.src_path}")
            print("Triggering ETL pipeline...")
            # Run the parser
            try:
                subprocess.run(
                    ["python", "-m", "EliteAnalytics.backend.parser"], 
                    cwd=os.path.dirname(_ROOT),
                    check=True
                )
                print("ETL pipeline completed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"ETL pipeline failed: {e}")

def run_watcher():
    path_to_watch = _ROOT  # Watch the EliteAnalytics folder or the root BCNPROJECT folder
    # For now, let's watch the directory above EliteAnalytics where match_1914105_cache.json is
    root_path = os.path.dirname(_ROOT)
    data_path = os.path.join(root_path, "assets", "data")
    
    event_handler = MatchCacheHandler()
    observer = Observer()
    observer.schedule(event_handler, data_path, recursive=False)
    observer.start()
    print(f"Watching for new match cache JSONs in {data_path} ...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    run_watcher()
