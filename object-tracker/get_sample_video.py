import urllib.request
import os


def download_video():
    """
    Downloads a short sample video for testing the object tracking pipeline.
    """
    url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/people-detection.mp4"
    output_dir = "data/sample_videos"
    output_path = os.path.join(output_dir, "sample.mp4")

    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(output_path):
        print(f"Downloading sample video to {output_path}...")
        urllib.request.urlretrieve(url, output_path)
        print("Download complete.")
    else:
        print(f"Sample video already exists at {output_path}.")


if __name__ == "__main__":
    download_video()
