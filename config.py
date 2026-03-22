import os
from dotenv import load_dotenv

load_dotenv()

HF_API_KEY: str   = os.getenv("HF_API_KEY", "")
HF_MODEL: str     = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
HF_API_URL: str   = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

CLASSIFIER_MODEL_PATH: str = os.getenv("CLASSIFIER_MODEL_PATH", "models/classifier_best.pt")
DETECTOR_MODEL_PATH: str   = os.getenv("DETECTOR_MODEL_PATH",   "models/detector_best.pt")

DETECTION_CONF_THRESHOLD: float    = 0.45
CLASSIFICATION_CONF_THRESHOLD: float = 0.50

CITY_NAME: str       = os.getenv("CITY_NAME", "Gandhinagar, Gujarat, India")
MAP_CENTER_LAT: float = float(os.getenv("MAP_CENTER_LAT", "23.2166"))
MAP_CENTER_LNG: float = float(os.getenv("MAP_CENTER_LNG", "72.6417"))
MAP_ZOOM: int         = 13

FEED_INTERVAL: int = int(os.getenv("FEED_INTERVAL_SECONDS", "5"))

INCIDENT_CSV: str = os.getenv("INCIDENT_CSV", "data/incident_log.csv")
SAMPLE_CSV: str   = os.getenv("SAMPLE_CSV",   "data/sample_traffic.csv")

ACCIDENT_CLASSES = [
    "rear_end", "head_on", "side_impact", "pile_up",
    "rollover", "pedestrian_hit", "cyclist_hit", "no_accident",
]

SEVERITY_MAP = {
    "rear_end": "medium", "head_on": "high", "side_impact": "medium",
    "pile_up": "high", "rollover": "high", "pedestrian_hit": "high",
    "cyclist_hit": "medium", "no_accident": "none",
}

CSV_COLUMNS = [
    "timestamp", "frame_id", "source", "accident_detected", "detection_conf",
    "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
    "accident_class", "class_conf", "severity",
    "location_lat", "location_lng", "lanes_blocked",
    "road_name", "speed_zone_kmph", "camera_id",
]

EMAIL_USER: str      = os.getenv("EMAIL_USER", "")
EMAIL_PASS: str      = os.getenv("EMAIL_PASS", "")
HOSPITAL_EMAIL: str  = os.getenv("HOSPITAL_EMAIL", "")
FIRE_DEPT_EMAIL: str = os.getenv("FIRE_DEPT_EMAIL", "")
