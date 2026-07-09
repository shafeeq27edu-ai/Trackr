import streamlit as st
import requests
import time
import pandas as pd
import json

st.set_page_config(page_title="Trackr Advanced Analytics", page_icon="🎥", layout="wide")

API_BASE_URL = "http://localhost:8000/api/v1"
SYS_API_BASE_URL = "http://localhost:8000/api/v1/system"

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
                if register(r_email, r_pwd, r_name):
                    st.success("Registered! You can now log in.")
                else:
                    st.error("Registration failed. Email might exist.")
    st.stop()

# --- Main App (Logged In) ---
st.title("🎥 Trackr: Advanced Intelligence & Analytics")

# --- Sidebar ---
st.sidebar.title(f"👤 {st.session_state.user.get('name', 'User')}")
st.sidebar.write(st.session_state.user.get('email'))
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
            requests.post(f"{API_BASE_URL}/projects", json={"name": new_p_name}, headers=get_auth_headers())
            st.rerun()
st.sidebar.divider()

st.sidebar.title("🖥️ System Health")
try:
    perf_res = requests.get(f"{SYS_API_BASE_URL}/performance")
    res_res = requests.get(f"{SYS_API_BASE_URL}/resources")
    models_res = requests.get(f"{SYS_API_BASE_URL}/models")
    
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
        uploaded_file = st.file_uploader("Upload a video file (.mp4)", type=["mp4"])
        if uploaded_file is not None:
            if st.button("Process Video"):
                with st.spinner("Uploading and queueing job..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "video/mp4")}
                    # We pass the token in headers, and project_id in data/form
                    data = {"project_id": st.session_state.selected_project_id}
                    response = requests.post(f"{API_BASE_URL}/jobs/upload", files=files, data=data, headers=get_auth_headers())
                    
                if response.status_code == 200:
                    data = response.json()
                    job_id = data.get("job_id")
                    st.success(f"Job Queued! ID: {job_id}")
                    
                    progress_bar = st.progress(0.0)
                    status_text = st.empty()
                    
                    while True:
                        time.sleep(1)
                        status_res = requests.get(f"{API_BASE_URL}/jobs/{job_id}", headers=get_auth_headers())
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
                                break
                            elif status == "FAILED":
                                st.error(f"Processing failed: {job.get('error')}")
                                break
                        else:
                            st.error(f"Failed to fetch job status: {status_res.text}")
                            break
                else:
                    st.error(f"Failed to queue job: {response.text}")
                    
        # List jobs for this project
        st.divider()
        st.subheader("Job History")
        jobs_res = requests.get(f"{API_BASE_URL}/jobs", headers=get_auth_headers())
        if jobs_res.status_code == 200:
            all_jobs = jobs_res.json().get("jobs", [])
            # Filter jobs matching current project manually for UI
            proj_jobs = [j for j in all_jobs if j.get("project_id") == st.session_state.selected_project_id]
            
            if not proj_jobs:
                st.info("No jobs found in this project.")
            else:
                for j in reversed(proj_jobs):
                    with st.expander(f"Job {j['id'][:8]}... - {j['filename']} ({j['status']})"):
                        if j['status'] == "COMPLETED":
                            if st.button("Load Results", key=f"load_{j['id']}"):
                                # Fetch analytics
                                analytics_res = requests.get(f"{API_BASE_URL}/jobs/{j['id']}/analytics", headers=get_auth_headers())
                                if analytics_res.status_code == 200:
                                    st.json(analytics_res.json())
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
                
                if s['status'] == "PLAYING":
                    view_btn = st.button("👀 View Live Feed", key=f"view_{s['id']}")
                    if view_btn:
                        st.write(f"Viewing Stream {s['id']}")
                        image_placeholder = st.empty()
                        
                        import asyncio
                        import websockets
                        
                        async def view_stream():
                            # NOTE: For websockets, we usually pass token in URL. For MVP, we ignore WS auth or add it if implemented
                            uri = f"ws://localhost:8000/api/v1/streams/live/{s['id']}"
                            try:
                                async with websockets.connect(uri) as websocket:
                                    while True:
                                        data = await websocket.recv()
                                        msg = json.loads(data)
                                        frame_data = msg["frame"]
                                        image_placeholder.image(f"data:image/jpeg;base64,{frame_data}", use_container_width=True)
                            except Exception as e:
                                st.error(f"WebSocket closed: {e}")
                                
                        asyncio.run(view_stream())
                st.divider()
