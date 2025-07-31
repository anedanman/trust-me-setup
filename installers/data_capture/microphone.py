import os
import time as pytime
import multiprocessing
from datetime import datetime

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import scipy.signal as sps

# Installs for linux: sudo apt install pipewire wireplumber pipewire-audio-client-libraries libpulse-dev libportaudio2 libportaudiocpp0

def formatted_time():
    return "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())


class Mic:
    def __init__(
        self,
        sampling_rate=48000,          # default rate
        n_channels=2,                   # default channels
        final_rate=2000,                 # final rate after resampling
        final_channels=1,                  # final channels goal (stereo -> mono)
        save_directory="data/audio",
        chunk_length=None,
    ):
        print(f"Initialized mic with default rate {sampling_rate}")
        
        self.sampling_rate  = sampling_rate
        self.n_channels     = n_channels
        self.final_channels = final_channels          # still 1 downstream
        self.final_rate     = final_rate
        self.save_directory = save_directory
        self.chunk_length   = chunk_length
        self.recording      = []
        self.is_recording   = False

    # ------------------------------------------------------------------ #
    #  Callback                                                          #
    # ------------------------------------------------------------------ #
    def callback(self, indata, frames, time, status):
        if status:
            print(f"PortAudio status: {status}", flush=True)
        self.recording.append(indata.copy())

    # ------------------------------------------------------------------ #
    #  Device helper (unchanged)                                         #
    # ------------------------------------------------------------------ #
    def find_default_sound_device(self, devs):
        hostapis = sd.query_hostapis()
        for dev in devs:                           # BRIO via Pulse/Wire
            if dev["max_input_channels"] > 0:
                api_name = hostapis[dev["hostapi"]]["name"].lower()
                if ("pulse" in api_name or "wire" in api_name) and \
                   "brio" in dev["name"].lower():
                    print(f"Using BRIO via {hostapis[dev['hostapi']]['name']} "
                          f"(device {dev['index']})")
                    return dev["index"]
        for dev in devs:                           # BRIO via ALSA
            if dev["max_input_channels"] > 0 and "brio" in dev["name"].lower():
                print(f"Using BRIO via {hostapis[dev['hostapi']]['name']} "
                      f"(device {dev['index']})")
                return dev["index"]
        default_dev = sd.default.device           # last resort
        idx = default_dev[0] if isinstance(default_dev, (tuple, list)) else default_dev
        print(f"No BRIO found; falling back to default input device {idx}")
        return idx

    # ------------------------------------------------------------------ #
    #  Main record loop                                                  #
    # ------------------------------------------------------------------ #
    def record(self, termFlag, name, chunkdur, event=None):
        if event is not None:
            event.wait()

        self.name = name
        self.is_recording = True
        print("Recording audio…")

        devs   = sd.query_devices()
        dev_id = self.find_default_sound_device(devs)

        hostapis  = sd.query_hostapis()
        pulse_idx = next(
            (i for i, api in enumerate(hostapis)
             if "pulse" in api["name"].lower() or "wire" in api["name"].lower()),
            None
        )
        if pulse_idx is not None:
            sd.default.hostapi = pulse_idx
            dev_id = None                      # let Pulse choose default

        sd.default.device = (dev_id, None) if dev_id is not None else None

        # --- always record at BRIO's native format ----------------------
        print(f"Opening stream at {self.sampling_rate} Hz, {self.n_channels} ch")

        try:
            with sd.InputStream(
                    samplerate=self.sampling_rate,
                    channels=self.n_channels,
                    dtype='float32',            # exact hardware format
                    device=dev_id,
                    callback=self.callback):

                next_flush = pytime.time() + chunkdur
                while self.is_recording and termFlag.value != 1:
                    pytime.sleep(0.5)
                    if pytime.time() >= next_flush:
                        self.save_recording()
                        self.recording = []
                        next_flush += chunkdur

        except sd.PortAudioError as e:
            print("PortAudio error:", e)
            termFlag.value = 1

        if self.recording:
            self.save_recording()

        sd.stop()
        sd._terminate()

        if termFlag.value == 1:
            print("Termination flag detected. Audio recording has been forced to end.")
        else:
            print("Audio recording stopped normally.")

    # ------------------------------------------------------------------ #
    #  Save helper                                                       #
    # ------------------------------------------------------------------ #
    def save_recording(self):
        """
        Save audio that preserves loudness/rhythm but removes intelligible
        speech by band-limiting to ≤1 kHz and resampling to 8 kHz mono.
        """
        if not self.recording:
            print("No recording to save.")
            return

        x = np.concatenate(self.recording, axis=0).astype(np.float32)

        # 1) stereo → mono
        if x.ndim == 2 and x.shape[1] == 2:
            x = x.mean(axis=1)

        # 2) brick-wall low-pass @ 1 kHz
        cutoff = 1000 / (0.5 * self.sampling_rate)  # normalised
        b, a = sps.butter(8, cutoff, btype='low')
        x = sps.filtfilt(b, a, x)

        # 3) resample to 8 kHz
        target_rate = 8000
        new_len = int(len(x) * target_rate / self.sampling_rate)
        x = sps.resample(x, new_len)

        # 4) normalise to –3 dBFS and int16
        peak = np.max(np.abs(x)) or 1.0
        pcm16 = np.int16(x / peak * 0.7071 * 32767)

        # 5) write WAV
        os.makedirs(self.save_directory, exist_ok=True)
        fname = f"{self.save_directory}/{self.name}_{formatted_time()}.wav"
        write(fname, target_rate, pcm16)
        print(f"Saved band-limited audio to {fname}")



# --------------------------------------------------------------------------
if __name__ == "__main__":
    mic = Mic()
    # mic.record(name="test", event=None)

