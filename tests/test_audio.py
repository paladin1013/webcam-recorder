import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import moviepy

# Parameters
fs = 44100  # Sample rate
seconds = 5  # Duration of recording
filename = "output.wav"  # Output filename

# List all available devices
print("Available audio devices:")
print(sd.query_devices())

# Replace this with your device ID or name
my_device = 1

# Query device information
device_info = sd.query_devices(my_device)
print(f"Device info for '{my_device}':")
print(device_info)

# Number of input channels
num_channels = device_info["max_input_channels"]
print(f"Maximum input channels: {num_channels}")

# Recording
print("Recording...")
myrecording = sd.rec(
    int(seconds * fs), samplerate=fs, channels=2, dtype="float64", device=1
)
sd.wait()  # Wait until recording is finished
print("Recording finished")

# Save as WAV file
write(filename, fs, myrecording)  # Save as WAV file
print(f"File saved as {filename}")
