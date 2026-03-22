import os
from datetime import datetime
from config import DETECTOR_MODEL_PATH, DETECTION_CONF_THRESHOLD


class AccidentDetector:
    def __init__(self):
        self._model = None
        self.model_path = DETECTOR_MODEL_PATH

    def _load_model(self):
        if self._model is None:
            try:
                from ultralytics import YOLO
                if not os.path.exists(self.model_path):
                    raise FileNotFoundError(
                        f"Detector model not found at: {self.model_path}\n"
                        "Place your detector_best.pt inside the models/ folder."
                    )
                self._model = YOLO(self.model_path)
                print(f"[Detector] Model loaded from {self.model_path}")
            except ImportError:
                raise ImportError("ultralytics not installed. Run: pip install ultralytics")

    def run(self, source, frame_id: int = 0, camera_id: str = "CAM-01",
            location_lat: float = 40.758, location_lng: float = -73.985,
            road_name: str = "Unknown Road", speed_zone_kmph: int = 60) -> dict:
        self._load_model()
        results = self._model(source, conf=DETECTION_CONF_THRESHOLD, verbose=False)

        output = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "frame_id": frame_id, "source": "detector",
            "accident_detected": False, "detection_conf": 0.0,
            "bbox_x1": None, "bbox_y1": None, "bbox_x2": None, "bbox_y2": None,
            "camera_id": camera_id,
            "location_lat": location_lat, "location_lng": location_lng,
            "road_name": road_name, "speed_zone_kmph": speed_zone_kmph,
        }

        best_conf = 0.0
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                conf = float(box.conf[0])
                if conf > best_conf:
                    best_conf = conf
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    output["accident_detected"] = True
                    output["detection_conf"]    = round(conf, 4)
                    output["bbox_x1"]           = round(x1, 1)
                    output["bbox_y1"]           = round(y1, 1)
                    output["bbox_x2"]           = round(x2, 1)
                    output["bbox_y2"]           = round(y2, 1)

        return output
