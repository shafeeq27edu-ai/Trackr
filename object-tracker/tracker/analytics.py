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
        
        # Speed and direction state
        self.track_history: Dict[int, List[Tuple[float, float, int]]] = {} # tracker_id -> [(cx, cy, frame_idx)]
        self.track_speeds: Dict[int, List[float]] = {} # tracker_id -> [speed_kmh]
        self.track_directions: Dict[int, str] = {} # tracker_id -> last_direction
        
        # Initialize the CSV file with headers
        self._csv_file = open(self.csv_path, mode='w', newline='')
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(["timestamp", "frame_idx", "track_id", "class_name", "center_x", "center_y", "speed_kmh", "direction"])
        
        # Track last-seen frame for stale tracker eviction
        self._last_seen: Dict[int, int] = {}  # tracker_id -> last frame_idx
        self._eviction_interval = 300  # Evict trackers not seen for this many frames
            
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

    def process_detections(self, detections: sv.Detections, class_names: Dict[int, str], frame_idx: int) -> None:
        """Alias for process_frame to maintain backward compatibility."""
        self.process_frame(detections, class_names, frame_idx)

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
        
        # Track which IDs are active this frame
        active_ids = set(detections.tracker_id)
        
        for class_id, tracker_id, bbox in zip(detections.class_id, detections.tracker_id, detections.xyxy):
            try:
                class_name = class_names[int(class_id)] if class_names else f"class_{class_id}"
            except (IndexError, KeyError, TypeError):
                class_name = f"class_{class_id}"
            
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
            current_pos = (center_x, center_y)
            
            # Maintain position history (capped to last 10 entries)
            if tracker_id not in self.track_history:
                self.track_history[tracker_id] = []
            self.track_history[tracker_id].append((center_x, center_y, frame_idx))
            if len(self.track_history[tracker_id]) > 10:
                self.track_history[tracker_id] = self.track_history[tracker_id][-10:]
            
            # Calculate Speed & Direction (smoothed over 5 frames)
            speed_kmh = 0.0
            direction = "Unknown"
            history = self.track_history[tracker_id]
            
            if len(history) >= 5:
                prev_x, prev_y, prev_frame = history[-5]
                dx = center_x - prev_x
                dy = center_y - prev_y
                frame_diff = frame_idx - prev_frame
                
                if frame_diff > 0:
                    dt = frame_diff / self.fps
                    dist_px = (dx**2 + dy**2)**0.5
                    # Conversion: 0.05 meters/pixel and 3.6 for km/h
                    speed_kmh = (dist_px * 0.05 / dt) * 3.6
                    
                    # Determine dominant direction
                    if abs(dx) > abs(dy):
                        direction = "East" if dx > 0 else "West"
                    else:
                        direction = "South" if dy > 0 else "North" # y-down
                        
            self.track_directions[tracker_id] = direction
            # Cap track_speeds to last entry only
            self.track_speeds[tracker_id] = [speed_kmh]
            
            # Log to CSV
            self._csv_writer.writerow([current_time, frame_idx, tracker_id, class_name, f"{center_x:.2f}", f"{center_y:.2f}", f"{speed_kmh:.2f}", direction])
            
            # Update last-seen frame for this tracker
            self._last_seen[tracker_id] = frame_idx
        
        # Evict stale trackers to prevent memory bloat on long videos/streams
        if frame_idx % self._eviction_interval == 0 and frame_idx > 0:
            stale_ids = [tid for tid, last_frame in self._last_seen.items()
                         if frame_idx - last_frame > self._eviction_interval]
            for tid in stale_ids:
                self.track_history.pop(tid, None)
                self.track_speeds.pop(tid, None)
                self.track_directions.pop(tid, None)
                self._last_seen.pop(tid, None)
                for zone_id in self.zone_states:
                    self.zone_states[zone_id].pop(tid, None)

    def get_track_speed(self, tracker_id: int) -> float:
        """Returns the last calculated speed for a track (in km/h)."""
        speeds = self.track_speeds.get(tracker_id, [])
        return speeds[-1] if speeds else 0.0

    def get_track_direction(self, tracker_id: int) -> str:
        """Returns the last calculated direction for a track."""
        return self.track_directions.get(tracker_id, "Unknown")
                
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
        
        # Calculate speed stats
        class_speeds = {}
        all_speeds = []
        for tracker_id, speeds in self.track_speeds.items():
            class_name = self.tracker_classes.get(tracker_id, "Unknown")
            # Filter out 0.0 speeds (initial frames)
            valid_speeds = [s for s in speeds if s > 0]
            if valid_speeds:
                if class_name not in class_speeds:
                    class_speeds[class_name] = []
                class_speeds[class_name].extend(valid_speeds)
                all_speeds.extend(valid_speeds)
                
        class_speed_averages = {
            class_name: round(sum(speeds) / len(speeds), 2)
            for class_name, speeds in class_speeds.items() if speeds
        }
        avg_speed = round(sum(all_speeds) / len(all_speeds), 2) if all_speeds else 0.0
        max_speed = round(max(all_speeds), 2) if all_speeds else 0.0
        
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
            "speed_stats": {
                "average_speed_kmh": avg_speed,
                "maximum_speed_kmh": max_speed,
                "class_averages_kmh": class_speed_averages
            },
            "zone_activity": self.zone_stats
        }
        
        # Write to JSON
        with open(self.summary_path, "w") as f:
            json.dump(summary, f, indent=4)
            
        # Close persistent CSV writer
        if hasattr(self, '_csv_file') and not self._csv_file.closed:
            self._csv_file.close()
            
        logger.info(f"Session summary generated at {self.summary_path}")
        return summary
        
    def _close_csv(self):
        """Safely close the CSV file handle."""
        if hasattr(self, '_csv_file') and self._csv_file and not self._csv_file.closed:
            self._csv_file.close()
    
    def __del__(self):
        """Ensure CSV file is closed on garbage collection."""
        self._close_csv()

    def reset(self) -> None:
        """Reset the analytics state."""
        self._close_csv()
        self.unique_counts.clear()
        self.peak_occupancy = 0
        self.total_detections = 0
        self.dwell_times.clear()
        self.tracker_classes.clear()
        self.zone_states.clear()
        self.zone_stats.clear()
        self.track_history.clear()
        self.track_speeds.clear()
        self.track_directions.clear()
        self._last_seen.clear()

# Backward compatibility alias
AnalyticsEngine = AnalyticsEnginePlugin

# Register AnalyticsEngine as a plugin
plugin_manager.register_plugin(AnalyticsEnginePlugin)
