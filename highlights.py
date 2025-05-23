import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from typing import Union, List, Tuple
from pathlib import Path
import os
from datetime import datetime
import subprocess
from moviepy.editor import VideoFileClip


def load_eyetracking_data(filepath: Union[str, Path]) -> pd.DataFrame:
    """
    Load eye tracking data from TSV file into pandas DataFrame.
    
    Args:
        filepath: Path to the TSV file
        
    Returns:
        pandas DataFrame with processed eye tracking data
    """
    try:
        # Read the TSV file, skipping the metadata header
        df = pd.read_csv(filepath, 
                        sep='\t',
                        skiprows=7)
        
        # Replace invalid values (-1) with NaN for proper handling
        numeric_columns = ['GazePointXLeft', 'GazePointYLeft', 'GazePointXRight', 'GazePointYRight',
                          'GazePointX', 'GazePointY', 'PupilSizeLeft', 'PupilSizeRight',
                          'DistanceLeft', 'DistanceRight', 'AverageDistance']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].replace(-1, np.nan)
                df[col] = df[col].replace(0, np.nan)

        
        # Fill NaN values with median for more robust handling of outliers
        for col in numeric_columns:
            if col in df.columns:
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
        
        # Ensure TimeStamp is numeric
        df['TimeStamp'] = pd.to_numeric(df['TimeStamp'], errors='coerce')
        
        return df
        
    except Exception as e:
        raise Exception(f"Error loading eye tracking data: {str(e)}")
    

def drop_initial_timewindow(df: pd.DataFrame, seconds: float) -> pd.DataFrame:
    """
    Drop initial time window from DataFrame.
    
    Args:
        df: DataFrame containing eye tracking data
        seconds: Number of seconds of data to remove from start
        
    Returns:
        DataFrame with initial time window removed
    """

    cutoff_time = seconds * 1000 # Convert to milliseconds
    
    # Filter data to keep everything after cutoff
    df_filtered = df[df['TimeStamp'] > cutoff_time]
    df_filtered['TimeStamp'] -= cutoff_time  # Adjust timestamps
    return df_filtered


