import os
import pandas as pd
from datetime import datetime
from config import INCIDENT_CSV, CSV_COLUMNS


def merge_outputs(detection: dict, classification: dict) -> dict:
    merged = {
        "timestamp":         detection.get("timestamp", datetime.now().isoformat(timespec="seconds")),
        "frame_id":          detection.get("frame_id", 0),
        "source":            "merged",
        "accident_detected": detection.get("accident_detected", False),
        "detection_conf":    detection.get("detection_conf", 0.0),
        "bbox_x1":           detection.get("bbox_x1"),
        "bbox_y1":           detection.get("bbox_y1"),
        "bbox_x2":           detection.get("bbox_x2"),
        "bbox_y2":           detection.get("bbox_y2"),
        "accident_class":    classification.get("accident_class", "no_accident"),
        "class_conf":        classification.get("class_conf", 0.0),
        "severity":          classification.get("severity", "none"),
        "location_lat":      detection.get("location_lat", 0.0),
        "location_lng":      detection.get("location_lng", 0.0),
        "lanes_blocked":     _estimate_lanes_blocked(classification.get("accident_class", "no_accident")),
        "road_name":         detection.get("road_name", "Unknown Road"),
        "speed_zone_kmph":   detection.get("speed_zone_kmph", 60),
        "camera_id":         detection.get("camera_id", "CAM-01"),
    }
    if not merged["accident_detected"]:
        merged["severity"]       = "none"
        merged["accident_class"] = "no_accident"
    return merged


def _estimate_lanes_blocked(accident_class: str) -> int:
    mapping = {
        "rear_end": 1, "head_on": 2, "side_impact": 1, "pile_up": 3,
        "rollover": 2, "pedestrian_hit": 1, "cyclist_hit": 1, "no_accident": 0,
    }
    return mapping.get(accident_class, 1)


def append_to_csv(row: dict) -> None:
    os.makedirs(os.path.dirname(INCIDENT_CSV), exist_ok=True)
    df_row = pd.DataFrame([row], columns=CSV_COLUMNS)
    if not os.path.exists(INCIDENT_CSV):
        df_row.to_csv(INCIDENT_CSV, index=False)
    else:
        df_row.to_csv(INCIDENT_CSV, mode="a", header=False, index=False)


def load_incident_log() -> pd.DataFrame:
    if not os.path.exists(INCIDENT_CSV):
        return pd.DataFrame(columns=CSV_COLUMNS)
    return pd.read_csv(INCIDENT_CSV)


def get_latest_incident() -> dict | None:
    df = load_incident_log()
    active = df[df["accident_detected"] == True]
    if active.empty:
        return None
    return active.iloc[-1].to_dict()
