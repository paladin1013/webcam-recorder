import multiprocessing as mp
import os

import numpy as np
import sounddevice as sd
from moviepy.editor import AudioFileClip, VideoFileClip
from scipy.io.wavfile import write


class AudioRecorder(mp.Process):
    def __init__(
        self,
        device_id: int = 1,
        sample_rate: int = 44100,
        channels: int = 2,  # use `sd.query_devices(device_id)["max_input_channels"])` to get the number of channels
        chunk_size: int = 1024,
        data_dir: str = "recordings/audios",
    ):
        super(AudioRecorder, self).__init__()
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.file_name = ""
        self.channels = channels
        self.chunk_size = chunk_size
        self.stop_event = mp.Event()
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def start_recording(self, file_name: str):
        if file_name.endswith(".wav"):
            file_name = file_name[:-4]
        # Check whether the subprocess is already running
        if self.is_alive():
            if self.file_name == file_name:
                print(
                    f"AudioRecorder is already recording to file {self.data_dir}/{file_name}"
                )
            else:
                print(
                    f"AudioRecorder is already recording to file {self.data_dir}/{self.file_name}, please stop it first."
                )
            return
        self.file_name = file_name
        self.start()

    def stop_recording(self):
        if self.is_alive():
            self.stop_event.set()
            self.join()
        else:
            print("AudioRecorder is not recording")

    def run(self):
        print("AudioRecorder started")
        audio_data = np.array([])
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device_id,
        ) as stream:
            while not self.stop_event.is_set():
                data, overflowed = stream.read(self.chunk_size)
                if overflowed:
                    print("Warning: Audio buffer overflowed")
                audio_data = np.concatenate((audio_data, data.ravel()))

        write(
            f"{self.data_dir}/{self.file_name}.wav",
            self.sample_rate,
            audio_data.reshape(-1, self.channels),
        )
        print(f"Audio saved to {self.data_dir}/{self.file_name}.wav")

    def merge_to_video(self, video_dir: str):
        if not os.path.exists(f"{video_dir}/{self.file_name}.mp4"):
            print(f"{video_dir}/{self.file_name}.mp4 does not exist.")
            return
        video_clip = VideoFileClip(f"{video_dir}/{self.file_name}.mp4")
        audio_clip = AudioFileClip(f"{self.data_dir}/{self.file_name}.wav")
        final_clip: VideoFileClip = video_clip.set_audio(audio_clip)
        final_clip.write_videofile(f"{video_dir}/{self.file_name}.mp4")


if __name__ == "__main__":
    audio_recorder = AudioRecorder()
    audio_recorder.start_recording("test")
    import time

    time.sleep(5)
    audio_recorder.stop_recording()