def calculate_interest_features(
    df: pd.DataFrame,
    video_fps: float = 9.1,
    savgol_window: int = 15,
    savgol_poly: int = 3,
    smoothing_window_sec: float = 10.0,
) -> pd.DataFrame:
    """
    Calculate features indicating potential moments of interest with averaged subsampling.
    
    Args:
        df: DataFrame with eye tracking data
        video_fps: Frame rate of video data (default 9.1 fps)
        savgol_window: Window size for Savitzky-Golay filter
        savgol_poly: Polynomial order for Savitzky-Golay filter
        smoothing_window_sec: Short-term smoothing window in seconds
    """
    # Calculate time differences and basic features
    df['dt'] = df['TimeStamp'].diff() / 1000.0
    
    # Calculate gaze velocity (eye movement speed)
    df['gaze_dx'] = df['GazePointX'].diff()
    df['gaze_dy'] = df['GazePointY'].diff()
    df['gaze_velocity'] = np.sqrt(df['gaze_dx']**2 + df['gaze_dy']**2) / df['dt']
    df['gaze_velocity'] = df['gaze_velocity'].fillna(0)
    
    # Calculate gaze acceleration
    df['gaze_acceleration'] = df['gaze_velocity'].diff() / df['dt']
    df['gaze_acceleration'] = df['gaze_acceleration'].fillna(0)
    
    # Calculate pupil size changes
    df['pupil_change_left'] = df['PupilSizeLeft'].diff().abs()
    df['pupil_change_right'] = df['PupilSizeRight'].diff().abs()
    df['pupil_change_avg'] = (df['pupil_change_left'] + df['pupil_change_right']) / 2
    df['pupil_change_avg'] = df['pupil_change_avg'].fillna(0)
    
    # Calculate distance changes (head movement indicator)
    df['distance_change'] = df['AverageDistance'].diff().abs()
    df['distance_change'] = df['distance_change'].fillna(0)
    
    # Apply Savitzky-Golay smoothing to reduce noise
    if len(df) > savgol_window:
        df['gaze_velocity_smooth'] = savgol_filter(df['gaze_velocity'], 
                                                  min(savgol_window, len(df)), 
                                                  savgol_poly)
        df['pupil_change_smooth'] = savgol_filter(df['pupil_change_avg'], 
                                                 min(savgol_window, len(df)), 
                                                 savgol_poly)
    else:
        df['gaze_velocity_smooth'] = df['gaze_velocity']
        df['pupil_change_smooth'] = df['pupil_change_avg']
    
    # Subsample to video frame rate
    sampling_interval_ms = 1000.0 / video_fps
    subsampled_timestamps = np.arange(df['TimeStamp'].min(), 
                                    df['TimeStamp'].max(), 
                                    sampling_interval_ms)
    
    df_subsampled = pd.DataFrame({'TimeStamp': subsampled_timestamps})
    
    # Interpolate features to subsampled timestamps
    features_to_interpolate = ['gaze_velocity_smooth', 'pupil_change_smooth', 
                              'gaze_acceleration', 'distance_change']
    
    for feature in features_to_interpolate:
        df_subsampled[feature] = np.interp(subsampled_timestamps, 
                                          df['TimeStamp'], 
                                          df[feature])
    
    # Normalize features to 0-1 range for combination
    for feature in features_to_interpolate:
        feature_values = df_subsampled[feature]
        if feature_values.std() > 0:
            df_subsampled[f'{feature}_norm'] = (feature_values - feature_values.min()) / (feature_values.max() - feature_values.min())
        else:
            df_subsampled[f'{feature}_norm'] = 0
    
    # Combine features into interest score with weights
    # Higher weights for more important indicators of engagement
    weights = {
        'gaze_velocity_smooth_norm': 0.4,  # Eye movement is primary indicator
        'gaze_acceleration_norm': 0.2,     # Sudden changes in movement
        'pupil_change_smooth_norm': 0.3,   # Pupil changes indicate cognitive load
        'distance_change_norm': 0.1        # Head movement (less important)
    }
    
    df_subsampled['interest_score'] = sum(
        weights[feature] * df_subsampled[feature] 
        for feature in weights.keys()
    )
    
    # Apply short-term smoothing to interest score
    smoothing_window_samples = int(smoothing_window_sec * video_fps)
    if smoothing_window_samples > 1 and len(df_subsampled) > smoothing_window_samples:
        weights_centered = create_centered_weights(smoothing_window_samples)
        df_subsampled['interest_score'] = np.convolve(
            df_subsampled['interest_score'], 
            weights_centered, 
            mode='same'
        )
    
    return df_subsampled


def create_centered_weights(window):
    """Helper function to create weights with higher values in center"""
    # Create triangular weights
    center = window // 2
    weights = np.zeros(window)
    for i in range(window):
        weights[i] = 1 - abs(i - center) / center
    return weights / weights.sum()  # Normalize to sum to 1


