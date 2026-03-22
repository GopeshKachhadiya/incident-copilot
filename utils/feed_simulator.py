import os
import time
import threading
import pandas as pd
from datetime import datetime
from config import SAMPLE_CSV, INCIDENT_CSV, CSV_COLUMNS, FEED_INTERVAL
from yolo.csv_merger import append_to_csv


DEFAULT_ROWS = [
    {
        "timestamp": "2026-03-21T14:32:05", "frame_id": 1, "source": "merged",
        "accident_detected": False, "detection_conf": 0.12,
        "bbox_x1": None, "bbox_y1": None, "bbox_x2": None, "bbox_y2": None,
        "accident_class": "no_accident", "class_conf": 0.95, "severity": "none",
        "location_lat": 23.2166, "location_lng": 72.6417,
        "lanes_blocked": 0, "road_name": "CH Road / S1 Circle",
        "speed_zone_kmph": 60, "camera_id": "CAM-GNR-01",
    },
    {
        "timestamp": "2026-03-21T14:32:15", "frame_id": 3, "source": "merged",
        "accident_detected": True, "detection_conf": 0.87,
        "bbox_x1": 320.0, "bbox_y1": 180.0, "bbox_x2": 640.0, "bbox_y2": 400.0,
        "accident_class": "rear_end", "class_conf": 0.91, "severity": "medium",
        "location_lat": 23.2166, "location_lng": 72.6417,
        "lanes_blocked": 1, "road_name": "CH Road / S1 Circle",
        "speed_zone_kmph": 60, "camera_id": "CAM-GNR-01",
    },
    {
        "timestamp": "2026-03-21T14:32:25", "frame_id": 5, "source": "merged",
        "accident_detected": True, "detection_conf": 0.96,
        "bbox_x1": 300.0, "bbox_y1": 160.0, "bbox_x2": 660.0, "bbox_y2": 430.0,
        "accident_class": "pile_up", "class_conf": 0.88, "severity": "high",
        "location_lat": 23.155, "location_lng": 72.665,
        "lanes_blocked": 3, "road_name": "PDPU Road Junction",
        "speed_zone_kmph": 50, "camera_id": "CAM-GNR-PDPU",
    },
]


class FeedSimulator:
    def __init__(self):
        self._running = False
        self._thread  = None
        self._rows    = self._load_rows()
        self._index   = 0

    def _load_rows(self) -> list:
        if os.path.exists(SAMPLE_CSV):
            df = pd.read_csv(SAMPLE_CSV)
            return df.to_dict("records")
        return DEFAULT_ROWS

    def start(self):
        if self._running:
            return
        if os.path.exists(INCIDENT_CSV):
            os.remove(INCIDENT_CSV)
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[FeedSimulator] Started — replaying traffic feed.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        print("[FeedSimulator] Stopped.")

    def _run_loop(self):
        while self._running:
            row = dict(self._rows[self._index % len(self._rows)])
            row["timestamp"] = datetime.now().isoformat(timespec="seconds")
            row["frame_id"]  = self._index + 1
            for col in CSV_COLUMNS:
                row.setdefault(col, None)
            append_to_csv(row)
            self._index += 1
            time.sleep(FEED_INTERVAL)

    @property
    def current_frame(self) -> int:
        return self._index
