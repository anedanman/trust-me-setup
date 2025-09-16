import argparse
import csv
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple, Optional

import cv2


def detect_face_count(frame, cascade, resize_width=640, scale_factor=1.1, min_neighbors=5, min_size=(30, 30)) -> int:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if w > resize_width:
        scale = resize_width / float(w)
        gray_small = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
    else:
        gray_small = gray
        scale = 1.0

    faces = cascade.detectMultiScale(gray_small, scaleFactor=scale_factor, minNeighbors=min_neighbors, minSize=min_size)
    return len(faces)


def compute_keep_segments(counts: List[int], fps: float, min_zero_seconds: float) -> List[Tuple[int, int]]:
    n = len(counts)
    if n == 0:
        return []
    min_zero_frames = int(math.ceil(min_zero_seconds * fps))

    # Find zero runs that are long enough to cut
    cut_segments = []
    i = 0
    while i < n:
        if counts[i] == 0:
            start = i
            while i < n and counts[i] == 0:
                i += 1
            end = i - 1
            if (end - start + 1) >= min_zero_frames:
                cut_segments.append((start, end))
        else:
            i += 1

    # Complement => keep segments
    keep_segments = []
    cursor = 0
    for cs, ce in cut_segments:
        if cursor <= cs - 1:
            keep_segments.append((cursor, cs - 1))
        cursor = ce + 1
    if cursor <= n - 1:
        keep_segments.append((cursor, n - 1))

    # Merge adjacent keep segments that are separated by short zero gaps (we ignored those gaps already)
    # Not strictly necessary since we already ignored short zeros.
    return keep_segments


def check_if_processed(timestamps_path: str) -> bool:
    """Check if the timestamp file already contains face counts for frames.

    Considered processed if:
    - header contains 'face_count', and
    - at least one data row has a third column (frame,timestamp,face_count)
    """
    if not os.path.exists(timestamps_path):
        return False

    try:
        with open(timestamps_path, "r") as f:
            header = f.readline().strip()
            if "face_count" not in header:
                return False
            # check at least one data line has 3 columns
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) >= 3:
                    return True
            return False
    except Exception:
        return False


def write_counts_to_timestamps(counts: List[int], fps: float, timestamps_path: str):
    """Add face counts to existing timestamp file."""
    if not os.path.exists(timestamps_path):
        print(f"Warning: Timestamp file not found: {timestamps_path}")
        return
    
    # Read existing timestamps
    with open(timestamps_path, "r") as f:
        lines = f.readlines()
    
    if not lines:
        print(f"Warning: Empty timestamp file: {timestamps_path}")
        return
    
    # Check if face_count column already exists
    header = lines[0].strip()
    if "face_count" in header:
        print(f"Face counts already exist in {timestamps_path}, updating...")
        # Remove existing face_count column and data
        lines[0] = header.split(",face_count")[0] + "\n"
        for i in range(1, len(lines)):
            if "," in lines[i]:
                parts = lines[i].strip().split(",")
                if len(parts) >= 3:  # frame, timestamp, face_count
                    lines[i] = ",".join(parts[:2]) + "\n"
    
    # Add face_count to header
    lines[0] = lines[0].strip() + ",face_count\n"
    
    # Add face counts to data lines
    for i in range(1, len(lines)):
        line = lines[i].strip()
        if line and "," in line:
            frame_idx = i - 1
            if frame_idx < len(counts):
                lines[i] = line + f",{counts[frame_idx]}\n"
            else:
                lines[i] = line + ",0\n"  # Default to 0 if no count available
    
    # Write updated file
    with open(timestamps_path, "w") as f:
        f.writelines(lines)


def write_counts_csv(counts: List[int], fps: float, csv_path: str):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "time_sec", "face_count"])
        for i, c in enumerate(counts):
            t = i / fps
            writer.writerow([i, f"{t:.3f}", c])


def extract_date_from_filename(filename: str) -> Optional[str]:
    """Extract date from filename in format YYYY-MM-DD."""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    return match.group(1) if match else None


def analyze_video_counts(input_path: str, resize_width: int) -> Tuple[List[int], float, int, int]:
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade.empty():
        raise RuntimeError("Failed to load Haar cascade. Ensure opencv-data is available.")

    counts = []
    idx = 0
    start_time = time.time()
    
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        c = detect_face_count(frame, cascade, resize_width=resize_width)
        counts.append(c)

        # Show processing speed every 100 frames
        if idx % 100 == 0:
            elapsed = time.time() - start_time
            if elapsed > 0:
                processing_fps = (idx + 1) / elapsed
                sys.stderr.write(f"\rAnalyzed {idx} frames (processing at {processing_fps:.1f} FPS) ...")
            else:
                sys.stderr.write(f"\rAnalyzed {idx} frames ...")
            sys.stderr.flush()
        idx += 1

    cap.release()
    total_time = time.time() - start_time
    avg_processing_fps = len(counts) / total_time if total_time > 0 else 0
    sys.stderr.write(f"\rAnalyzed {len(counts)} frames in {total_time:.1f}s (avg {avg_processing_fps:.1f} FPS). Done.\n")
    return counts, fps, width, height


