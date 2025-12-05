from utils.file_utils import load_image_as_bgr_array
import cv2
import numpy as np

class PotholeProcessor:
    def __init__(self):
        pass

    def estimate_depth_heuristic(self, bbox, image):
        """
        Estimates depth based on darkness heuristic (darker area = greater depth).
        Max depth assumed to be 0.3m.
        """
        # Ensure bbox values are within image bounds and valid integers
        x1, y1, x2, y2 = [int(max(0, v)) for v in bbox]
        x1, x2 = min(x1, image.shape[1]), min(x2, image.shape[1])
        y1, y2 = min(y1, image.shape[0]), min(y2, image.shape[0])
        
        # Check for valid crop dimensions
        if x2 <= x1 or y2 <= y1:
            return 0.0
            
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return 0.0
            
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mean = float(gray.mean())
        
        # Scale (255 - mean) normalized by 255 to a maximum of 0.3m
        # 255 (white) -> 0m; 0 (black) -> 0.3m
        depth_m = max(0.0, (255.0 - mean) / 255.0 * 0.3)
        return float(depth_m)

    def extract(self, image_path: str, yolo_results):
        img = load_image_as_bgr_array(image_path)
        h, w = img.shape[:2]
        r = yolo_results[0]
        boxes = getattr(r, 'boxes', None)
        names = getattr(r, 'names', {}) if hasattr(r, 'names') else {}

        detections = []
        if boxes is None or len(boxes) == 0:
            return {"detections": [], "primary": None, "road_type": "unknown"}

        for box in boxes:
            # Unified tensor to numpy conversion
            try:
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls = int(box.cls[0].cpu().numpy())
            except Exception:
                xyxy = box.xyxy[0].numpy() if len(box.xyxy) > 0 else np.zeros(4)
                conf = box.conf.item() if len(box.conf) > 0 else 0.0
                cls = box.cls.item() if len(box.cls) > 0 else -1
            
            x1, y1, x2, y2 = map(float, xyxy.tolist())
            area_px = max(0.0, (x2 - x1) * (y2 - y1))
            area_pct = area_px / (w * h) if (w*h) > 0 else 0.0

            depth_m = self.estimate_depth_heuristic([x1,y1,x2,y2], img)

            # risk score: area_pct scaled by (1 + depth_ratio)
            depth_ratio = (depth_m / 0.1) if depth_m and depth_m > 1e-6 else 0.0
            risk_score = float(area_pct * (1.0 + depth_ratio))

            detections.append({
                "xyxy": [x1, y1, x2, y2],
                "conf": conf,
                "class_id": cls,
                "class_name": names.get(cls, str(cls)),
                "area_px": float(area_px),
                "area_pct": float(area_pct),
                "est_depth_m": depth_m,
                "risk_score": float(risk_score)
            })

        detections_sorted = sorted(detections, key=lambda x: x['risk_score'], reverse=True)
        primary = detections_sorted[0] if detections_sorted else None

        # Road type heuristic based on vertical position
        road_type = "unknown"
        if primary and h > 0:
            _, y1, _, y2 = primary['xyxy']
            # If the pothole is primarily in the bottom half of the image (y > 0.5 * h)
            if (y2 / h) > 0.5: 
                road_type = "asphalt"

        return {"detections": detections_sorted, "primary": primary, "road_type": road_type}