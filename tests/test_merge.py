import time
import ffmpeg
import subprocess


def sync_audio_video(video_file, audio_file, output_file):
    command = [
        "ffmpeg",
        "-i",
        video_file,
        "-i",
        audio_file,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-strict",
        "experimental",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        output_file,
    ]
    subprocess.run(command)


video_file = "recordings/raw_videos/20231230_223915.mp4"
audio_file = "recordings/audios/20231230_223915.wav"
video_file_with_start_time = "recordings/raw_videos/20231230_223915_new.mp4"
audio_file = "recordings/audios/20231230_223915.wav"
audio_file_with_start_time = "recordings/audios/20231230_223915_new.wav"
output_file = "recordings/videos/20231230_223915.mp4"

# Get current time in seconds since the Epoch
current_time_seconds = time.time()
delayed_time_seconds = current_time_seconds - 5

# Convert to a struct_time in local time
local_time = time.localtime(current_time_seconds)
# Format the time with milliseconds
formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time) + ".{:03d}".format(
    int((current_time_seconds % 1) * 1000)
)

delayed_formatted_time = time.strftime(
    "%Y-%m-%d %H:%M:%S", time.localtime(delayed_time_seconds)
) + ".{:03d}".format(int((delayed_time_seconds % 1) * 1000))

ffmpeg.input(video_file).output(
    video_file_with_start_time, metadata=f"creation_time={formatted_time}"
).run()

ffmpeg.input(audio_file).output(
    audio_file_with_start_time, metadata=f"creation_time={delayed_formatted_time}"
).run()


sync_audio_video(video_file_with_start_time, audio_file_with_start_time, output_file)