def write_output_opencv(input_path: str, output_path: str, keep_segments: List[Tuple[int, int]], fps: float, width: int, height: int):
    if not keep_segments:
        print("No segments to keep. Skipping video writing.")
        return

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {input_path}")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        cap.release()
        raise RuntimeError(f"Failed to open VideoWriter: {output_path}")

    seg_idx = 0
    start, end = keep_segments[seg_idx]
    frame_idx = 0
    kept = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Advance to the segment containing this frame
        while seg_idx < len(keep_segments) and frame_idx > end:
            seg_idx += 1
            if seg_idx < len(keep_segments):
                start, end = keep_segments[seg_idx]

        if seg_idx < len(keep_segments) and start <= frame_idx <= end:
            out.write(frame)
            kept += 1

        if frame_idx % 200 == 0:
            sys.stderr.write(f"\rWrote {kept} frames ...")
            sys.stderr.flush()

        frame_idx += 1

    cap.release()
    out.release()
    sys.stderr.write(f"\rWrote {kept} frames. Done.\n")


def write_output_ffmpeg(input_path: str, output_path: str, keep_segments: List[Tuple[int, int]], fps: float):
    if not keep_segments:
        print("No segments to keep. Skipping video writing.")
        return

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not found in PATH. Install ffmpeg or use --method opencv.")

    tempdir = tempfile.mkdtemp(prefix="face_segments_")
    try:
        parts = []
        for i, (s, e) in enumerate(keep_segments):
            start_t = s / fps
            end_t = (e + 1) / fps  # end is inclusive; ffmpeg -to is exclusive
            seg_path = os.path.join(tempdir, f"part_{i:04d}.mp4")

            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{start_t:.6f}",
                "-to", f"{end_t:.6f}",
                "-i", input_path,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                "-c:a", "copy",
                "-movflags", "+faststart",
                seg_path,
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            parts.append(seg_path)

        concat_file = os.path.join(tempdir, "concat.txt")
        with open(concat_file, "w") as f:
            for p in parts:
                # concat demuxer expects escaped paths or safe=0
                f.write(f"file '{p}'\n")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path,
        ]
        subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def process_folder(input_folder: str, output_folder: Optional[str], min_zero_seconds: float, 
                  resize_width: int, method: str, target_date: Optional[str] = None, 
                  in_place: bool = False, force: bool = False):
    """Process all video files in a folder."""
    input_path = Path(input_folder)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")
    
    # Find all video files
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
    video_files = [f for f in input_path.iterdir() 
                   if f.is_file() and f.suffix.lower() in video_extensions]
    
    # Filter by date if specified
    if target_date:
        video_files = [f for f in video_files if extract_date_from_filename(f.name) == target_date]
        print(f"Filtering for date: {target_date}")
    
    if not video_files:
        date_msg = f" for date {target_date}" if target_date else ""
        print(f"No video files found in {input_folder}{date_msg}")
        return
    
    print(f"Found {len(video_files)} video files to process")
    
    # Create output directory if not processing in place
    if not in_place and output_folder:
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] Processing: {video_file.name}")
        
        # Find corresponding timestamp file generically.
        # Rule: timestamps live in the same folder and are named
        #   <user>_timestamps_<suffix>.txt
        # where <suffix> matches the tail of the video name after the last underscore
        # or, when chunked: replace _chunk<d>_ with _timestamps_.
        import re
        base_name = video_file.stem
        suffix = base_name.split("_")[-1]

        # Try pattern based on replacing chunk with timestamps
        candidate1 = re.sub(r"_chunk\d+_", "_timestamps_", video_file.name)
        candidate1 = os.path.splitext(candidate1)[0] + ".txt"
        tp1 = video_file.parent / candidate1

        # Fallback: any file matching *_timestamps_<suffix>.txt
        pattern = f"*_timestamps_{suffix}.txt"
        matches = list(video_file.parent.glob(pattern))

        if tp1.exists():
            timestamp_path = tp1
        elif matches:
            timestamp_path = matches[0]
        else:
            # Last resort: search any *_timestamps_*.txt with same date token if present
            date_token = extract_date_from_filename(video_file.name)
            if date_token:
                matches = list(video_file.parent.glob(f"*_timestamps_{date_token}*.txt"))
            timestamp_path = matches[0] if matches else video_file.parent / (base_name + "_timestamps.txt")
        
        # Check if already processed
        if not force and check_if_processed(str(timestamp_path)):
            print(f"  ✓ Already processed (face counts found in timestamp file)")
            continue
        
        try:
            # Analyze video
            counts, fps, width, height = analyze_video_counts(str(video_file), resize_width)
            
            # Write face counts to timestamp file
            write_counts_to_timestamps(counts, fps, str(timestamp_path))
            
            # Compute filtering segments
            keep_segments = compute_keep_segments(counts, fps, min_zero_seconds)
            total_frames_kept = sum((e - s + 1) for s, e in keep_segments)
            total_frames = len(counts)
            
            print(f"  Keep segments: {len(keep_segments)} | frames kept: {total_frames_kept}/{total_frames} ({100.0*total_frames_kept/total_frames:.1f}%)")
            
            # Determine output path
            if in_place:
                output_video_path = str(video_file)
            else:
                if output_folder:
                    output_path = Path(output_folder)
                    output_video_path = str(output_path / f"{video_file.stem}_filtered{video_file.suffix}")
                else:
                    output_video_path = str(video_file.parent / f"{video_file.stem}_filtered{video_file.suffix}")
            
            # Write filtered video
            if method == "ffmpeg":
                write_output_ffmpeg(str(video_file), output_video_path, keep_segments, fps)
            else:
                write_output_opencv(str(video_file), output_video_path, keep_segments, fps, width, height)
                
            if in_place:
                print(f"  ✓ Overwritten: {video_file.name}")
            else:
                print(f"  ✓ Completed: {Path(output_video_path).name}")
            
        except Exception as e:
            print(f"  ✗ Error processing {video_file.name}: {e}")
            continue


