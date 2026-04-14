import argparse
import csv
import math
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Iterable, List, Optional, Sequence, Tuple


DEFAULT_MIN_ZERO_SECONDS = 2.0
DEFAULT_FPS = 10.0
TIMESTAMP_FORMAT = "%Y-%m-%d$%H-%M-%S-%f"
OUTPUT_HEADERS = [
    "new_frame_idx",
    "original_frame_number",
    "timestamp",
    "face_count",
    "kept",
]


def compute_keep_segments(counts: Sequence[int], fps: float, min_zero_seconds: float) -> List[Tuple[int, int]]:
    """Mirror the filtering logic from video_filter.py."""
    n = len(counts)
    if n == 0:
        return []

    min_zero_frames = int(math.ceil(min_zero_seconds * fps))
    cut_segments: List[Tuple[int, int]] = []
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

    keep_segments: List[Tuple[int, int]] = []
    cursor = 0
    for start, end in cut_segments:
        if cursor <= start - 1:
            keep_segments.append((cursor, start - 1))
        cursor = end + 1

    if cursor <= n - 1:
        keep_segments.append((cursor, n - 1))

    return keep_segments


def normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def parse_timestamp(value: str) -> Optional[datetime]:
    value = value.strip()
    if not value:
        return None

    try:
        return datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        return None


def infer_fps(rows: Sequence[dict]) -> float:
    timestamps = []
    for row in rows:
        parsed = parse_timestamp(row["timestamp"])
        if parsed is not None:
            timestamps.append(parsed)

    if len(timestamps) < 2:
        return DEFAULT_FPS

    deltas = []
    for prev, cur in zip(timestamps, timestamps[1:]):
        delta = (cur - prev).total_seconds()
        if delta > 0:
            deltas.append(delta)

    if not deltas:
        return DEFAULT_FPS

    median_delta = median(deltas)
    if median_delta <= 0:
        return DEFAULT_FPS

    return 1.0 / median_delta


def read_timestamp_file(path: Path) -> List[dict]:
    with path.open("r", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        if reader.fieldnames is None:
            raise ValueError("missing header")

        normalized = {normalize_header(name): name for name in reader.fieldnames}
        frame_key = normalized.get("original_frame_number") or normalized.get("frame_number")
        timestamp_key = normalized.get("timestamp")
        face_count_key = normalized.get("face_count")

        if frame_key is None or timestamp_key is None or face_count_key is None:
            raise ValueError(
                "expected columns containing frame_number/original_frame_number, timestamp, and face_count"
            )

        rows = []
        for row in reader:
            original_frame = (row.get(frame_key) or "").strip()
            timestamp = (row.get(timestamp_key) or "").strip()
            face_count_raw = (row.get(face_count_key) or "").strip()

            if not original_frame and not timestamp and not face_count_raw:
                continue

            if not original_frame:
                raise ValueError("encountered row without frame number")
            if not timestamp:
                raise ValueError("encountered row without timestamp")

            try:
                face_count = int(face_count_raw)
            except ValueError as exc:
                raise ValueError(f"invalid face_count '{face_count_raw}'") from exc

            rows.append(
                {
                    "original_frame_number": original_frame,
                    "timestamp": timestamp,
                    "face_count": face_count,
                }
            )

    return rows


def build_updated_rows(rows: Sequence[dict], fps: float, min_zero_seconds: float) -> List[dict]:
    counts = [row["face_count"] for row in rows]
    keep_segments = compute_keep_segments(counts, fps, min_zero_seconds)

    kept_mask = [False] * len(rows)
    for start, end in keep_segments:
        for idx in range(start, end + 1):
            kept_mask[idx] = True

    next_frame_idx = 0
    output_rows = []
    for idx, row in enumerate(rows):
        kept = kept_mask[idx]
        new_frame_idx = str(next_frame_idx) if kept else ""
        if kept:
            next_frame_idx += 1

        output_rows.append(
            {
                "new_frame_idx": new_frame_idx,
                "original_frame_number": row["original_frame_number"],
                "timestamp": row["timestamp"],
                "face_count": str(row["face_count"]),
                "kept": "1" if kept else "0",
            }
        )

    return output_rows


def write_timestamp_file(path: Path, rows: Sequence[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def find_txt_files(target: Path) -> List[Path]:
    if target.is_file():
        return [target]

    if not target.exists():
        raise FileNotFoundError(f"path does not exist: {target}")

    if target.name == "hires":
        return sorted(path for path in target.glob("*.txt") if path.is_file())

    hires_files = sorted(path for path in target.glob("*/hires/*.txt") if path.is_file())
    if hires_files:
        return hires_files

    return sorted(path for path in target.rglob("*.txt") if path.is_file())


def process_file(path: Path, min_zero_seconds: float, dry_run: bool) -> Tuple[int, int, float]:
    rows = read_timestamp_file(path)
    fps = infer_fps(rows)
    updated_rows = build_updated_rows(rows, fps, min_zero_seconds)
    kept_count = sum(1 for row in updated_rows if row["kept"] == "1")

    if not dry_run:
        write_timestamp_file(path, updated_rows)

    return kept_count, len(updated_rows), fps


def process_files(paths: Iterable[Path], min_zero_seconds: float, dry_run: bool) -> int:
    total_files = 0
    total_rows = 0
    total_kept = 0
    failures = 0

    for path in paths:
        total_files += 1
        try:
            kept_count, row_count, fps = process_file(path, min_zero_seconds, dry_run)
            total_rows += row_count
            total_kept += kept_count
            kept_ratio = (100.0 * kept_count / row_count) if row_count else 0.0
            action = "would update" if dry_run else "updated"
            print(f"{action}: {path} | fps~{fps:.3f} | kept {kept_count}/{row_count} ({kept_ratio:.1f}%)")
        except Exception as exc:
            failures += 1
            print(f"failed: {path} | {exc}")

    if total_files == 0:
        print("No txt files found.")
        return 0

    summary_action = "would update" if dry_run else "updated"
    total_ratio = (100.0 * total_kept / total_rows) if total_rows else 0.0
    print(
        f"{summary_action} {total_files - failures}/{total_files} files | "
        f"kept {total_kept}/{total_rows} frames ({total_ratio:.1f}%)"
    )

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rewrite hires timestamp txt files to include keep/drop decisions that mirror video_filter.py."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=Path(__file__).resolve().parent / "data",
        type=Path,
        help="File or directory to process. Defaults to the repo data folder.",
    )
    parser.add_argument(
        "--min-zero-seconds",
        type=float,
        default=DEFAULT_MIN_ZERO_SECONDS,
        help="Minimum consecutive zero-face duration removed by the filter.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect and report changes without rewriting files.",
    )
    args = parser.parse_args()

    files = find_txt_files(args.path)
    return process_files(files, args.min_zero_seconds, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
