import csv
import os
import time
from typing import Dict, Set
import supervision as sv

class AnalyticsEngine:
    """
    Manages object analytics including unique deduplicated counts and CSV event logging.
    """
    
    def __init__(self, log_dir: str = "outputs"):
        """
        Initializes the analytics engine and the CSV log file.
        
        Args:
            log_dir (str): Directory where logs.csv will be stored.
        """
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.csv_path = os.path.join(self.log_dir, "logs.csv")
        self.unique_counts: Dict[str, Set[int]] = {}
        
        # Initialize the CSV file with headers
        with open(self.csv_path, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "frame_idx", "track_id", "class_name", "center_x", "center_y"])
            
    def process_detections(self, detections: sv.Detections, class_names: Dict[int, str], frame_idx: int) -> None:
        """
        Updates unique counts and logs detection events to the CSV.
        
        Args:
            detections (sv.Detections): The tracked detections for the current frame.
            class_names (Dict[int, str]): Mapping of class IDs to class names.
            frame_idx (int): The current frame number.
        """
        if detections.tracker_id is None or len(detections) == 0 or len(detections.tracker_id) == 0:
            return
            
        current_time = time.time()
        
        with open(self.csv_path, mode='a', newline='') as f:
            writer = csv.writer(f)
            
            for class_id, tracker_id, bbox in zip(detections.class_id, detections.tracker_id, detections.xyxy):
                class_name = class_names[class_id]
                
                # Update unique counts using a Set to automatically deduplicate
                if class_name not in self.unique_counts:
                    self.unique_counts[class_name] = set()
                self.unique_counts[class_name].add(tracker_id)
                
                # Calculate bounding box center
                center_x = (bbox[0] + bbox[2]) / 2.0
                center_y = (bbox[1] + bbox[3]) / 2.0
                
                # Log to CSV
                writer.writerow([current_time, frame_idx, tracker_id, class_name, f"{center_x:.2f}", f"{center_y:.2f}"])
                
    def get_summary_text(self) -> str:
        """
        Returns a formatted string summarizing the unique counts.
        """
        summary = []
        for class_name, ids in self.unique_counts.items():
            summary.append(f"{class_name}: {len(ids)}")
        return " | ".join(summary) if summary else "Waiting for detections..."