def main():
    parser = argparse.ArgumentParser(description="Filter out zero-face segments from video(s) and save per-frame face counts to timestamp files.")
    
    # New batch processing arguments
    parser.add_argument("--folder", "-f", help="Process all videos in this folder (alternative to --input)")
    parser.add_argument("--output-folder", help="Output folder for batch processing (ignored if --in-place is used)")
    parser.add_argument("--date", help="Process only videos from specific date (YYYY-MM-DD format)")
    parser.add_argument("--in-place", action="store_true", help="Overwrite original files instead of creating new ones")
    parser.add_argument("--force", action="store_true", help="Process even if already processed (overwrite existing face counts)")
    
    # Original single file arguments
    parser.add_argument("--input", "-i", help="Path to input video (for single file processing)")
    parser.add_argument("--output", "-o", help="Path to output filtered video (mp4, for single file processing)")
    parser.add_argument("--counts", "-c", help="Path to CSV file to save per-frame counts (for single file processing)")
    
    # Common arguments
    parser.add_argument("--min-zero-seconds", type=float, default=2.0, help="Minimum consecutive zero-face duration to remove (seconds)")
    parser.add_argument("--resize-width", type=int, default=640, help="Resize width for detection (lower = faster)")
    parser.add_argument("--method", choices=["ffmpeg", "opencv"], default="ffmpeg", help="How to write output video (ffmpeg preserves audio)")
    
    args = parser.parse_args()
    
    # Determine processing mode
    if args.folder:
        # Batch processing mode
        input_folder = args.folder
        output_folder = args.output_folder if not args.in_place else None
        
        if not args.in_place and not output_folder:
            # Default: add "_filtered" to the input folder name
            input_path = Path(input_folder)
            output_folder = str(input_path.parent / (input_path.name + "_filtered"))
        
        process_folder(input_folder, output_folder, args.min_zero_seconds, args.resize_width, 
                      args.method, args.date, args.in_place, args.force)
        
    elif args.input and args.output and args.counts:
        # Single file processing mode (original functionality)
        counts, fps, width, height = analyze_video_counts(args.input, args.resize_width)
        write_counts_csv(counts, fps, args.counts)

        keep_segments = compute_keep_segments(counts, fps, args.min_zero_seconds)
        total_frames_kept = sum((e - s + 1) for s, e in keep_segments)
        total_frames = len(counts)
        print(f"Keep segments: {len(keep_segments)} | frames kept: {total_frames_kept}/{total_frames} ({100.0*total_frames_kept/total_frames:.1f}%)")

        if args.method == "ffmpeg":
            write_output_ffmpeg(args.input, args.output, keep_segments, fps)
        else:
            write_output_opencv(args.input, args.output, keep_segments, fps, width, height)
            
    else:
        # Default behavior: process the default folder with in-place modification
        # Determine username from tmp/current_username if available
        repo_root = Path(__file__).resolve().parent
        username_file = repo_root / "tmp" / "current_username"
        username = None
        if username_file.exists():
            try:
                username = username_file.read_text().strip()
            except Exception:
                username = None
        default_folder = str(repo_root / "data" / (username or "") / "hires") if username else str(repo_root / "data")

        # If username not known, try to find any user/hires dir under data
        if username is None:
            candidates = list((repo_root / "data").glob("*/hires"))
            if candidates:
                default_folder = str(candidates[0])

        if os.path.exists(default_folder):
            print(f"No arguments provided. Processing default folder: {default_folder}")
            print("Using --in-place mode (original files will be overwritten)")
            process_folder(default_folder, None, args.min_zero_seconds, args.resize_width, 
                          args.method, args.date, in_place=True, force=args.force)
        else:
            parser.print_help()
            print(f"\nError: Default folder '{default_folder}' not found.")
            print("Please provide either:")
            print("  --folder <path> for batch processing, or")
            print("  --input, --output, and --counts for single file processing")
            sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()