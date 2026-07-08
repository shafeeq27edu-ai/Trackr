import streamlit as st
import requests
import tempfile
import json

st.set_page_config(page_title="Trackr CV Dashboard", page_icon="👁️", layout="wide")

st.title("👁️ Trackr: Object Tracking Dashboard")
st.markdown("Upload a video to process it through our YOLOv8 and ByteTrack pipeline. The FastAPI backend handles the heavy lifting.")

# Define the API endpoint
API_URL = "http://localhost:8000/api/v1/process/video"

uploaded_file = st.file_uploader("Upload a video file (.mp4)", type=["mp4"])

if uploaded_file is not None:
    st.info("File uploaded successfully. Click 'Process Video' to begin tracking.")
    
    if st.button("Process Video", type="primary"):
        with st.spinner("Analyzing video on the backend... This may take a few moments."):
            try:
                # Send the file to the FastAPI backend via a POST request
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "video/mp4")}
                response = requests.post(API_URL, files=files)
                
                if response.status_code == 200:
                    st.success("Processing complete!")
                    
                    # Read the custom analytics header
                    analytics_header = response.headers.get("X-Analytics-Summary", "{}")
                    
                    try:
                        counts = json.loads(analytics_header)
                    except json.JSONDecodeError:
                        counts = {}
                    
                    # Layout: 2 columns (Video and Metrics)
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.subheader("Annotated Video")
                        # Write the response content (video bytes) to a temp file so Streamlit can render it
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
                            tmp_vid.write(response.content)
                            tmp_vid_path = tmp_vid.name
                            
                        st.video(tmp_vid_path)
                        
                    with col2:
                        st.subheader("Unique Object Counts")
                        if counts:
                            for class_name, count in counts.items():
                                st.metric(label=f"Total {class_name.title()}s", value=count)
                        else:
                            st.write("No objects detected or tracking data unavailable.")
                            
                else:
                    st.error(f"Failed to process video. Server returned status {response.status_code}.")
                    st.text(response.text)
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend API. Please ensure the FastAPI server is running on http://localhost:8000.")
