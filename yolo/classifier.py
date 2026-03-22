import os
from datetime import datetime
from config import CLASSIFIER_MODEL_PATH, CLASSIFICATION_CONF_THRESHOLD, SEVERITY_MAP


class AccidentClassifier:
    def __init__(self):
        self._model = None
        self.model_path = CLASSIFIER_MODEL_PATH

    def _load_model(self):
        if self._model is None:
            try:
                from ultralytics import YOLO
                if not os.path.exists(self.model_path):
                    raise FileNotFoundError(
                        f"Classifier model not found at: {self.model_path}\n"
                        "Place your classifier_best.pt inside the models/ folder."
                    )
                self._model = YOLO(self.model_path)
                print(f"[Classifier] Model loaded from {self.model_path}")
            except ImportError:
                raise ImportError("ultralytics not installed. Run: pip install ultralytics")

    def run(self, source, frame_id: int = 0, camera_id: str = "CAM-01") -> dict:
        self._load_model()
        results = self._model(source, verbose=False)

        output = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "frame_id": frame_id, "source": "classifier",
            "accident_class": "no_accident", "class_conf": 0.0,
            "severity": "none", "camera_id": camera_id,
        }

        for result in results:
            if result.probs is None:
                continue
            top_idx  = int(result.probs.top1)
            top_conf = float(result.probs.top1conf)
            if top_conf >= CLASSIFICATION_CONF_THRESHOLD:
                class_name = result.names[top_idx]
                output["accident_class"] = class_name
                output["class_conf"]     = round(top_conf, 4)
                output["severity"]       = SEVERITY_MAP.get(class_name, "low")

        return output