def video2eye(df, start_date, end_date, video_path):
    # assuming the dates are strings and format is "YYYY-MM-DD$HH-MM-SS-XXXXXX"
    # the videos are named as "USERNAME_chunk{i}_{date}.mp4 in dir video_path"
    start_dt = datetime.strptime(start_date, '%Y-%m-%d$%H-%M-%S-%f')
    end_dt   = datetime.strptime(end_date,   '%Y-%m-%d$%H-%M-%S-%f')
    matched = []
    for fname in os.listdir(video_path):
        if not fname.lower().endswith('.mp4'):
            continue
        parts = fname.split('_')
        date_part = parts[-1].rsplit('.', 1)[0]
        try:
            file_dt = datetime.strptime(date_part, '%Y-%m-%d$%H-%M-%S-%f')
        except ValueError:
            continue
        if start_dt <= file_dt <= end_dt:
            matched.append(os.path.join(video_path, fname))
    
    # now load corresponding timestamp files and extract start/end times
    video_times = []
    for video_file in matched:
        fname = os.path.basename(video_file)
        parts = fname.split('_')

        # replace chunkX with 'timestamps'
        parts[-2] = 'timestamps'
        ts_fname = '_'.join(parts).rsplit('.', 1)[0] + '.txt'
        ts_path = os.path.join(video_path, ts_fname)

        times = []
        with open(ts_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    _, tm = line.split(',', 1)
                except ValueError:
                    continue
                times.append(tm)
        if times:
            video_times.append((video_file, times[1], times[-1]))
    return video_times


def find_top_n_peaks(df, n, delta):
    """
    Find top n peaks by highest interest score values, ensuring minimum time distance between all peaks.
    
    Args:
        df: DataFrame containing 'interest_score', and 'timestamp' columns
        n: Number of peaks to find
        delta: Minimum seconds between peaks (converted to ms internally)
    """
    delta_ms = delta * 1000  # Convert delta from seconds to milliseconds
    
    # Get indices sorted by interest_score in descending order
    sorted_indices = df['interest_score'].argsort()[::-1]
    print("Interest scores:", df['interest_score'].values)
    print("Sorted indices:", sorted_indices)
    # Create initial peaks list with metadata
    peaks_info = []
    for idx in sorted_indices:
        timestamp = df.loc[idx, 'TimeStamp']
        score = df.loc[idx, 'interest_score']
        video_file = df.loc[idx, 'video_file']
        if pd.isna(video_file):  # Skip frames without video
            continue
        peaks_info.append((idx, timestamp, score, video_file))
    
    # Filter peaks ensuring minimum time distance between ALL pairs
    selected_peaks = []
    for peak in peaks_info:
        # Check if this peak is far enough from ALL already selected peaks
        is_valid = True
        for selected in selected_peaks:
            if abs(peak[1] - selected[1]) < delta_ms:
                is_valid = False
                break
        
        if is_valid:
            selected_peaks.append(peak)
            if len(selected_peaks) == n:
                break
    
    return selected_peaks

def extract_highlights(df, peaks, highlight_dir, segment_duration=60):
    """
    Extract video segments based on identified peaks of most interest and save them to highlight_dir.
    
    Args:
        df: DataFrame containing 'interest_score', and 'timestamp' columns
        peaks: List of tuples with peak timestamps and corresponding video files
        highlight_dir: Directory to save extracted video segments
        segment_duration: Duration of each highlight segment in seconds
    """
    from pathlib import Path
    Path(highlight_dir).mkdir(parents=True, exist_ok=True)
    
    for i, (idx, timestamp, score, video_file) in enumerate(peaks):
        if pd.isna(video_file):
            continue
            
        # Calculate start time relative to video start
        video_rows = df[df['video_file'] == video_file]
        if len(video_rows) == 0:
            continue
            
        video_start_ts = video_rows['TimeStamp'].min()
        relative_time = (timestamp - video_start_ts) / 1000.0  # Convert to seconds
        
        # Calculate segment bounds
        start_time = max(0, relative_time - segment_duration/2)
        
        # Output filename
        video_basename = os.path.splitext(os.path.basename(video_file))[0]
        output_file = os.path.join(highlight_dir, f"highlight_{i+1}_{video_basename}_t{relative_time:.1f}s_score{score:.3f}.mp4")
        
        try:
            # Load video with moviepy
            video = VideoFileClip(video_file)
            end_time = min(start_time + segment_duration, video.duration)
            
            # Create clip
            clip = video.subclip(start_time, end_time)
            
            # Write with proper encoding
            clip.write_videofile(
                output_file,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # Clean up
            clip.close()
            video.close()
            
            print(f"Extracted highlight {i+1}: {output_file}")
            
        except Exception as e:
            print(f"Failed to extract highlight {i+1}: {e}")

def assign_video_to_frames(
    df: pd.DataFrame,
    video_times: List[Tuple[str, str, str]],
    start_date: str
) -> pd.DataFrame:
    """
    Add a column 'video_file' mapping each df TimeStamp (ms) to the corresponding video.
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d$%H-%M-%S-%f')
    ranges = []
    for video_file, start_ts, end_ts in video_times:
        s_dt = datetime.strptime(start_ts, '%Y-%m-%d$%H-%M-%S-%f')
        e_dt = datetime.strptime(end_ts, '%Y-%m-%d$%H-%M-%S-%f')
        s_off = (s_dt - start_dt).total_seconds() * 1000
        e_off = (e_dt - start_dt).total_seconds() * 1000
        ranges.append((video_file, s_off, e_off))

    def lookup(ts: float):
        for vf, s, e in ranges:
            if s <= ts <= e:
                return vf
        return None

    df['video_file'] = df['TimeStamp'].apply(lookup)
    return df


def merge_eyetracking_files(eye_dir: str, user: str, date: str) -> pd.DataFrame:
    """
    Find and merge all eye tracking files for a given date, adjusting timestamps.
    
    Args:
        eye_dir: Directory containing eye tracking files
        user: Username to filter files
        date: Date string in format YYYY-MM-DD
        
    Returns:
        Merged DataFrame with adjusted timestamps
    """
    import glob
    
    # Find all TSV files for the specified date and user
    pattern = os.path.join(eye_dir, f"{user}_{date}*.tsv")
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No eye tracking files found for {user} on {date} in {eye_dir}")
    
    # Sort files by filename to ensure chronological order
    files.sort()
    print(f"Found {len(files)} eye tracking files to merge:")
    for f in files:
        print(f"  {os.path.basename(f)}")
    
    merged_dfs = []
    cumulative_time_offset = 0
    
    for i, filepath in enumerate(files):
        print(f"Processing file {i+1}/{len(files)}: {os.path.basename(filepath)}")
        
        # Load the file
        df = load_eyetracking_data(filepath)
        
        if len(df) == 0:
            print(f"  Skipping empty file: {filepath}")
            continue
        
        # Extract start and end times from filename for proper offset calculation
        filename = os.path.basename(filepath)
        parts = filename.split('_')
        file_start_str = parts[-2]  # Start timestamp from filename
        file_end_str = parts[-1].split('.')[0]  # End timestamp from filename
        
        
        file_start_dt = datetime.strptime(file_start_str, '%Y-%m-%d$%H-%M-%S-%f')
        file_end_dt = datetime.strptime(file_end_str, '%Y-%m-%d$%H-%M-%S-%f')
        
        
        # Adjust timestamps based on actual file timing
        if i == 0:
            # First file: normalize to start from 0
            min_timestamp = df['TimeStamp'].min()
            df['TimeStamp'] = df['TimeStamp'] - min_timestamp
            cumulative_time_offset = df['TimeStamp'].max()
            last_file_end_dt = file_end_dt
        else:
            # Calculate real time gap between end of last file and start of current file
            time_gap_seconds = (file_start_dt - last_file_end_dt).total_seconds()
            time_gap_ms = time_gap_seconds * 1000
            
            print(f"  Time gap from previous file: {time_gap_seconds:.1f} seconds")
            
            # Adjust timestamps: normalize current file and add cumulative offset plus real gap
            min_timestamp = df['TimeStamp'].min()
            df['TimeStamp'] = df['TimeStamp'] - min_timestamp + cumulative_time_offset + time_gap_ms
            
            # Update cumulative offset to end of current file
            cumulative_time_offset = df['TimeStamp'].max()
            last_file_end_dt = file_end_dt
        
        file_duration = (file_end_dt - file_start_dt).total_seconds()
        print(f"  File duration: {file_duration:.1f} seconds")
        print(f"  Cumulative duration: {cumulative_time_offset/1000:.1f} seconds")
        
        merged_dfs.append(df)
    
    # Concatenate all DataFrames
    merged_df = pd.concat(merged_dfs, ignore_index=True)
    
    print(f"Merged dataset: {len(merged_df)} samples, total duration: {merged_df['TimeStamp'].max()/1000:.1f} seconds")
    
    return merged_df


def get_date_range_from_merged_data(merged_df: pd.DataFrame, files: List[str]) -> Tuple[str, str]:
    """
    Extract start and end dates from the first and last files for video matching.
    
    Args:
        merged_df: Merged eye tracking DataFrame
        files: List of original file paths
        
    Returns:
        Tuple of (start_date, end_date) strings
    """
    if not files:
        raise ValueError("No files provided")
    
    # Extract dates from first and last files
    first_file = os.path.basename(files[0])
    last_file = os.path.basename(files[-1])
    
    # Parse start date from first file
    start_date = first_file.split('_')[-2]
    
    # Parse end date from last file  
    end_date = last_file.split('_')[-1].split('.')[0]
    
    return start_date, end_date


def main(date: str = None, user: str = None, eye_dir: str = None, video_dir: str = None, highlight_dir: str = None, number_of_highlights: int = None, delta_seconds: int = None):
    """
    Main function to process eye tracking data and extract highlights.
    
    Args:
        date: Date string in format YYYY-MM-DD
        user: Username for file filtering
        eye_dir: Directory containing eye tracking TSV files
        video_dir: Directory containing video files
        highlight_dir: Directory to save extracted highlights
        number_of_highlights: Number of highlight clips to extract
        delta_seconds: Minimum time separation between highlights in seconds
    """
    import sys
    import glob
    
    # Default values
    if date is None:
        date = '2025-05-23'
    if user is None:
        user = "TEST_SUBJECT"
    if eye_dir is None:
        eye_dir = '/home/trustme/trust-me-setup/installers/data_collection/TEST_SUBJECT/tobii/'
    if video_dir is None:
        video_dir = '/home/trustme/trust-me-setup/installers/data_collection/TEST_SUBJECT/hires/'
    if highlight_dir is None:
        highlight_dir = f'/home/trustme/trust-me-setup/highlights/{user}/'
    if number_of_highlights is None:
        number_of_highlights = 4
    if delta_seconds is None:
        delta_seconds = 1800  # 30 minutes

    print(f"Processing eye tracking data for {user} on {date}")
    print(f"Eye tracking dir: {eye_dir}")
    print(f"Video dir: {video_dir}")
    print(f"Highlight dir: {highlight_dir}")
    print(f"Number of highlights: {number_of_highlights}")
    print(f"Minimum separation: {delta_seconds} seconds")
    
    # Find and merge all eye tracking files for the date
    pattern = os.path.join(eye_dir, f"{user}_{date}*.tsv")
    files = glob.glob(pattern)
    
    if not files:
        print(f"Error: No eye tracking files found for {user} on {date} in {eye_dir}")
        return
    
    # Merge all files
    df = merge_eyetracking_files(eye_dir, user, date)
    
    # Calculate interest features
    print("Calculating interest features...")
    df = calculate_interest_features(df)
    
    # Get date range for video matching
    start_date, end_date = get_date_range_from_merged_data(df, files)
    print(f"Date range: {start_date} to {end_date}")
    
    # Find and assign videos to frames
    print("Finding matching videos...")
    videos = video2eye(df, start_date, end_date, video_dir)
    print(f"Found {len(videos)} matching videos")
    
    df = assign_video_to_frames(df, videos, start_date)

    print("Assigned video_file column")
    print(f"Frames with video: {len(df[df['video_file'].notna()])}")
    print(f"Frames without video: {len(df[df['video_file'].isna()])}")
    
    # Find top n peaks with at least delta seconds apart
    print(f"Finding top {number_of_highlights} peaks with {delta_seconds}s minimum separation...")
    peaks = find_top_n_peaks(df, n=number_of_highlights, delta=delta_seconds)
    # print("Top peaks:", peaks)
    
    # Extract highlights
    print("Extracting highlights...")
    extract_highlights(df, peaks, highlight_dir)
    print("Done!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract highlights from eye tracking data')
    parser.add_argument('--date', type=str, help='Date in format YYYY-MM-DD (default: 2025-05-23)')
    parser.add_argument('--user', type=str, help='Username for file filtering (default: TEST_SUBJECT)')
    parser.add_argument('--eye-dir', type=str, help='Directory containing eye tracking TSV files')
    parser.add_argument('--video-dir', type=str, help='Directory containing video files')
    parser.add_argument('--highlight-dir', type=str, help='Directory to save extracted highlights')
    parser.add_argument('--highlights', type=int, help='Number of highlight clips to extract (default: 4)')
    parser.add_argument('--separation', type=int, help='Minimum time separation between highlights in seconds (default: 1800)')
    
    args = parser.parse_args()
    
    main(
        date=args.date,
        user=args.user,
        eye_dir=args.eye_dir,
        video_dir=args.video_dir,
        highlight_dir=args.highlight_dir,
        number_of_highlights=args.highlights,
        delta_seconds=args.separation
    )
