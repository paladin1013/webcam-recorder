import asyncio
import os
import pickle
import time
from datetime import datetime
from typing import List, Tuple
import zmq.asyncio
import pytz


class TrajRecorder:
    def __init__(
        self,
        server_ip: str,
        server_port: int,
        data_dir: str,
        save_data_interval: float = 1.0,
        time_zone: str = "America/Los_Angeles",
    ):
        self.server_ip = server_ip
        self.server_port = server_port
        self.context = zmq.asyncio.Context()
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{server_ip}:{server_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.data_dir = data_dir
        self.save_data_interval = save_data_interval
        self.start_global_time = time.time()
        self.received_msgs: List[Tuple[float, bytes]] = []
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{server_port}")
        self.time_zone = pytz.timezone(time_zone)

    async def run_receive(self):
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

    def save_data(self, file_name: str):
        if file_name.endswith(".pkl"):
            file_name = file_name[:-4]
        if self.received_msgs:
            prev_msgs = []
            if os.path.exists(f"{self.data_dir}/{file_name}.pkl"):
                with open(f"{self.data_dir}/{file_name}.pkl", "rb") as f:
                    prev_msgs = pickle.load(f)
            with open(f"{self.data_dir}/{file_name}.pkl", "wb") as f:
                pickle.dump(prev_msgs + self.received_msgs, f)
            print(
                f"Saved additional {len(self.received_msgs)} msgs in {self.data_dir}/{file_name}.pkl"
            )

            self.received_msgs = []
            return True
        else:
            return False

    async def save_data_periodically(self):
        patch_id = 0
        while True:
            file_name = datetime.fromtimestamp(
                self.start_global_time, self.time_zone
            ).strftime("%Y%m%d_%H%M%S")
            saved = self.save_data(file_name)
            if saved:
                patch_id += 1
            await asyncio.sleep(self.save_data_interval)

    async def replay_data(self, file_name: str):
        if file_name.endswith(".pkl"):
            file_name = file_name[:-4]
        with open(f"{self.data_dir}/{file_name}.pkl", "rb") as f:
            msgs = pickle.load(f)
            print(f"Replaying {len(msgs)} msgs")
        replay_start_time = time.monotonic()
        for t, msg in msgs:
            target_time = replay_start_time + t
            sleep_time = max(0, target_time - time.monotonic())
            await asyncio.sleep(sleep_time)
            await self.pub_socket.send(msg)
            print(f"Time elapsed: {time.monotonic() - replay_start_time:.3f}", end="\r")

    async def run(self):
        await asyncio.gather(self.run_receive(), self.save_data_periodically())


if __name__ == "__main__":
    recorder = TrajRecorder("172.24.95.130", 8800, "recordings/trajectories")
    # asyncio.run(recorder.run())
    # asyncio.run(recorder.replay_data("20231228_173448.pkl"))
