import asyncio
import time
import cv2
import av
from quart import (
    Quart,
    Response,
    render_template,
    redirect,
    url_for,
    send_from_directory,
    request,
    jsonify,
)
import os
import pytz
from datetime import datetime


class WebServer:
    def __init__(self, time_zone="America/Los_Angeles"):
        self.app = Quart(__name__)
        self.setup_routes()
        self.cap = cv2.VideoCapture()
        self.setup_camera()
        self.recording = False
        self.stream = None
        self.container = None
        self.recordings_dir = "./recordings/videos"
        self.time_zone = pytz.timezone(time_zone)
        self.start_time = time.monotonic()

    def setup_camera(self):
        self.cap.open(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def setup_routes(self):
        self.app.route("/")(self.index)
        self.app.route("/video_feed")(self.video_feed)
        self.app.route("/start_recording", methods=["POST"])(self.start_recording)
        self.app.route("/stop_recording", methods=["POST"])(self.stop_recording)
        # self.app.route("/video_replay")(self.video_replay)
        self.app.route("/progress", methods=["POST"])(self.progress)

        self.app.route("/recordings/<filename>")(self.serve_recording)

    def generate_output_filename(self):
        # Generate a unique file name using the current timestamp
        create_time = datetime.fromtimestamp(time.time(), tz=self.time_zone).strftime(
            "%Y%m%d_%H%M%S"
        )
        return f"{self.recordings_dir}/{create_time}.mp4"

    async def gen_frames(self):
        while True:
            success, frame = self.cap.read()
            if not success:
                break
            else:
                start_time = time.monotonic()
                if self.recording:
                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = av.VideoFrame.from_ndarray(img, format="rgb24")
                    for packet in self.stream.encode(img):
                        self.container.mux(packet)

                ret, buffer = cv2.imencode(".jpg", frame)
                frame = buffer.tobytes()
                # print(
                #     f"Recording: {self.recording}, single frame fps: {1/(time.monotonic() - start_time):.1f}",
                #     end="\r",
                # )
                yield (
                    b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            await asyncio.sleep(0)

    async def index(self):
        os.makedirs(self.recordings_dir, exist_ok=True)
        recording_files = os.listdir(self.recordings_dir)
        recording_files.sort(reverse=True)
        return await render_template(
            "index.html", video_files=recording_files, recording=self.recording
        )

    def video_feed(self):
        return Response(
            self.gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )

    async def start_recording(self):
        print("Enter start_recording")
        if self.recording:
            print("Recording already started!")
            return redirect(url_for("index"))
        self.recording = True
        self.container = av.open(self.generate_output_filename(), mode="w")
        self.stream = self.container.add_stream("h264", rate=24)
        self.stream.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.stream.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.stream.pix_fmt = "yuv420p"
        return redirect(url_for("index"))

    async def stop_recording(self):
        if not self.recording:
            print("Recording has not started!")
            return redirect(url_for("index"))

        self.recording = False
        time.sleep(0.1)
        for packet in self.stream.encode():
            self.container.mux(packet)
        self.container.close()
        return redirect(url_for("index"))

    async def limited_stream(self, path, chunk_size=1024 * 1024, delay=0.1):
        """
        Stream a file with limited bandwidth.

        :param path: File path
        :param chunk_size: Size of each chunk in bytes
        :param delay: Delay between chunks in seconds
        """
        with open(path, "rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk
                await asyncio.sleep(delay)

    async def serve_recording(self, filename):
        return Response(
            self.limited_stream(f"{self.recordings_dir}/{filename}"),
            content_type="video/mp4",
        )

    async def progress(self):
        data = await request.get_json()
        current_time = time.monotonic() - self.start_time
        print(
            f"Progress: current time: {current_time:.3f}, client time stamp: {data['client_timestamp']/1000:.3f}, \
                current video time: {data['time']:.3f} seconds, paused: {data['paused']}"
        )
        return jsonify({"status": "success"})

    def run(self):
        self.app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    server = WebServer()
    server.run()
