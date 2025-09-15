import os
import time as pytime
import multiprocessing
from datetime import datetime
import wave  # NEW

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write  # still used nowhere now; can keep or remove
import scipy.signal as sps

# Installs for linux: sudo apt install pipewire wireplumber pipewire-audio-client-libraries libpulse-dev libportaudio2 libportaudiocpp0

def formatted_time():
    return "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())


class Mic:
    def __init__(
        self,
        sampling_rate=48000,          # device rate
        n_channels=2,                 # device channels
        final_rate=8000,              # file/output rate (keep 8k as in save_recording)
        final_channels=1,             # file/output channels (mono)
        save_directory="data/audio",
        chunk_length=None,
    ):
        print(f"Initialized mic with default rate {sampling_rate}")
        
        self.sampling_rate  = sampling_rate
        self.n_channels     = n_channels
        self.final_channels = final_channels
        self.final_rate     = final_rate
        self.save_directory = save_directory
        self.chunk_length   = chunk_length
        self.recording      = []
        self.is_recording   = False
        self.chunk_nr       = 0
        self.current_stamp  = None

        # NEW: streaming writer + small periodic flush
        self.wf = None
        self.small_flush = 0.5  # seconds between appends

        # optional: track overflow without printing in callback
        self.overflow_count = 0
        self.last_status = ""

    # ------------------------------------------------------------------ #
    #  Callback                                                          #
    # ------------------------------------------------------------------ #
    def callback(self, indata, frames, time, status):
        # Avoid prints in realtime thread (can cause overflows)
        if status:
            try:
                if hasattr(status, "input_overflow") and status.input_overflow:
                    self.overflow_count += 1
            except Exception:
                pass
            self.last_status = str(status)
        self.recording.append(indata.copy())

    # ------------------------------------------------------------------ #
    #  Device helper                                                     #
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
    #  Helpers to open/close the current chunk WAV                       #
    # ------------------------------------------------------------------ #
    def _open_chunk_wav(self):
        """Open a new WAV for the current chunk and write a valid header."""
        os.makedirs(self.save_directory, exist_ok=True)
        fname = os.path.join(
            self.save_directory,
            f"{self.name}_chunk{self.chunk_nr}_{self.current_stamp}.wav"
        )
        self.wf = wave.open(fname, "wb")
        self.wf.setnchannels(self.final_channels)   # mono
        self.wf.setsampwidth(2)                     # int16
        self.wf.setframerate(self.final_rate)       # 8 kHz
        # header is written now; file size > 0 immediately

    def _close_chunk_wav(self):
        if self.wf is not None:
            try:
                self.wf.close()
            except Exception:
                pass
            self.wf = None

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

        print(f"Opening stream at {self.sampling_rate} Hz, {self.n_channels} ch")

        try:
            with sd.InputStream(
                    samplerate=self.sampling_rate,
                    channels=self.n_channels,
                    dtype='float32',
                    device=dev_id,
                    callback=self.callback):

                # Start first chunk file
                self.current_stamp = formatted_time()
                self.chunk_nr = 0
                self._open_chunk_wav()

                next_small_flush = pytime.time() + self.small_flush
                next_rotate = pytime.time() + chunkdur

                while self.is_recording and termFlag.value != 1:
                    now = pytime.time()

                    # append buffered audio frequently
                    if now >= next_small_flush:
                        self.save_recording()        # appends to same WAV
                        next_small_flush += self.small_flush

                    # rotate file per chunk duration (like camera)
                    if now >= next_rotate:
                        # flush remaining, close old, open new
                        self.save_recording()
                        self._close_chunk_wav()
                        self.chunk_nr += 1
                        self.current_stamp = formatted_time()
                        self._open_chunk_wav()
                        next_rotate += chunkdur

        except sd.PortAudioError as e:
            print("PortAudio error:", e)
            termFlag.value = 1

        # final flush & close
        self.save_recording()
        self._close_chunk_wav()

        sd.stop()
        sd._terminate()

        if termFlag.value == 1:
            print("Termination flag detected. Audio recording has been forced to end.")
        else:
            print("Audio recording stopped normally.")

    # ------------------------------------------------------------------ #
    #  Save helper (now appends to the open WAV)                         #
    # ------------------------------------------------------------------ #
    def save_recording(self):
        """
        Append processed audio to the current WAV:
        - stereo → mono
        - low-pass @ 1 kHz
        - resample to 8 kHz
        - normalize, int16
        """
        if not self.recording or self.wf is None:
            return

        # move buffered blocks out atomically
        blocks, self.recording = self.recording, []
        x = np.concatenate(blocks, axis=0).astype(np.float32)

        # stereo → mono
        if x.ndim == 2 and x.shape[1] == 2:
            x = x.mean(axis=1)

        # brick-wall low-pass @ 1 kHz
        cutoff = 1000 / (0.5 * self.sampling_rate)
        b, a = sps.butter(8, cutoff, btype='low')
        x = sps.filtfilt(b, a, x)

        # resample to 8 kHz
        target_rate = self.final_rate  # 8000 by default
        new_len = int(len(x) * target_rate / self.sampling_rate)
        if new_len <= 0:
            return
        x = sps.resample(x, new_len)

        # normalize & convert to int16
        peak = np.max(np.abs(x)) or 1.0
        pcm16 = np.int16(x / peak * 0.7071 * 32767)

        # append frames
        try:
            self.wf.writeframes(pcm16.tobytes())
        except Exception as e:
            # don't crash capture on transient disk errors
            print(f"Audio write error: {e}")

