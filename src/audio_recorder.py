import json
import multiprocessing as mp
import os
from typing import Optional

import numpy as np
import sounddevice as sd
from moviepy.editor import AudioFileClip, VideoFileClip
from scipy.io.wavfile import write
from pathlib import Path
import time


class AudioRecorder:
    def __init__(
        self,
        device_id: int = 1,
        sample_rate: int = 44100,
        channels: int = 2,  # use `sd.query_devices(device_id)["max_input_channels"])` to get the number of channels
        chunk_size: int = 1024,
        data_dir: str = str(Path(__file__).parent.parent) + "/recordings",
    ):
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.file_name = ""
        self.channels = channels
        self.chunk_size = chunk_size
        self.data_dir = data_dir
        self.audio_dir = data_dir + "/audios"
        self.process: Optional[mp.Process] = None
        self.stop_event = mp.Event()
        os.makedirs(self.audio_dir, exist_ok=True)
        self.meta_data_dir = data_dir + "/meta_data"
        os.makedirs(self.meta_data_dir, exist_ok=True)

    def start_recording(self, file_name: str):
        self.stop_event.clear()
        if file_name.endswith(".wav"):
            file_name = file_name[:-4]
        # Check whether the subprocess is already running
        if self.process is not None and self.process.is_alive():
            if self.file_name == file_name:
                print(
                    f"AudioRecorder is already recording to file {self.audio_dir}/{file_name}"
                )
            else:
                print(
                    f"AudioRecorder is already recording to file {self.audio_dir}/{self.file_name}, please stop it first."
                )
            return
        self.file_name = file_name
        self.process = mp.Process(target=self.record)
        self.process.start()

    def stop_recording(self):
        if self.process is not None and self.process.is_alive():
            self.stop_event.set()
            self.process.join()
            print("AudioRecorder stopped")
        else:
            print("AudioRecorder is not recording")

    def record(self):
        print("AudioRecorder started")
        audio_data = np.array([])
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device_id,
        ) as stream:
            audio_start_time = time.time()
            while not self.stop_event.is_set():
                data, overflowed = stream.read(self.chunk_size)
                if overflowed:
                    print("Warning: Audio buffer overflowed")
                audio_data = np.concatenate((audio_data, data.ravel()))
            audio_stop_time = time.time()
        write(
            f"{self.audio_dir}/{self.file_name}.wav",
            self.sample_rate,
            audio_data.reshape(-1, self.channels),
        )
        with open(f"{self.meta_data_dir}/{self.file_name}_audio.json", "w") as f:
            json.dump({"start_time": audio_start_time, "stop_time": audio_stop_time}, f)
        print(f"Audio saved to {self.audio_dir}/{self.file_name}.wav")

    def start_merging_to_video(self, raw_video_dir: str, video_dir: str):
        merge_process = mp.Process(
            target=self.merge_to_video,
            args=(
                raw_video_dir,
                video_dir,
            ),
        )
        merge_process.start()

    def merge_to_video(self, raw_video_dir: str, video_dir: str):
        start_time = time.monotonic()
        timeout = 1.0
        while not os.path.exists(f"{raw_video_dir}/{self.file_name}.mp4"):
            if time.monotonic() - start_time > timeout:
                print(f"{raw_video_dir}/{self.file_name}.mp4 does not exist.")
                return
            else:
                time.sleep(0.1)

        with open(f"{self.meta_data_dir}/{self.file_name}_video.json", "r") as f:
            video_meta_data = json.load(f)
        with open(f"{self.meta_data_dir}/{self.file_name}_audio.json", "r") as f:
            audio_meta_data = json.load(f)

        # Audio recording starts earlier than video
        start_time_diff = video_meta_data["start_time"] - audio_meta_data["start_time"]

        final_start_time = max(
            video_meta_data["start_time"], audio_meta_data["start_time"]
        )
        final_stop_time = min(
            video_meta_data["stop_time"], audio_meta_data["stop_time"]
        )
        # Crop video clip and audio clip according to the start and stop time
        video_clip = VideoFileClip(f"{raw_video_dir}/{self.file_name}.mp4")
        # video_clip: VideoFileClip = video_clip.subclip(
        #     final_start_time - video_meta_data["start_time"],
        #     final_stop_time - video_meta_data["start_time"],
        # )
        audio_clip = AudioFileClip(f"{self.audio_dir}/{self.file_name}.wav")
        audio_clip = audio_clip.subclip(
            final_start_time - audio_meta_data["start_time"],
            final_stop_time - audio_meta_data["start_time"],
        )

        final_clip: VideoFileClip = video_clip.set_audio(audio_clip)
        final_clip.write_videofile(f"{video_dir}/{self.file_name}.mp4")
        print(f"Audio merged to {video_dir}/{self.file_name}.mp4")


if __name__ == "__main__":
    audio_recorder = AudioRecorder()
    audio_recorder.file_name = "20240101_121440"
    audio_recorder.merge_to_video(
        audio_recorder.data_dir + "/raw_videos", audio_recorder.data_dir + "/videos"
    )
    # audio_recorder.start_recording("test1")
    # time.sleep(2)
    # audio_recorder.stop_recording()

    # audio_recorder.start_recording("test2")
    # time.sleep(2)
    # audio_recorder.stop_recording()
