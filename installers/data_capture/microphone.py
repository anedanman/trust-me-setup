import os
import time as pytime
from datetime import datetime

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write


def formatted_time():
    return '{:%Y-%m-%d$%H-%M-%S-%f}'.format(datetime.now())


class Mic:
    def __init__(
        self,
        sampling_rate=44100,
        n_channels=1,
        save_directory="data/audio",
        chunk_length=60 * 60 * 2,
    ):
        print(f"Initialized mic with sampling rate {sampling_rate}")

        self.n_channels = n_channels
        self.sampling_rate = sampling_rate
        self.sampling_rate = sampling_rate
        self.save_directory = save_directory
        self.chunk_length = chunk_length
        self.recording = []

    def callback(self, indata, frames, time, status):
        if status:
            print(f"Error: {status}", flush=True)
        self.recording.append(indata.copy())

    
    def find_streamcam_mic(self, devs):
        for dev in devs:
            if "StreamCam" in dev["name"]:
                return dev["index"]

    def record(self, name, duration, event):
        if duration is None or duration < 0:
            duration = np.inf

        self.duration = duration

        if event is not None:
            event.wait()

        self.name = name
        self.is_recording = True
        print("Recording audio... Press Ctrl+C to stop.")

        start_time = pytime.time()

        devs = sd.query_devices()
        dev_id = self.find_streamcam_mic(devs)
        
        with sd.InputStream(
            device=dev_id,
            samplerate=self.sampling_rate,
            channels=self.n_channels,
            callback=self.callback,
        ):
            try:
                while self.is_recording and pytime.time() - start_time < duration:
                    if pytime.time() - start_time > self.duration:
                        break

                    pytime.sleep(1)
            except KeyboardInterrupt:
                print("Recording stopped by user.")
            finally:
                self.is_recording = False
                self.save_recording()

    def save_recording(self):
        if self.recording:
            recording_np = np.concatenate(np.array(self.recording), axis=0)
            filename = f"{self.save_directory}/{self.name}_{formatted_time()}.wav"

            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory)

            write(filename, self.sampling_rate, recording_np)
            print(f"Recording saved to {filename}")
        else:
            print("No recording to save.")
