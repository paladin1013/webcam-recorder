import time
from flask import (
    Flask,
    Response,
    render_template,
    redirect,
    url_for,
    send_from_directory,
)
import cv2
import threading
import os
import av

app = Flask(__name__)

# Global variables
outputFile = "recorded.mp4"
cap = cv2.VideoCapture()
cap.open(0)
recording = False


def gen_frames():
    global recording, stream, container
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            if recording:
                # Convert the frame to PIL Image
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = av.VideoFrame.from_ndarray(img, format="rgb24")
                # Encode and write the frame
                print("gen_frames: writing frame")
                for packet in stream.encode(img):
                    container.mux(packet)
                print("gen_frames: done writing frame")

            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/start_recording", methods=["POST"])
def start_recording():
    global recording, stream, container
    recording = True
    container = av.open(outputFile, mode="w")
    stream = container.add_stream("h264", rate=24)
    stream.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    stream.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    stream.pix_fmt = "yuv420p"

    return redirect(url_for("index"))


@app.route("/stop_recording", methods=["POST"])
def stop_recording():
    global recording, stream, container
    recording = False
    # Finalize the video file
    time.sleep(0.1)
    # Finalize the video file
    print("stop_recording: finalizing video file")
    for packet in stream.encode():
        container.mux(packet)
    container.close()
    print("stop_recording: done finalizing video file")
    return redirect(url_for("index"))


@app.route("/video")
def video():
    return send_from_directory(directory=".", path=outputFile)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
