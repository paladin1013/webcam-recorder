import asyncio
import time
from quart import (
    Quart,
    Response,
    render_template,
    redirect,
    url_for,
    send_from_directory,
)
import cv2
import av

app = Quart(__name__)

# Global variables
outputFile = "recorded.mp4"
cap = cv2.VideoCapture()

cap.open(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
recording = False


async def gen_frames():
    global recording, stream, container
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            start_time = time.monotonic()
            if recording:
                # Convert the frame to PIL Image
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = av.VideoFrame.from_ndarray(img, format="rgb24")
                # Encode and write the frame
                for packet in stream.encode(img):
                    container.mux(packet)

            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            end_time = time.monotonic()
            print(f"Single frame fps: {1/(end_time - start_time):.1f}", end="\r")
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        await asyncio.sleep(0)


@app.route("/")
async def index():
    return await render_template("index.html")


@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/start_recording", methods=["POST"])
async def start_recording():
    global recording, stream, container
    recording = True
    container = av.open(outputFile, mode="w")
    stream = container.add_stream("h264", rate=24)
    stream.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    stream.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video resolution: {stream.width}x{stream.height}")
    stream.pix_fmt = "yuv420p"

    return redirect(url_for("index"))


@app.route("/stop_recording", methods=["POST"])
async def stop_recording():
    global recording, stream, container
    recording = False
    # Wait until the video frames are written
    time.sleep(0.1)
    # Finalize the video file
    for packet in stream.encode():
        container.mux(packet)
    container.close()
    return redirect(url_for("index"))


@app.route("/video")
async def video():
    return await send_from_directory(directory=".", file_name=outputFile)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
