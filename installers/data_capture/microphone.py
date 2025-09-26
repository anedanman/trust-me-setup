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
        
        self._blur_b = None        # FIR coeffs for temporal blur
        self._blur_zi1 = self._blur_zi2 = self._blur_zi3 = None  # lfilter states
        self._peak_slow = None     # running peak estimate
        self._gain = 1.0           # smoothed output gain
        
        self._scramble_buf = np.zeros(0, dtype=np.float32)  # leftover samples between calls
        self._frame_len = None
        self._frames_per_group = 10   # ~240 ms if frame_len ~40 ms
        self._xfade_len = 20
        self._peak_slow = None       # for smoothed gain (no pops)
        self._gain = 0.3


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
        Time-scramble within short windows to reduce intelligibility but keep the scene feel:
        - mono mix
        - slice into ~40 ms frames
        - randomize frame order within ~240 ms groups
        - short crossfade between frames to avoid clicks
        - smoothed output gain (no per-chunk pops)
        - optional resample to self.final_rate
        - append to the already-open WAV (self.wf)
        """
        if not self.recording or self.wf is None:
            return

        # Pull pending callback blocks and clear queue quickly
        blocks, self.recording = self.recording, []
        x = np.concatenate(blocks, axis=0).astype(np.float32)
        if x.size == 0:
            return

        # Stereo → mono
        if x.ndim == 2 and x.shape[1] == 2:
            x = x.mean(axis=1)

        fs = int(self.sampling_rate)

        # --- initialize frame & xfade lengths once (40 ms frames, 5 ms crossfade)
        if self._frame_len is None:
            self._frame_len = max(160, int(0.040 * fs))   # ≥160 samples safeguard
        if self._xfade_len is None:
            self._xfade_len = max(32, min(self._frame_len // 4, int(0.005 * fs)))

        frame_len = self._frame_len
        xfade = self._xfade_len
        group_frames = int(self._frames_per_group)

        # Accumulate with leftover from previous call
        buf = np.concatenate([self._scramble_buf, x])
        n_full_frames = buf.size // frame_len
        n_groups = n_full_frames // group_frames
        n_use_frames = n_groups * group_frames
        n_use_samples = n_use_frames * frame_len

        if n_use_frames == 0:
            # Not enough for one full group: keep as leftover for next call
            self._scramble_buf = buf
            return

        # Reshape into groups x frames x samples
        frames = buf[:n_use_samples].reshape(n_groups, group_frames, frame_len)

        # Prepare fades
        fade_in = np.linspace(0.0, 1.0, xfade, dtype=np.float32)
        fade_out = fade_in[::-1]

        out_chunks = []
        prev_tail = None

        # Process each group: permute frames and crossfade joins
        for g in range(n_groups):
            order = np.random.permutation(group_frames)
            for idx, fidx in enumerate(order):
                frm = frames[g, fidx, :]

                if prev_tail is None:
                    # first frame: just store
                    out_chunks.append(frm.astype(np.float32, copy=False))
                    prev_tail = out_chunks[-1]
                else:
                    # crossfade boundary: last xfade of previous with first xfade of current
                    a = prev_tail[-xfade:] * fade_out
                    b = frm[:xfade] * fade_in
                    xfd = a + b

                    # assemble: (prev without its last xfade) + xfade + (rest of current)
                    out_chunks[-1] = np.concatenate([out_chunks[-1][:-xfade], xfd], axis=0)
                    out_chunks.append(frm[xfade:].astype(np.float32, copy=False))
                    prev_tail = out_chunks[-1]

        y = np.concatenate(out_chunks, axis=0)

        # Keep leftover (anything after the processed region)
        self._scramble_buf = buf[n_use_samples:]

        # --- Output rate (skip resample if already matching)
        target_rate = int(self.final_rate)
        if target_rate != fs:
            from fractions import Fraction
            frac = Fraction(target_rate, fs).limit_denominator(1000)
            y = sps.resample_poly(y, frac.numerator, frac.denominator).astype(np.float32)

        # --- Smoothed gain to avoid level jumps (no per-block hard normalize)
        block_peak = float(np.max(np.abs(y)) if y.size else 0.0) or 1e-6
        if self._peak_slow is None:
            self._peak_slow = block_peak

        # quick attack, slower release
        alpha_up, alpha_dn = 0.35, 0.05
        a = alpha_up if block_peak > self._peak_slow else alpha_dn
        self._peak_slow = a * block_peak + (1 - a) * self._peak_slow

        target_lin = 10.0 ** (-10.0 / 20.0)  # ≈ -1 dBFS
        desired_gain = target_lin / max(self._peak_slow, 1e-6)
        self._gain = 0.2 * desired_gain + 0.8 * self._gain

        y = np.clip(y * self._gain, -1.0, 1.0)

        # Write as int16
        pcm16 = np.int16(y * 32767)
        try:
            self.wf.writeframes(pcm16.tobytes())
        except Exception as e:
            print(f"Audio write error: {e}")






