import asyncio
import logging
import os
from pathlib import Path
import pickle
import time
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import pytz
import zmq.asyncio


class MsgRecorder:
    def __init__(
        self,
        server_ip: str,
        server_port: int,
        data_dir: str = str(Path(__file__).parent.parent) + "/recordings",
        save_msgs_interval: float = 1.0,
        time_zone: str = "America/Los_Angeles",
    ):
        self.server_ip = server_ip
        self.server_port = server_port
        self.context = zmq.asyncio.Context()
        self.pub_socket = None
        self.sub_socket = None

        self.data_dir = data_dir
        self.msg_dir = data_dir + "/messages"
        if not os.path.exists(data_dir + "/messages"):
            os.makedirs(data_dir + "/messages")
        self.save_msgs_interval = save_msgs_interval
        self.receive_start_time_global = time.time()
        self.received_msgs: List[Tuple[float, bytes]] = []
        self.receiving_task: Optional[asyncio.Task] = None
        self.replay_msgs: List[Tuple[float, bytes]] = []
        self.replaying_task: Optional[asyncio.Task] = None
        self.replaying_file_name = ""
        self.replaying_idx = 0

        # To be updated during the video replaying. These values should be updated simultaneously.
        self.update_local_time = time.monotonic()
        self.browser_global_timestamp = time.time()
        """The most recent global timestamp provided by the browser."""
        self.video_replay_timestamp = 0
        """The most recent local timestamp of the video being replayed."""
        self.video_is_playing = False
        """Whether the video in the browser is playing or paused."""

        self.replay_backtrack_time = 0.1

        self.time_zone = pytz.timezone(time_zone)

    async def run_receive(self):
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{self.server_ip}:{self.server_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        start_receive_time = time.monotonic()
        while True:
            received_bytes = await self.sub_socket.recv(flags=0)
            if isinstance(received_bytes, bytes):
                self.received_msgs.append(
                    (time.monotonic() - start_receive_time, received_bytes)
                )
            print(
                f"Time elapsed: {time.monotonic() - start_receive_time:.3f}", end="\r"
            )

    def start_receive(self):
        self.receive_start_time_global = time.time()
        self.received_msgs = []
        if (
            self.receiving_task is None
            or self.receiving_task.done()
            or self.receiving_task.cancelled()
        ):
            self.receiving_task = asyncio.create_task(self.run_receive())

    def stop_receive(self, data_file_name: str = ""):
        if self.receiving_task is not None:
            self.receiving_task.cancel()
            self.receiving_task = None
        if self.sub_socket is not None and not self.sub_socket.closed:
            self.sub_socket.close()
        if self.received_msgs:
            self.save_msgs(data_file_name)
        else:
            print("No message recorded.")

    async def run_replay(self):
        recorded_timestamps = np.array([t for t, _ in self.replay_msgs])
        if len(recorded_timestamps) <= 1:
            print("No message loaded, failed to start replaying.")
            return

        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{self.server_port}")

        prev_browser_time = self.browser_global_timestamp
        prev_video_time = self.video_replay_timestamp
        prev_end_idx = int(np.searchsorted(recorded_timestamps, prev_video_time))
        cursor_jumped = False
        while True:
            current_video_time = (
                self.video_replay_timestamp + time.monotonic() - self.update_local_time
            )

            # Decide whether cursor is jumped either forward or backward
            browser_elapsed_time = self.browser_global_timestamp - prev_browser_time
            video_elapsed_time = self.video_replay_timestamp - prev_video_time

            elapsed_time_diff = browser_elapsed_time - video_elapsed_time
            if abs(elapsed_time_diff) > 0.2:
                cursor_jumped = True
                print(
                    f"Cursor jumped from {prev_video_time:.3f} to {current_video_time:.3f}"
                )
            else:
                cursor_jumped = False

            prev_browser_time = self.browser_global_timestamp
            prev_video_time = self.video_replay_timestamp
            current_idx = int(np.searchsorted(recorded_timestamps, current_video_time))
            if self.video_is_playing:
                print(
                    f"msg_recorder: video replay {self.video_replay_timestamp:.3f}, {current_video_time=:.3f}, {current_idx=}, {prev_end_idx=}"
                )
                if cursor_jumped:
                    prev_end_idx = int(
                        np.searchsorted(
                            recorded_timestamps,
                            max(0, current_video_time - self.replay_backtrack_time),
                        )
                    )

                if current_idx < prev_end_idx:
                    print(
                        "Warning: cursor jumped back in time but cursor_jumped is False. Will not send any messages."
                    )
                    await asyncio.sleep(0.01)

                    continue

                # Send all messages between prev_end_idx and current_idx
                for i in range(prev_end_idx, current_idx):
                    await self.pub_socket.send(self.replay_msgs[i][1])

                prev_end_idx = current_idx
            else:  # Video is not playing
                if cursor_jumped:
                    prev_end_idx = int(
                        np.searchsorted(
                            recorded_timestamps,
                            max(0, current_video_time - self.replay_backtrack_time),
                        )
                    )
            self.replaying_idx = prev_end_idx
            await asyncio.sleep(0.01)

    def start_replay(self, file_name: str):
        if file_name.endswith(".pkl"):
            file_name = file_name[:-4]
        if not os.path.exists(f"{self.msg_dir}/{file_name}.pkl"):
            print(f"{self.msg_dir}/{file_name}.pkl does not exist.")
            return
        self.load_msgs(file_name)
        if len(self.replay_msgs) == 0:
            print("No message loaded, failed to start replaying.")
            return
        # Check whether file_name existed

        self.replaying_file_name = file_name
        if (
            self.replaying_task is None
            or self.replaying_task.done()
            or self.replaying_task.cancelled()
        ):
            self.replaying_task = asyncio.create_task(self.run_replay())
            print(f"self.replaying_task created")
        else:
            print(f"self.replaying_task already exists")

    def stop_replay(self):
        if self.replaying_task is not None:
            self.replaying_task.cancel()
            self.replaying_task = None

        else:
            print(f"self.replaying_task is None")
        if self.pub_socket is not None and not self.pub_socket.closed:
            self.pub_socket.close()
        self.replay_msgs = []
        self.replaying_file_name = ""

    def find_replay_file(self, file_name: str):
        if file_name.endswith(".pkl"):
            file_name = file_name[:-4]
        if os.path.exists(f"{self.msg_dir}/{file_name}.pkl"):
            return True
        else:
            return False

    def save_msgs(self, file_name: str, enable_append: bool = False):
        if file_name == "":
            file_name = datetime.fromtimestamp(
                self.receive_start_time_global, self.time_zone
            ).strftime("%Y%m%d_%H%M%S")
        if file_name.endswith(".pkl"):
            file_name = file_name[:-4]
        if self.received_msgs:
            prev_msgs = []
            if enable_append and os.path.exists(f"{self.msg_dir}/{file_name}.pkl"):
                with open(f"{self.msg_dir}/{file_name}.pkl", "rb") as f:
                    prev_msgs = pickle.load(f)
                print(
                    f"Loaded {len(prev_msgs)} msgs from {self.msg_dir}/{file_name}.pkl"
                )
            with open(f"{self.msg_dir}/{file_name}.pkl", "wb") as f:
                pickle.dump(prev_msgs + self.received_msgs, f)
            print(
                f"Saved {len(prev_msgs + self.received_msgs)} msgs in {self.msg_dir}/{file_name}.pkl"
            )

            self.received_msgs = []
            return True
        else:
            return False

    def load_msgs(self, file_name: str):
        if file_name.endswith(".pkl"):
            file_name = file_name[:-4]
        with open(f"{self.msg_dir}/{file_name}.pkl", "rb") as f:
            loaded_msgs = pickle.load(f)
            print(f"Loaded {len(loaded_msgs)} msgs")
        timestamps = np.array([t for t, _ in loaded_msgs])
        if np.any(timestamps[1:] < timestamps[:-1]):
            print("Warning: timestamps are not in ascending order. Will be sorted")
            self.replay_msgs = sorted(loaded_msgs, key=lambda x: x[0])
        else:
            self.replay_msgs = loaded_msgs


if __name__ == "__main__":
    recorder = MsgRecorder("172.24.95.130", 8800, "recordings/messages")
    # asyncio.run(recorder.run())
    # recorder.load_msgs("20231228_173448.pkl")
    # asyncio.run(recorder.run_replay())
