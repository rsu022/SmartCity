from utils.file_utils import load_image_as_bgr_array
import numpy as np
# Note: cv2 is not strictly needed here, but ensure load_image_as_bgr_array is robust

class WasteProcessor:
    def __init__(self):
        pass

    def extract(self, image_path: str, yolo_results):
        img = load_image_as_bgr_array(image_path)
        h, w = img.shape[:2]
        r = yolo_results[0]
        boxes = getattr(r, 'boxes', None)
        names = getattr(r, 'names', {}) if hasattr(r, 'names') else {}

        detections = []
        if boxes is None or len(boxes) == 0:
            return {"detections": [], "primary": None, "waste_type": "unknown"}

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

            # Density (Mask area / Bbox area)
            density = 1.0 # Default if no mask is available
            if hasattr(box, 'mask') and box.mask is not None:
                try:
                    # Get the mask for the current detection
                    mask_data = box.mask.data[0].cpu().numpy()
                    
                    # Ensure mask has non-zero size before dividing
                    if mask_data.size > 0:
                        density = float(mask_data.sum() / mask_data.size)
                    else:
                        density = 0.0
                except Exception:
                    density = 1.0 

            # Proximity to the bottom of the image (h - bottom_y) / h
            bottom_y = y2
            proximity_pct = (h - bottom_y) / h if h > 0 else 0.0

            detections.append({
                "xyxy": [x1, y1, x2, y2],
                "conf": conf,
                "class_id": cls,
                "class_name": names.get(cls, str(cls)),
                "area_px": float(area_px),
                "area_pct": float(area_pct),
                "density": float(density),
                "proximity_pct": float(proximity_pct)
            })

        # Primary detection is the one with the largest pixel area
        detections_sorted = sorted(detections, key=lambda x: x['area_px'], reverse=True)
        primary = detections_sorted[0] if detections_sorted else None
        waste_type = primary.get('class_name') if primary else 'unknown'

        return {"detections": detections_sorted, "primary": primary, "waste_type": waste_type}