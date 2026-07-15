import streamlit as st
import requests
import time
import pandas as pd
import json

st.set_page_config(page_title="Trackr Advanced Analytics", page_icon="🎥", layout="wide")

# Custom Premium Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0B0E14;
    color: #E2E8F0;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif;
    background: -webkit-linear-gradient(45deg, #A78BFA, #38BDF8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.stMetric {
    background: rgba(30, 41, 59, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stMetric:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 30px -5px rgba(56, 189, 248, 0.15);
}
div[data-testid="stExpander"] {
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    margin-bottom: 15px;
    transition: all 0.3s ease;
}
div[data-testid="stExpander"]:hover {
    border-color: rgba(56, 189, 248, 0.3);
}
.stButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.5rem 1rem;
    transition: all 0.3s ease;
    box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39);
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
    background: linear-gradient(90deg, #4f46e5, #7c3aed);
}
.stTextInput>div>div>input {
    background-color: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: white;
    border-radius: 8px;
}
.stTextInput>div>div>input:focus {
    border-color: #38BDF8;
    box-shadow: 0 0 0 1px #38BDF8;
}
</style>
""", unsafe_allow_html=True)

import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
SYS_API_BASE_URL = os.getenv("SYS_API_BASE_URL", "http://localhost:8000/api/v1/system")

# --- Session State Management ---
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_project_id" not in st.session_state:
    st.session_state.selected_project_id = None

def get_auth_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def login(email, password):
    data = {"username": email, "password": password}
    res = requests.post(f"{API_BASE_URL}/auth/login", data=data)
    if res.status_code == 200:
        st.session_state.token = res.json().get("access_token")
        # Fetch user profile
        user_res = requests.get(f"{API_BASE_URL}/auth/me", headers=get_auth_headers())
        if user_res.status_code == 200:
            st.session_state.user = user_res.json()
        return True
    return False

def register(email, password, name):
    data = {"email": email, "password": password, "name": name}
    res = requests.post(f"{API_BASE_URL}/auth/register", json=data)
    return res.status_code == 200

def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.selected_project_id = None
    st.rerun()

# --- Auth UI ---
if not st.session_state.token:
    st.title("Welcome to Trackr")
    tab_login, tab_register = st.tabs(["Login", "Register"])
    
    with tab_login:
        with st.form("login_form"):
            l_email = st.text_input("Email")
            l_pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                with st.spinner("Authenticating..."):
                    if login(l_email, l_pwd):
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
                    
    with tab_register:
        with st.form("register_form"):
            r_name = st.text_input("Name")
            r_email = st.text_input("Email")
            r_pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Register"):
                with st.spinner("Creating account..."):
                    if register(r_email, r_pwd, r_name):
                        st.success("Registered! You can now log in.")
                    else:
                        st.error("Registration failed. Email might exist.")
    st.stop()

# --- Main App (Logged In) ---
st.title("🎥 Trackr: Advanced Intelligence & Analytics")

# --- Sidebar ---
user_data = st.session_state.user or {}
st.sidebar.title(f"👤 {user_data.get('name', 'User')}")
st.sidebar.write(user_data.get('email', ''))
if st.sidebar.button("Logout"):
    logout()
st.sidebar.divider()

# Projects Sidebar
st.sidebar.subheader("📁 Workspaces")
projects_res = requests.get(f"{API_BASE_URL}/projects", headers=get_auth_headers())
if projects_res.status_code == 200:
    projects = projects_res.json()
    if projects:
        proj_opts = {p["id"]: p["name"] for p in projects}
        
        # If the currently selected project doesn't exist, reset it
        if st.session_state.selected_project_id not in proj_opts:
            st.session_state.selected_project_id = projects[0]["id"]
            
        selected_id = st.sidebar.selectbox(
            "Select Project",
            options=list(proj_opts.keys()),
            format_func=lambda x: proj_opts[x],
            index=list(proj_opts.keys()).index(st.session_state.selected_project_id)
        )
        st.session_state.selected_project_id = selected_id
    else:
        st.sidebar.info("No projects yet.")
        st.session_state.selected_project_id = None
        
    with st.sidebar.expander("➕ New Project"):
        new_p_name = st.text_input("Project Name")
        if st.button("Create"):
            with st.spinner("Creating project..."):
                requests.post(f"{API_BASE_URL}/projects", json={"name": new_p_name}, headers=get_auth_headers())
                st.rerun()
st.sidebar.divider()

st.sidebar.title("🖥️ System Health")
try:
    perf_res = requests.get(f"{SYS_API_BASE_URL}/performance", headers=get_auth_headers())
    res_res = requests.get(f"{SYS_API_BASE_URL}/resources", headers=get_auth_headers())
    models_res = requests.get(f"{SYS_API_BASE_URL}/models", headers=get_auth_headers())
    
    if res_res.status_code == 200:
        res_data = res_res.json()
        st.sidebar.subheader("Resources")
        st.sidebar.progress(res_data["cpu_percent"] / 100.0, text=f"CPU Usage: {res_data['cpu_percent']}%")
        st.sidebar.progress(res_data["memory"]["percent"] / 100.0, text=f"Memory: {res_data['memory']['used_gb']}GB / {res_data['memory']['total_gb']}GB")
except Exception:
    st.sidebar.error("System API offline")

# --- App Tabs ---
tab_batch, tab_live = st.tabs(["📁 Offline Batch Processing", "🔴 Live Streaming"])

with tab_batch:
    if not st.session_state.selected_project_id:
        st.warning("Please create or select a project from the sidebar first.")
    else:
        # Load jobs first to display dashboard metrics
        jobs_res = requests.get(f"{API_BASE_URL}/jobs", headers=get_auth_headers())
        proj_jobs = []
        if jobs_res.status_code == 200:
            all_jobs = jobs_res.json().get("jobs", [])
            proj_jobs = [j for j in all_jobs if j.get("project_id") == st.session_state.selected_project_id]
            
        # Display Workspace Dashboard Metrics
        if proj_jobs:
            completed_jobs = [j for j in proj_jobs if j.get("status") == "COMPLETED"]
            total_count = len(proj_jobs)
            success_count = len(completed_jobs)
            failed_count = len([j for j in proj_jobs if j.get("status") == "FAILED"])
            
            avg_fps = 0.0
            if completed_jobs:
                avg_fps = sum(j.get("average_fps", 0.0) or 0.0 for j in completed_jobs) / len(completed_jobs)
                
            success_rate = (success_count / (total_count - len([j for j in proj_jobs if j.get("status") in ["INITIALIZING", "PROCESSING"]])) * 100) if total_count > 0 and (total_count - len([j for j in proj_jobs if j.get("status") in ["INITIALIZING", "PROCESSING"]])) > 0 else 100.0

            st.write("### 📁 Workspace Performance")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Total Jobs Run", total_count)
            m_col2.metric("Success Rate", f"{success_rate:.1f}%")
            m_col3.metric("Failed Runs", failed_count)
            m_col4.metric("Average Speed", f"{avg_fps:.1f} FPS")
            st.divider()

        if "active_job_id" not in st.session_state:
            st.session_state.active_job_id = None
            st.session_state.start_process_time = None
            
        if st.session_state.active_job_id:
            job_id = st.session_state.active_job_id
            st.info(f"Processing Job: {job_id}")
            status_res = requests.get(f"{API_BASE_URL}/jobs/{job_id}", headers=get_auth_headers())
            
            if status_res.status_code == 200:
                job = status_res.json()
                status = job.get("status")
                stage = job.get("stage", "")
                progress = job.get("progress", 0.0)
                
                elapsed = time.time() - st.session_state.start_process_time
                
                if progress > 0:
                    rate = progress / elapsed
                    remaining = 100.0 - progress
                    eta_seconds = remaining / rate
                    eta_str = time.strftime("%M:%S", time.gmtime(eta_seconds))
                else:
                    eta_str = "--:--"
                    
                current_fps_val = job.get("average_fps", 0.0) or 0.0
                progress_val = min(max(progress / 100.0, 0.0), 1.0)
                st.progress(progress_val)
                st.markdown(
                    f"**Status:** `{status}` | **Stage:** {stage} | "
                    f"**Progress:** {progress:.1f}% | **Speed:** {current_fps_val:.1f} FPS | "
                    f"**Elapsed:** {time.strftime('%M:%S', time.gmtime(elapsed))} | **ETA:** {eta_str}"
                )
                
                if status == "COMPLETED":
                    st.success("Video processing completed successfully!")
                    st.session_state.active_job_id = None
                elif status == "FAILED":
                    st.error(f"Processing failed: {job.get('error')}")
                    st.session_state.active_job_id = None
                else:
                    time.sleep(1)
                    st.rerun()
            else:
                st.error(f"Failed to fetch job status: {status_res.text}")
                st.session_state.active_job_id = None
                
        else:
            uploaded_file = st.file_uploader("Upload a video file (.mp4)", type=["mp4"])
            if uploaded_file is not None:
                if st.button("Process Video"):
                    with st.spinner("Uploading and queueing job..."):
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "video/mp4")}
                        data = {"project_id": st.session_state.selected_project_id}
                        response = requests.post(f"{API_BASE_URL}/jobs/upload", files=files, data=data, headers=get_auth_headers())
                        
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.active_job_id = data.get("job_id")
                        st.session_state.start_process_time = time.time()
                        st.rerun()
                    else:
                        st.error(f"Failed to queue job: {response.text}")
                    
        # List jobs for this project (using the list fetched at the top)
        st.divider()
        st.subheader("Job History")
        
        if jobs_res.status_code == 200:
            if not proj_jobs:
                st.info("No jobs found in this project.")
            else:
                for j in reversed(proj_jobs):
                    with st.expander(f"Job {j['id'][:8]}... - {j['filename']} ({j['status']})"):
                        if j['status'] == "COMPLETED":
                            # Load job details side-by-side: Video & Heatmap
                            v_col1, v_col2 = st.columns(2)
                            token_param = f"?token={st.session_state.token}"
                            video_res_url = f"{API_BASE_URL}/jobs/{j['id']}/result{token_param}"
                            heatmap_url = f"{API_BASE_URL}/jobs/{j['id']}/heatmap{token_param}"
                            
                            with v_col1:
                                st.write("### 🎥 Processed Output")
                                st.video(video_res_url)
                            with v_col2:
                                st.write("### 🔥 Activity Heatmap")
                                st.image(heatmap_url, use_container_width=True)
                                
                            # Download grid
                            d_col1, d_col2, d_col3 = st.columns(3)
                            d_col1.link_button("📥 Download Video", video_res_url, use_container_width=True)
                            d_col2.link_button("📥 Download Heatmap", heatmap_url, use_container_width=True)
                            d_col3.link_button("📥 Download CSV Report", f"{API_BASE_URL}/jobs/{j['id']}/report{token_param}", use_container_width=True)
                            
                            # Render Analytics Dashboard
                            analytics = j.get("analytics")
                            if analytics:
                                st.write("### 📊 Analytics Overview")
                                tab_charts, tab_tables, tab_meta = st.tabs(["Count Charts", "Detailed Data", "Technical Metrics"])
                                
                                # Process analytics data
                                traffic_stats = analytics.get("traffic_stats", {})
                                video_stats = analytics.get("video_stats", {})
                                class_distribution = analytics.get("class_distribution", {})
                                dwell_times_sec = analytics.get("dwell_times_sec", {})
                                speed_stats = analytics.get("speed_stats", {})
                                
                                with tab_charts:
                                    c_col1, c_col2 = st.columns(2)
                                    with c_col1:
                                        st.write("#### Classification Count")
                                        if class_distribution:
                                            df_dist = pd.DataFrame(list(class_distribution.items()), columns=["Object Type", "Count"])
                                            st.bar_chart(df_dist, x="Object Type", y="Count")
                                        else:
                                            st.info("No classification data found.")
                                    with c_col2:
                                        st.write("#### Average Speed (km/h)")
                                        class_averages = speed_stats.get("class_averages_kmh", {}) if speed_stats else {}
                                        if class_averages:
                                            df_speeds = pd.DataFrame(list(class_averages.items()), columns=["Object Type", "Avg Speed (km/h)"])
                                            st.bar_chart(df_speeds, x="Object Type", y="Avg Speed (km/h)")
                                        else:
                                            st.info("No speed data found.")
                                        
                                with tab_tables:
                                    col_data = []
                                    if traffic_stats:
                                        col_data.extend([
                                            {"Metric": k.replace("_", " ").title(), "Value": str(v)}
                                            for k, v in traffic_stats.items()
                                        ])
                                    if dwell_times_sec:
                                        col_data.extend([
                                            {"Metric": f"Dwell Time - {k.replace('_', ' ').title()}", "Value": f"{v}s"}
                                            for k, v in dwell_times_sec.items()
                                        ])
                                    if speed_stats:
                                        col_data.append(
                                            {"Metric": "Global Average Speed", "Value": f"{speed_stats.get('average_speed_kmh', 0.0)} km/h"}
                                        )
                                        col_data.append(
                                            {"Metric": "Global Maximum Speed", "Value": f"{speed_stats.get('maximum_speed_kmh', 0.0)} km/h"}
                                        )
                                    if col_data:
                                        df_traffic = pd.DataFrame(col_data)
                                        st.dataframe(df_traffic, use_container_width=True, hide_index=True)
                                    else:
                                        st.info("No traffic flow data found.")
                                        
                                with tab_meta:
                                    if video_stats:
                                        m1, m2, m3 = st.columns(3)
                                        m1.metric("Total Frames", video_stats.get("total_frames", 0))
                                        m2.metric("Avg Processing Speed", f"{video_stats.get('avg_processing_fps', 0.0):.1f} FPS")
                                        m3.metric("Duration", f"{video_stats.get('processing_time_sec', 0.0):.1f}s")
                            
                        elif j['status'] == "FAILED":
                            st.error(f"Job Failed: {j.get('error', 'Unknown Error')}")
                        elif j['status'] in ["INITIALIZING", "PROCESSING"]:
                            st.info(f"Current Stage: {j.get('stage', 'Starting...')}")
                            progress_val = float(j.get('progress', 0.0)) / 100.0
                            st.progress(min(max(progress_val, 0.0), 1.0))
                            
                        if st.button("Delete Job", key=f"del_{j['id']}"):
                            requests.delete(f"{API_BASE_URL}/jobs/{j['id']}", headers=get_auth_headers())
                            st.rerun()

with tab_live:
    st.header("🔴 Live Video Streams")
    with st.expander("➕ Add New Stream"):
        source_input = st.text_input("Stream Source (e.g., '0' for webcam, or RTSP URL)", value="0")
        if st.button("Add Stream"):
            res = requests.post(f"{API_BASE_URL}/streams", json={"source": source_input}, headers=get_auth_headers())
            if res.status_code == 200:
                st.success("Stream added!")
                st.rerun()
            else:
                st.error(f"Failed to add stream: {res.status_code} - {res.text}")
                
    st.divider()
    streams_res = requests.get(f"{API_BASE_URL}/streams", headers=get_auth_headers())
    if streams_res.status_code == 200:
        streams = streams_res.json().get("streams", [])
        if not streams:
            st.info("No active streams. Add one above.")
        else:
            for s in streams:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                col1.write(f"**Source:** {s['source']} (ID: {s['id']})")
                col2.write(f"Status: `{s['status']}`")
                
                with col3:
                    if s['status'] in ["INITIALIZING", "STOPPED", "FAILED"]:
                        if st.button("▶️ Start", key=f"start_{s['id']}"):
                            requests.post(f"{API_BASE_URL}/streams/{s['id']}/start", headers=get_auth_headers())
                            st.rerun()
                    elif s['status'] == "PLAYING":
                        if st.button("⏹️ Stop", key=f"stop_{s['id']}"):
                            requests.post(f"{API_BASE_URL}/streams/{s['id']}/stop", headers=get_auth_headers())
                            st.rerun()
                
                with col4:
                    if st.button("🗑️ Delete", key=f"del_{s['id']}"):
                        requests.delete(f"{API_BASE_URL}/streams/{s['id']}", headers=get_auth_headers())
                        st.rerun()
                        
                if s.get("error"):
                    st.error(f"⚠️ Error: {s['error']}")
                
                if s['status'] == "PLAYING":
                    # Display stream stats
                    st.caption(f"FPS: {s.get('fps', 0)} | Frames Processed: {s.get('frames_processed', 0)} | Detections: {s.get('total_detections', 0)}")
                
                if s['status'] == "PLAYING":
                    view_btn = st.button("👀 View Live Feed", key=f"view_{s['id']}")
                    if view_btn:
                        st.write(f"Viewing Stream {s['id']}")
                        import streamlit.components.v1 as components
                        html_code = f"""
                        <!DOCTYPE html>
                        <html>
                        <body style="margin:0; padding:0; background-color:#0e1117; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; font-family: sans-serif;">
                            <div id="status" style="margin-bottom: 10px; color: #38BDF8;">Connecting to stream...</div>
                            <img id="videoStream" style="max-width: 100%; height: auto; border: 1px solid #333;" />
                            <script>
                                var wsUrl = "{API_BASE_URL}".replace(/^http/, "ws");
                                var ws = new WebSocket(wsUrl + "/streams/live/{s['id']}?token={st.session_state.token}");
                                ws.binaryType = "blob";
                                var img = document.getElementById("videoStream");
                                var statusDiv = document.getElementById("status");
                                
                                ws.onopen = function() {{
                                    statusDiv.innerText = "Connected - Waiting for frames...";
                                }};
                                
                                ws.onmessage = function(event) {{
                                    statusDiv.style.display = 'none'; // Hide status once frames arrive
                                    if (img.src) {{
                                        URL.revokeObjectURL(img.src);
                                    }}
                                    img.src = URL.createObjectURL(event.data);
                                }};
                                
                                ws.onerror = function(error) {{
                                    statusDiv.innerText = "Error: Connection lost or failed to connect.";
                                    statusDiv.style.color = "#ef4444";
                                }};
                                
                                ws.onclose = function() {{
                                    statusDiv.innerText = "Connection closed.";
                                    statusDiv.style.display = 'block';
                                    statusDiv.style.color = "#ef4444";
                                }};
                            </script>
                        </body>
                        </html>
                        """
                        components.html(html_code, height=600)
                st.divider()
