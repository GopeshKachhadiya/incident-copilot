"""
utils/yolo_pipeline.py
End-to-end YOLO pipeline: video/webcam → detector → classifier → CSV.

Run this as a standalone script during actual inference:
    python utils/yolo_pipeline.py --source path/to/video.mp4 --camera CAM-01

Or import YoloPipeline for programmatic use.
"""

import os
import cv2
import time
import argparse
from datetime import datetime

from yolo.detector   import AccidentDetector
from yolo.classifier import AccidentClassifier
from yolo.csv_merger import merge_outputs, append_to_csv
from config import DETECTION_CONF_THRESHOLD, MAP_CENTER_LAT, MAP_CENTER_LNG

# Camera registry: maps camera ID → GPS location + road name
# Edit this dict to match your actual camera positions
CAMERA_REGISTRY = {
    "CAM-01": {"lat": 40.7580, "lng": -73.9855, "road": "7th Ave & W 45th St", "speed": 50},
    "CAM-02": {"lat": 40.7614, "lng": -73.9776, "road": "Lexington Ave & E 48th St", "speed": 50},
    "CAM-03": {"lat": 40.7484, "lng": -73.9967, "road": "9th Ave & W 34th St", "speed": 60},
    "CAM-04": {"lat": 40.7549, "lng": -73.9840, "road": "Broadway & W 47th St", "speed": 40},
}


class YoloPipeline:
    """
    Full YOLO detection + classification pipeline.
    Processes video frames and writes results to incident CSV.
    """

    def __init__(self, camera_id: str = "CAM-01"):
        self.camera_id  = camera_id
        self.cam_info   = CAMERA_REGISTRY.get(camera_id, {
            "lat": MAP_CENTER_LAT, "lng": MAP_CENTER_LNG,
            "road": "Unknown Road", "speed": 60,
        })
        self.detector   = AccidentDetector()
        self.classifier = AccidentClassifier()
        self.frame_id   = 0

    def process_frame(self, frame) -> dict:
        """
        Process a single OpenCV frame through both YOLO models.

        Args:
            frame: OpenCV BGR numpy array

        Returns:
            Merged result dict (all CSV columns populated)
        """
        self.frame_id += 1

        # Run detector
        detection = self.detector.run(
            source        = frame,
            frame_id      = self.frame_id,
            camera_id     = self.camera_id,
            location_lat  = self.cam_info["lat"],
            location_lng  = self.cam_info["lng"],
            road_name     = self.cam_info["road"],
            speed_zone_kmph = self.cam_info["speed"],
        )

        # Only run classifier if detector found something
        if detection["accident_detected"]:
            classification = self.classifier.run(
                source    = frame,
                frame_id  = self.frame_id,
                camera_id = self.camera_id,
            )
        else:
            classification = {
                "accident_class": "no_accident",
                "class_conf":     0.0,
                "severity":       "none",
            }

        merged = merge_outputs(detection, classification)
        append_to_csv(merged)
        return merged

    def run_video(self, source, display: bool = False, max_frames: int = None):
        """
        Process a video file or webcam stream.

        Args:
            source    : File path string or 0 for webcam
            display   : Show OpenCV preview window
            max_frames: Stop after this many frames (None = run until end)
        """
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {source}")

        fps    = cap.get(cv2.CAP_PROP_FPS) or 30
        delay  = max(1, int(1000 / fps))
        frames = 0

        print(f"[Pipeline] Running on {source} at {fps:.1f} FPS — Camera {self.camera_id}")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                result = self.process_frame(frame)
                frames += 1

                status = "🚨 ACCIDENT" if result["accident_detected"] else "✅ Clear"
                print(
                    f"\r[Pipeline] Frame {frames} | {status} | "
                    f"cls={result['accident_class']} ({result['class_conf']:.0%})",
                    end="", flush=True,
                )

                if display:
                    annotated = _draw_overlay(frame, result)
                    cv2.imshow("Traffic Co-Pilot — YOLO Feed", annotated)
                    if cv2.waitKey(delay) & 0xFF == ord("q"):
                        break

                if max_frames and frames >= max_frames:
                    break

        finally:
            cap.release()
            if display:
                cv2.destroyAllWindows()
            print(f"\n[Pipeline] Finished — {frames} frames processed.")


def _draw_overlay(frame, result: dict):
    """Draw detection bounding box and classification label on frame."""
    frame = frame.copy()
    if result["accident_detected"]:
        x1 = int(result.get("bbox_x1") or 0)
        y1 = int(result.get("bbox_y1") or 0)
        x2 = int(result.get("bbox_x2") or frame.shape[1])
        y2 = int(result.get("bbox_y2") or frame.shape[0])

        severity_colours = {
            "high":   (0, 0, 220),
            "medium": (0, 140, 255),
            "low":    (0, 200, 0),
        }
        colour = severity_colours.get(result.get("severity", "medium"), (0, 140, 255))

        cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)
        label = f"{result['accident_class']} {result['class_conf']:.0%}"
        cv2.putText(frame, label, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, colour, 2)

    # Status bar
    status = "ACCIDENT DETECTED" if result["accident_detected"] else "CLEAR"
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 32), (20, 20, 20), -1)
    cv2.putText(frame, f"  {status}  |  {result['road_name']}  |  CAM: {result['camera_id']}",
                (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return frame


# ── CLI entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO Traffic Incident Pipeline")
    parser.add_argument("--source",  default="0",       help="Video path or 0 for webcam")
    parser.add_argument("--camera",  default="CAM-01",  help="Camera ID from CAMERA_REGISTRY")
    parser.add_argument("--display", action="store_true", help="Show OpenCV preview window")
    parser.add_argument("--frames",  type=int, default=None, help="Max frames to process")
    args = parser.parse_args()

    source = int(args.source) if args.source == "0" else args.source
    pipeline = YoloPipeline(camera_id=args.camera)
    pipeline.run_video(source, display=args.display, max_frames=args.frames)
