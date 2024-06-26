import asyncio
import json
import logging
import os
from pathlib import Path
import time
from datetime import datetime
from typing import Dict, Optional

import av
import cv2
import pytz
from quart import (
    Quart,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
    websocket,
)

from audio_recorder import AudioRecorder
from msg_recorder import MsgRecorder


def parse_range_header(header, total_size):
    # Parse the range header to get start and end byte positions
    range_type, range_spec = header.split("=")
    if range_type != "bytes":
        raise ValueError("Invalid range type")
    start, end = range_spec.split("-")
    start = int(start) if start else 0
    end = int(end) if end else total_size - 1
    return start, end


class WebServer:
    def __init__(
        self,
        time_zone="America/Los_Angeles",
        resolution=(1440, 720),
        msg_recorder: Optional[MsgRecorder] = None,
        audio_recorder: Optional[AudioRecorder] = None,
        data_dir=str(Path(__file__).parent.parent) + "/recordings",
    ):
        self.app = Quart(__name__)
        self.setup_routes()
        self.cap = cv2.VideoCapture()
        self.is_recording = False
        self.stream = None
        self.container = None
        self.data_dir = data_dir
        if audio_recorder is None:
            print(
                f"AudioRecorder is not provided, will store video files to {self.data_dir}/videos directly."
            )
            self.raw_video_dir = data_dir + "/videos"
        else:
            self.raw_video_dir = data_dir + "/raw_videos"
        self.video_dir = data_dir + "/videos"
        self.meta_data_dir = data_dir + "/meta_data"

        os.makedirs(self.raw_video_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        os.makedirs(self.meta_data_dir, exist_ok=True)

        self.time_zone = pytz.timezone(time_zone)
        self.record_start_time = time.time()
        self.record_file_name = ""
        self.record_start_time_accurate = time.time()
        self.replay_start_time = time.time()
        self.recorded_frame_num = 0
        self.resolution = resolution
        self.client_ip = ""

        self.app.before_serving(self.setup_camera)
        self.app.after_serving(self.release_camera)

        self.app.websocket("/ws")(self.ws)
        self.msg_recorder = msg_recorder
        self.audio_recorder = audio_recorder

    async def ws(self):
        while True:
            ws_started_time = time.monotonic()
            ws_msg_dict: Dict[str, Optional[str]] = {"client_ip": self.client_ip}
            if self.is_recording:
                recording_time = time.time() - self.record_start_time
                # Transform recording_time to MM:SS
                ws_msg_dict["recording_time"] = time.strftime(
                    "%M:%S", time.gmtime(recording_time)
                )
            else:
                ws_msg_dict["recording_time"] = "00:00"

            if self.msg_recorder:
                ws_msg_dict["received_msg_num"] = str(
                    len(self.msg_recorder.received_msgs)
                )
                ws_msg_dict["loaded_msg_num"] = str(len(self.msg_recorder.replay_msgs))
                ws_msg_dict["replaying_msg_idx"] = str(self.msg_recorder.replaying_idx)
            else:
                ws_msg_dict["received_msg_num"] = str(0)
                ws_msg_dict["loaded_msg_num"] = str(0)
                ws_msg_dict["replaying_msg_idx"] = str(0)
            if self.client_ip:
                await websocket.send(json.dumps(ws_msg_dict))
            await asyncio.sleep(0.5)

    async def release_camera(self):
        if self.cap.isOpened():
            self.cap.release()
        print("Camera released")

    def setup_camera(self):
        if not self.cap.isOpened():
            self.cap.open(0)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        print(f"Camera initialized with resolution {self.resolution}")

    def setup_routes(self):
        self.app.route("/")(self.index)
        self.app.route("/video_feed")(self.video_feed)
        self.app.route("/start_recording", methods=["POST"])(self.start_recording)
        self.app.route("/stop_recording", methods=["POST"])(self.stop_recording)
        # self.app.route("/video_replay")(self.video_replay)
        self.app.route("/progress", methods=["POST"])(self.progress)

        self.app.route("/recordings/<filename>")(self.serve_recording)

    async def gen_frames(self):
        while True:
            success, frame = self.cap.read()
            if not success:
                await asyncio.sleep(0.1)
            else:
                start_time = time.monotonic()
                if self.is_recording:
                    if self.recorded_frame_num == 0:
                        print(
                            f"Record starting time difference: {self.record_start_time_accurate - self.record_start_time:.3f}"
                        )
                        if self.msg_recorder:
                            self.msg_recorder.start_receive()
                        if self.audio_recorder:
                            self.audio_recorder.start_recording(self.record_file_name)
                        self.record_start_time_accurate = time.time()

                    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = av.VideoFrame.from_ndarray(img, format="rgb24")
                    for packet in self.stream.encode(img):
                        self.container.mux(packet)
                    self.recorded_frame_num += 1

                ret, buffer = cv2.imencode(".jpg", frame)
                frame = buffer.tobytes()
                # print(
                #     f"Recording: {self.is_recording}, single frame fps: {1/(time.monotonic() - start_time):.1f}",
                #     end="\r",
                # )

                yield (
                    b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )

            await asyncio.sleep(0)

    async def index(self):
        recording_files = os.listdir(self.video_dir)
        recording_files.sort(reverse=True)
        return await render_template(
            "index.html",
            video_files=recording_files,
            recording=self.is_recording,
            client_ip=self.client_ip,
        )

    def video_feed(self):
        return Response(
            self.gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )

    async def start_recording(self):
        print("Enter start_recording")
        if self.is_recording:
            print("Recording already started!")
            return redirect(url_for("index"))
        self.record_start_time = time.time()
        self.recorded_frame_num = 0
        self.is_recording = True

        self.record_file_name = datetime.fromtimestamp(
            self.record_start_time, tz=self.time_zone
        ).strftime("%Y%m%d_%H%M%S")
        file_path = f"{self.raw_video_dir}/{self.record_file_name}.mp4"

        self.container = av.open(file_path, mode="w")
        self.stream = self.container.add_stream(
            "h264", rate=self.cap.get(cv2.CAP_PROP_FPS)
        )
        self.stream.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.stream.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.stream.pix_fmt = "yuv420p"

        return redirect(url_for("index"))

    async def stop_recording(self):
        if not self.is_recording:
            print("Recording has not started!")
            return redirect(url_for("index"))

        self.is_recording = False
        time.sleep(0.1)
        stop_recording_time = time.time()
        for packet in self.stream.encode():
            self.container.mux(packet)
        self.container.close()

        with open(f"{self.meta_data_dir}/{self.record_file_name}_video.json", "w") as f:
            json.dump(
                {
                    "start_time": self.record_start_time,
                    "stop_time": stop_recording_time,
                    "frame_rate": self.cap.get(cv2.CAP_PROP_FPS),
                    "resolution": [self.stream.width, self.stream.height],
                    "recorded_frame_num": self.recorded_frame_num,
                },
                f,
            )

        if self.msg_recorder:
            self.msg_recorder.stop_receive(data_file_name=self.record_file_name)

        if self.audio_recorder:
            self.audio_recorder.stop_recording()
            self.audio_recorder.start_merging_to_video(
                self.raw_video_dir, self.video_dir
            )

        return redirect(url_for("index"))

    async def limited_stream(self, path, range_header=None, chunk_size=1024 * 1024):
        start, end = 0, None
        total_size = os.path.getsize(path)

        if range_header:
            start, end = parse_range_header(range_header, total_size)
            if end is None:
                end = total_size - 1

        with open(path, "rb") as file:
            file.seek(start)
            if end is None:
                end = total_size - 1

            remaining = end - start + 1
            while remaining > 0:
                chunk = file.read(min(chunk_size, remaining))
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    async def serve_recording(self, filename):
        range_header = request.headers.get("Range")
        print(f"serve_recording: filename: {filename}, range_header: {range_header}")
        total_size = os.path.getsize(f"{self.video_dir}/{filename}")

        if self.msg_recorder:
            msg_file_name = filename
            if msg_file_name.endswith(".mp4"):
                msg_file_name = msg_file_name[:-4]
            if self.msg_recorder.replaying_file_name != msg_file_name:
                if self.msg_recorder.replaying_file_name != "":
                    self.msg_recorder.stop_replay()
                if self.msg_recorder.find_replay_file(msg_file_name):
                    self.msg_recorder.start_replay(msg_file_name)

        if range_header:
            start, end = parse_range_header(range_header, total_size)
            content_range_header = f"bytes {start}-{end}/{total_size}"
            return Response(
                self.limited_stream(f"{self.video_dir}/{filename}", range_header),
                status=206,  # Partial Content
                content_type="video/mp4",
                headers={"Content-Range": content_range_header},
            )
        else:
            return Response(
                self.limited_stream(f"{self.video_dir}/{filename}"),
                content_type="video/mp4",
            )

    async def progress(self):
        logging.getLogger("hypercorn.access").setLevel(logging.WARNING)
        data = await request.get_json()

        if self.msg_recorder:
            msg_file_name = data["video_filename"]
            if msg_file_name.endswith(".mp4"):
                msg_file_name = msg_file_name[:-4]

            if self.msg_recorder.replaying_file_name != msg_file_name:
                if self.msg_recorder.replaying_file_name != "":
                    self.msg_recorder.stop_replay()
                if self.msg_recorder.find_replay_file(msg_file_name):
                    self.msg_recorder.start_replay(msg_file_name)
            self.msg_recorder.update_local_time = time.monotonic()
            self.msg_recorder.browser_global_timestamp = data["client_timestamp"]
            self.msg_recorder.video_replay_timestamp = data["video_timestamp"]
            self.msg_recorder.video_is_playing = data["is_playing"]
            print(
                f"{data['client_timestamp']:.3f}, {data['video_timestamp']:.3f}, {data['is_playing']}"
            )

        self.client_ip = request.remote_addr
        return jsonify({"status": "success"})

    def run(self):
        self.app.run(host="0.0.0.0", port=5000, use_reloader=False)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()
        if self.msg_recorder:
            self.msg_recorder.stop_receive()
            self.msg_recorder.stop_replay()


if __name__ == "__main__":
    msg_recorder = MsgRecorder("172.24.95.130", 8800)
    # audio_recorder = AudioRecorder()
    # server = WebServer(msg_recorder=msg_recorder, audio_recorder=audio_recorder)

    server = WebServer(msg_recorder=msg_recorder)
    server.run()
