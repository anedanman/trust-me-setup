import os
import time as pytime
import multiprocessing
from datetime import datetime

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
from utils import save_pid
from scipy.io import wavfile
import scipy.signal as sps
def formatted_time():
    return "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())


class Mic:
    def __init__(
        self,
        sampling_rate=16000,
        final_rate=900,
        n_channels=1,
        save_directory="data/audio",
        chunk_length=60 * 60 * 2,
    ):
        print(f"Initialized mic with sampling rate {sampling_rate}")

        self.n_channels = n_channels
        self.sampling_rate = sampling_rate
        self.save_directory = save_directory
        self.chunk_length = chunk_length
        self.final_rate = final_rate
        self.recording = []

    def callback(self, indata, frames, time, status):
        if status:
            print(f"Error: {status}", flush=True)
        self.recording.append(indata.copy())

    def find_default_sound_device(self, devs):
        brio = False
        for dev in devs:
            if dev["max_input_channels"] > 0:
                if "brio" in dev["name"].lower():
                    print("Using BRIO Mic")
                    brio = True        
                    return dev["index"]
        if not brio:
            print("Can't find BRIO microphone. Try plugging BRIO in and out.")
        exit()
        # return sd.default.device
        

    def record(self, termFlag, name, chunkdur, event):
        if event is not None:
            event.wait()

        self.name = name
        self.is_recording = True
        
        print("Recording audio... Press Ctrl+C to stop.")

        devs = sd.query_devices()
        dev_id = self.find_default_sound_device(devs)
        start_time = pytime.time()

        while self.is_recording and termFlag.value != 1:
            with sd.InputStream(
                device=dev_id,
                samplerate=self.sampling_rate,
                channels=self.n_channels,
                callback=self.callback,
            ):
                try:
                    while pytime.time() - start_time < chunkdur and termFlag.value != 1:
                        pytime.sleep(1)
                except KeyboardInterrupt:
                    print("Recording stopped by user.")
                    self.is_recording = False
                    break
                
            self.save_recording()
            self.recording = []
            start_time = pytime.time()
            if(termFlag.value == 1):
                print("Termination flag detected. Audio recording has been forced to end.")
                break
                
    def save_recording(self):
        if self.recording:
            # Convert list of recordings to a numpy array
            recording_np = np.concatenate([np.array(chunk) for chunk in self.recording], axis=0)
            
            # Resample
            new_len = int(len(recording_np) * (self.final_rate / self.sampling_rate))
            recording_np = sps.resample(recording_np, new_len)
            # Ensure the directory exists
            if not os.path.exists(self.save_directory):
                os.makedirs(self.save_directory)
            # Convert to a supported data type before saving
            if recording_np.dtype == 'float64':  # sounddevice might return float64
                # Normalize and convert to int16
                recording_int16 = np.int16(recording_np / np.max(np.abs(recording_np)) * 32767)
                filename = f"{self.save_directory}/{self.name}_{formatted_time()}.wav"
                write(filename, self.final_rate, recording_int16)
            else:
                # Save directly if already a supported type
                filename = f"{self.save_directory}/{self.name}_{formatted_time()}.wav"
                write(filename, self.final_rate, recording_np)
            print(f"Recording saved to {filename}")
        else:
            print("No recording to save.")
if __name__ == "__main__":
    mic = Mic()    
    # mic.record(name="test", event=None)
