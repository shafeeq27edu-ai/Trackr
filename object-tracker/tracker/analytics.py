import csv
import os
import time
import json
from typing import Dict, Set, List, Tuple, Any
import supervision as sv
from core.logging import logger
from tracker.analytics_base import BaseAnalytics
from core.plugin_manager import plugin_manager

class AnalyticsEnginePlugin(BaseAnalytics):
    """
    Manages advanced object analytics including unique deduplicated counts, 
    CSV event logging, Dwell Time, Zone Entry/Exits, and Peak Occupancy.
    Acts as an analytics plugin.
    """
    
    @property
    def name(self) -> str:
        return "AdvancedAnalytics"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_results(self) -> Dict[str, Any]:
        return self.get_summary_text() # Or whatever JSON payload we prefer
        
    def __init__(self, log_dir: str = "outputs", fps: float = 30.0):
        self.log_dir = log_dir
        self.fps = fps
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.csv_path = os.path.join(self.log_dir, "logs.csv")
        self.summary_path = os.path.join(self.log_dir, "summary.json")
        
        self.unique_counts: Dict[str, Set[int]] = {}
        
        # Advanced stats state
        self.peak_occupancy = 0
        self.total_detections = 0
        self.dwell_times: Dict[int, Dict[str, int]] = {} # tracker_id -> {'first': frame, 'last': frame}
        self.tracker_classes: Dict[int, str] = {} # tracker_id -> class_name
        self.zone_states: Dict[str, Dict[int, bool]] = {} # zone_id -> {tracker_id -> bool (is_in_zone)}
        self.zone_stats: Dict[str, Dict[str, int]] = {} # zone_id -> {'entries': 0, 'exits': 0}
        
        # Initialize the CSV file with headers
        with open(self.csv_path, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "frame_idx", "track_id", "class_name", "center_x", "center_y"])
            
    def register_zone(self, zone_id: str):
        """Registers a zone for entry/exit tracking."""
        if zone_id not in self.zone_states:
            self.zone_states[zone_id] = {}
            self.zone_stats[zone_id] = {'entries': 0, 'exits': 0}

    def process_zone_triggers(self, zone_id: str, trigger_results: List[bool], tracker_ids: List[int]):
        """Processes boolean trigger arrays from PolygonZone to calculate entry/exits."""
        if zone_id not in self.zone_states:
            self.register_zone(zone_id)
            
        for is_in_zone, t_id in zip(trigger_results, tracker_ids):
            prev_state = self.zone_states[zone_id].get(t_id, False)
            if is_in_zone and not prev_state:
                self.zone_stats[zone_id]['entries'] += 1
            elif not is_in_zone and prev_state:
                self.zone_stats[zone_id]['exits'] += 1
                
            self.zone_states[zone_id][t_id] = is_in_zone

    def process_frame(self, detections: sv.Detections, class_names: Dict[int, str], frame_idx: int) -> None:
        """
        Updates unique counts, dwell times, and logs detection events to the CSV.
        """
        if detections.tracker_id is None or len(detections) == 0 or len(detections.tracker_id) == 0:
            return
            
        current_time = time.time()
        
        # Peak occupancy
        current_occupancy = len(detections)
        if current_occupancy > self.peak_occupancy:
            self.peak_occupancy = current_occupancy
            
        self.total_detections += current_occupancy
        
        with open(self.csv_path, mode='a', newline='') as f:
            writer = csv.writer(f)
            
            for class_id, tracker_id, bbox in zip(detections.class_id, detections.tracker_id, detections.xyxy):
                class_name = class_names[class_id]
                self.tracker_classes[tracker_id] = class_name
                
                # Update unique counts using a Set to automatically deduplicate
                if class_name not in self.unique_counts:
                    self.unique_counts[class_name] = set()
                self.unique_counts[class_name].add(tracker_id)
                
                # Update Dwell Time logic
                if tracker_id not in self.dwell_times:
                    self.dwell_times[tracker_id] = {'first': frame_idx, 'last': frame_idx}
                else:
                    self.dwell_times[tracker_id]['last'] = frame_idx
                
                # Calculate bounding box center
                center_x = (bbox[0] + bbox[2]) / 2.0
                center_y = (bbox[1] + bbox[3]) / 2.0
                
                # Log to CSV
                writer.writerow([current_time, frame_idx, tracker_id, class_name, f"{center_x:.2f}", f"{center_y:.2f}"])
                
    def get_summary_text(self) -> str:
        """Returns a formatted string summarizing the unique counts."""
        summary = []
        for class_name, ids in self.unique_counts.items():
            summary.append(f"{class_name}: {len(ids)}")
        return " | ".join(summary) if summary else "Waiting for detections..."

    def generate_session_summary(self, total_frames: int, duration_sec: float) -> Dict:
        """
        Calculates and exports the final session analytics summary.
        """
        # Calculate class distributions
        class_distribution = {class_name: len(ids) for class_name, ids in self.unique_counts.items()}
        
        # Calculate dwell times (in seconds)
        dwell_time_list = []
        for t_id, frames in self.dwell_times.items():
            duration_frames = frames['last'] - frames['first']
            seconds = duration_frames / self.fps
            dwell_time_list.append(seconds)
            
        avg_dwell = sum(dwell_time_list) / len(dwell_time_list) if dwell_time_list else 0
        max_dwell = max(dwell_time_list) if dwell_time_list else 0
        
        # Construct JSON summary
        summary = {
            "video_stats": {
                "total_frames": total_frames,
                "processing_time_sec": round(duration_sec, 2),
                "avg_processing_fps": round(total_frames / duration_sec, 2) if duration_sec > 0 else 0,
            },
            "traffic_stats": {
                "total_unique_objects": sum(class_distribution.values()),
                "peak_occupancy": self.peak_occupancy,
                "average_objects_per_frame": round(self.total_detections / total_frames, 2) if total_frames > 0 else 0,
            },
            "class_distribution": class_distribution,
            "dwell_times_sec": {
                "average": round(avg_dwell, 2),
                "maximum": round(max_dwell, 2)
            },
            "zone_activity": self.zone_stats
        }
        
        # Write to JSON
        with open(self.summary_path, "w") as f:
            json.dump(summary, f, indent=4)
            
        logger.info(f"Session summary generated at {self.summary_path}")
        return summary
        
    def reset(self) -> None:
        """Reset the analytics state."""
        self.unique_counts.clear()

# Backward compatibility alias
AnalyticsEngine = AnalyticsEnginePlugin

# Register AnalyticsEngine as a plugin
plugin_manager.register_plugin(AnalyticsEnginePlugin)
