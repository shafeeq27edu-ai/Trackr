import streamlit as st
import requests
import time
import pandas as pd
import json

st.set_page_config(page_title="Trackr Advanced Analytics", page_icon="🎥", layout="wide")

st.title("🎥 Trackr: Advanced Intelligence & Analytics")
st.markdown("Upload a video to process it through the ByteTrack pipeline and generate powerful spatial analytics.")

API_BASE_URL = "http://localhost:8000/api/v1/jobs"

uploaded_file = st.file_uploader("Upload a video file (.mp4)", type=["mp4"])

if uploaded_file is not None:
    if st.button("Process Video"):
        with st.spinner("Uploading and queueing job..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "video/mp4")}
            response = requests.post(f"{API_BASE_URL}/upload", files=files)
            
        if response.status_code == 200:
            data = response.json()
            job_id = data.get("job_id")
            st.success(f"Job Queued! ID: {job_id}")
            
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            # Polling loop
            while True:
                time.sleep(1)
                status_res = requests.get(f"{API_BASE_URL}/{job_id}")
                if status_res.status_code == 200:
                    job = status_res.json()
                    
                    status = job.get("status")
                    stage = job.get("stage", "")
                    progress = job.get("progress", 0.0)
                    
                    progress_val = min(max(progress / 100.0, 0.0), 1.0)
                    progress_bar.progress(progress_val)
                    status_text.text(f"Status: {status} | Stage: {stage} | Progress: {progress:.1f}%")
                    
                    if status == "COMPLETED":
                        st.success("Video processing completed!")
                        
                        # --- Results Layout ---
                        st.header("📊 Intelligence Dashboard")
                        
                        # Fetch analytics
                        analytics_res = requests.get(f"{API_BASE_URL}/{job_id}/analytics")
                        if analytics_res.status_code == 200:
                            summary = analytics_res.json().get("analytics", {})
                            
                            # 1. Top-Level Metrics
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Total Unique Objects", summary.get("traffic_stats", {}).get("total_unique_objects", 0))
                            col2.metric("Peak Occupancy", summary.get("traffic_stats", {}).get("peak_occupancy", 0))
                            col3.metric("Avg Objects / Frame", summary.get("traffic_stats", {}).get("average_objects_per_frame", 0))
                            col4.metric("Avg Dwell Time (s)", summary.get("dwell_times_sec", {}).get("average", 0))
                            
                            st.divider()
                            
                            # 2. Split view for Video and Heatmap
                            v_col, h_col = st.columns(2)
                            
                            with v_col:
                                st.subheader("Annotated Video")
                                video_res = requests.get(f"{API_BASE_URL}/{job_id}/result")
                                if video_res.status_code == 200:
                                    st.video(video_res.content)
                                    st.download_button("⬇️ Download Video", data=video_res.content, file_name=f"tracked_{job_id}.mp4", mime="video/mp4")
                            
                            with h_col:
                                st.subheader("Spatial Heatmap")
                                heatmap_res = requests.get(f"{API_BASE_URL}/{job_id}/heatmap")
                                if heatmap_res.status_code == 200:
                                    st.image(heatmap_res.content, use_container_width=True)
                                    st.download_button("⬇️ Download Heatmap", data=heatmap_res.content, file_name=f"heatmap_{job_id}.png", mime="image/png")
                                else:
                                    st.info("Heatmap not generated for this video.")
                            
                            st.divider()
                            
                            # 3. Charts & Data
                            c1, c2 = st.columns(2)
                            
                            with c1:
                                st.subheader("Class Distribution")
                                class_dist = summary.get("class_distribution", {})
                                if class_dist:
                                    df_classes = pd.DataFrame(list(class_dist.items()), columns=["Class", "Count"]).set_index("Class")
                                    st.bar_chart(df_classes)
                                else:
                                    st.info("No objects detected.")
                                    
                            with c2:
                                st.subheader("Zone Activity")
                                zones = summary.get("zone_activity", {})
                                if zones:
                                    zone_data = []
                                    for z_id, stats in zones.items():
                                        zone_data.append({"Zone": z_id, "Entries": stats["entries"], "Exits": stats["exits"]})
                                    st.dataframe(pd.DataFrame(zone_data), use_container_width=True)
                                else:
                                    st.info("No zones configured or triggered.")
                                    
                            st.divider()
                            
                            # 4. Exports
                            st.subheader("Raw Data Exports")
                            report_res = requests.get(f"{API_BASE_URL}/{job_id}/report")
                            if report_res.status_code == 200:
                                st.download_button(
                                    label="⬇️ Download Raw CSV Telemetry",
                                    data=report_res.content,
                                    file_name=f"telemetry_{job_id}.csv",
                                    mime="text/csv"
                                )
                                
                            st.download_button(
                                label="⬇️ Download Session JSON",
                                data=json.dumps(summary, indent=4),
                                file_name=f"session_{job_id}.json",
                                mime="application/json"
                            )
                        break
                    elif status == "FAILED":
                        st.error(f"Processing failed: {job.get('error')}")
                        break
                else:
                    st.error(f"Failed to fetch job status: {status_res.text}")
                    break
        else:
            st.error(f"Failed to queue job: {response.text}")
