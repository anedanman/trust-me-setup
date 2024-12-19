import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python import BaseOptions

import os
from pathlib import Path
from typing import Union

import numpy as np
from scipy.signal import savgol_filter
import cv2
import pandas as pd
import numpy as np
from tqdm import tqdm
from moviepy.video.io.VideoFileClip import VideoFileClip


def extract_blendshapes(video_path):
    base_options = BaseOptions(
        model_asset_path='face_landmarker.task',
        # delegate=BaseOptions.Delegate.GPU
    )
    
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=True,
        num_faces=1,
        running_mode=vision.RunningMode.VIDEO,
        # delegate=BaseOptions.Delegate.GPU
    )
    
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        # Get actual video duration using moviepy
        with VideoFileClip(video_path) as video:
            actual_duration = video.duration
            
        # Open video file
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        actual_fps = total_frames / actual_duration
        print(f'Video FPS: {fps}, Total frames: {total_frames}, Duration: {actual_duration:.2f}s', f'Actual FPS: {actual_fps}')
        if total_frames == 0:
            return None

        # Calculate time per frame using actual duration
        time_per_frame = actual_duration / total_frames
        blendshapes_data = []
        frame_count = 0
        
        # Wrap with tqdm for progress bar
        with tqdm(total=total_frames, desc="Processing frames") as pbar:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    break
                
                # Convert frame to RGB (MediaPipe requires RGB)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                
                # Detect face blendshapes
                detection_result = landmarker.detect_for_video(mp_image, frame_count)

                if detection_result.face_blendshapes:
                    # Get blendshapes for the first detected face
                    frame_data = {
                        'frame': frame_count,
                        'timestamp': frame_count * time_per_frame  # Use actual time per frame
                    }
                    
                    # Add all blendshape values
                    for blendshape in detection_result.face_blendshapes[0]:
                        frame_data[blendshape.category_name] = blendshape.score
                        
                    blendshapes_data.append(frame_data)
                else:
                    # Add empty data if no face detected
                    blendshapes_data.append({
                        'frame': frame_count,
                        'timestamp': frame_count * time_per_frame  # Use actual time per frame
                    })
                
                frame_count += 1
                pbar.update(1)
        
        cap.release()
        
    return pd.DataFrame(blendshapes_data)

def create_centered_weights(window):
    """Helper function to create weights with higher values in center"""
    # Create triangular weights
    center = window // 2
    weights = np.zeros(window)
    for i in range(window):
        weights[i] = 1 - abs(i - center) / center
    return weights / weights.sum()  # Normalize to sum to 1

def process_blendshapes(blendshapes_path: Union[str, Path]) -> pd.DataFrame:
    import numpy as np
    import joblib
    import pandas as pd

    # Load original data
    df = pd.read_csv(blendshapes_path)
    # print('original len:', len(df))
    
    # Create mask for valid data
    cols_to_drop = open("cols_to_drop_2.txt").read().split("\n")
    features_df = df.drop(columns=cols_to_drop)
    valid_mask = ~features_df.replace(-1, np.nan).isna().any(axis=1)
    
    # Make predictions only for valid rows
    if valid_mask.any():
        clf = joblib.load("model.pkl")
        valid_preds = clf.predict_proba(features_df[valid_mask])
        
        # Initialize predictions array with zeros
        all_preds = np.zeros(len(df))
        # Fill in valid predictions
        all_preds[valid_mask] = valid_preds[:, 2]
        
        # Add predictions to original dataframe
        df['preds'] = all_preds
    else:
        df['preds'] = 0
    
    # Smooth the predictions while preserving length
    window = 500  # 50 seconds at 10 fps
    weights = create_centered_weights(window)
    df["preds"] = pd.Series(
        np.convolve(df["preds"], weights, mode='same'),
        index=df.index
    )
        
    # print('final len:', len(df))
    return df


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
        
        # Define numeric columns
        numeric_columns = ['TimeStamp', 'GazePointXLeft', 'GazePointYLeft', 
                         'ValidityLeft', 'GazePointXRight', 'GazePointYRight', 
                         'ValidityRight', 'GazePointX', 'GazePointY',
                         'PupilSizeLeft', 'PupilValidityLeft', 'PupilSizeRight',
                         'PupilValidityRight', 'DistanceLeft', 'DistanceRight',
                         'AverageDistance']
        
        # Convert empty strings to NaN
        df = df.replace('', 0.)
        
        # Convert numeric columns to float
        # df[numeric_columns] = df[numeric_columns].astype(float)
        
        # Replace -1 values with NaN
        df = df.replace(-1, 0.)
        
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


def calculate_interest_features(df: pd.DataFrame, video_fps: float = 9.1) -> pd.DataFrame:
    """
    Calculate features indicating potential moments of interest with averaged subsampling.
    
    Args:
        df: DataFrame with eye tracking data
        video_fps: Frame rate of video data (default 10 fps)
    """
    # Calculate time differences and basic features
    df['dt'] = df['TimeStamp'].diff() / 1000.0
    df['dx'] = df['GazePointX'].diff()
    df['dy'] = df['GazePointY'].diff()
    df['eye_speed'] = np.sqrt(df['dx']**2 + df['dy']**2) / df['dt']
    df['pupil_change'] = abs(df['PupilSizeLeft'].diff()) + abs(df['PupilSizeRight'].diff())
    
    # Calculate window size for subsampling
    eyetracker_fps = 1 / df['dt'].mean()
    print('Eyetracker FPS:', eyetracker_fps)
    
    # Create time bins aligned with video frames
    df['time_bin'] = (df['TimeStamp'] // (1000/video_fps)).astype(int)

    window = 16  # About 0.25 seconds of data at 60 Hz
    df['eye_speed'] = savgol_filter(df['eye_speed'].fillna(0), window, 3)
    df['pupil_change'] = savgol_filter(df['pupil_change'].fillna(0), window, 3)
    
    print('Len of data before subsample:', len(df))
    # Group and average by time bins
    df_subsampled = df.groupby('time_bin').agg({
        'TimeStamp': 'max',
        'eye_speed': 'mean',
        'pupil_change': 'mean',
        'GazePointX': 'mean',
        'GazePointY': 'mean',
        'PupilSizeLeft': 'mean',
        'PupilSizeRight': 'mean'
    }).reset_index()
    print('Len of data after subsample:', len(df_subsampled))
    
    # fill NaN values with 0 in eye_speed_sustained and pupil_change_sustained
    df_subsampled['eye_speed'] = df_subsampled['eye_speed'].fillna(0)
    df_subsampled['pupil_change'] = df_subsampled['pupil_change'].fillna(0)
    
    # Normalize features
    for col in ['eye_speed', 'pupil_change']:
        df_subsampled[col] = (df_subsampled[col] - df_subsampled[col].min()) / \
                            (df_subsampled[col].max() - df_subsampled[col].min())
    
    # Additional smoothing for better signal
    window = 500  # 50 seconds at video fps
    weights = create_centered_weights(window)
    
    for col in ['eye_speed', 'pupil_change']:
        df_subsampled[col] = pd.Series(
            np.convolve(df_subsampled[col], weights, mode='same'),
            index=df_subsampled.index
        )
    
    # Calculate interest score
    df_subsampled['interest_score'] = (df_subsampled['eye_speed'] + 
                                      df_subsampled['pupil_change']) / 2
    
    return df_subsampled


def process_video(args):
    """
    Process a single video file and save blendshapes data.
    
    Args:
        args: tuple containing (video_file, video_path, blends_path)
    """
    video_file, video_path, blends_path = args
    try:
        # Full path to video file
        video_full_path = os.path.join(video_path, video_file)
        
        # Extract blendshapes
        df = extract_blendshapes(video_full_path)
        
        # Only save if valid data was returned
        if df is not None:
            # Generate output filename
            output_filename = video_file.replace('.mp4', '_blendshapes.csv')
            output_path = os.path.join(blends_path, output_filename)
            df.to_csv(output_path, index=False)
            return f"Processed {video_file} successfully"
        else:
            return f"Skipped {video_file} - no valid frames"
            
    except Exception as e:
        return f"Error processing {video_file}: {str(e)}"

def blendshapes_group(video_path='./installers/data_collection/data/hires', blends_path='./blendshapes', date='2024-08-27'):
    """
    Process multiple videos from a specific date in parallel and save blendshapes data.
    
    Args:
        video_path: Path to directory containing videos
        blends_path: Path to directory where blendshapes CSV files will be saved
        date: Date string to filter videos (format: YYYY-MM-DD)
    """
    import os
    from concurrent.futures import ProcessPoolExecutor
    from pathlib import Path
    
    # Create blends directory if it doesn't exist
    Path(blends_path).mkdir(parents=True, exist_ok=True)
    
    # Get list of video files for the specified date
    video_files = [f for f in os.listdir(video_path) 
                  if f.endswith('.mp4') and date in f]
    
    # Create arguments for processvideo
    process_args = [(f, video_path, blends_path) for f in video_files]
    
    # Process videos in parallel
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(process_video, process_args))
    
    # Print processing results
    for result in results:
        print(result)

def merge_blendshapes(blends_path='./blendshapes', date='2024-08-27'):
    import re
    from datetime import datetime, timedelta
    
    # Get all blendshape files for the specified date
    files = [f for f in os.listdir(blends_path) 
             if f.endswith('_blendshapes.csv') and date in f]
    
    # Parse filename info
    file_info = []
    pattern = r'(.+?)_chunk(\d+)_(\d{4}-\d{2}-\d{2}\$\d{2}-\d{2}-\d{2}-\d{6})_blendshapes\.csv'
    
    for f in files:
        match = re.match(pattern, f)
        if match:
            nickname = match.group(1)
            chunk_num = int(match.group(2))
            timestamp = datetime.strptime(match.group(3), '%Y-%m-%d$%H-%M-%S-%f')
            file_info.append((f, nickname, chunk_num, timestamp))
    
    # Sort by timestamp
    file_info.sort(key=lambda x: x[3])
    
    # Group files by nickname and sequential chunks
    groups = []
    current_group = []
    
    for file, nickname, chunk_num, timestamp in file_info:
        if not current_group or chunk_num == 0:
            if current_group:  # Save previous group if exists
                groups.append(current_group)
            current_group = [(file, nickname, chunk_num, timestamp)]
        else:
            current_group.append((file, nickname, chunk_num, timestamp))
    
    if current_group:  # Add last group
        groups.append(current_group)
    
    # Merge each group
    for group_idx, group in enumerate(groups):
        merged_df = None
        nickname = group[0][1]  # Get nickname from first file in group
        
        accumulated_frames = 0
        group_start_time = group[0][3]  # First chunk's start time
        
        for file, _, chunk_num, file_start_time in group:
            df = pd.read_csv(os.path.join(blends_path, file))
            
            # Calculate actual fps for this chunk using file timestamps
            chunk_duration = (group[chunk_num + 1][3] - file_start_time).total_seconds() if chunk_num + 1 < len(group) else None
            if chunk_duration is None:
                # For last chunk, use the average fps from previous chunks
                fps = accumulated_frames / ((file_start_time - group_start_time).total_seconds())
            else:
                fps = len(df) / chunk_duration
            
            print(f"Chunk {chunk_num} FPS: {fps:.2f}")
            
            # Recalculate timestamps using actual fps and accumulated frames
            df['frame'] = range(accumulated_frames, accumulated_frames + len(df))
            df['timestamp'] = df['frame'] / fps
            df['chunk'] = chunk_num
            
            # Merge with previous chunks
            merged_df = pd.concat([merged_df, df]) if merged_df is not None else df
            
            # Update accumulated frames
            accumulated_frames += len(df)
        
        # Save merged group
        if merged_df is not None:
            start_time = group[0][3].strftime('%Y-%m-%d$%H-%M-%S')
            end_time = group[-1][3].strftime('%H-%M-%S')
            output_name = f'{nickname}_merged_group{group_idx}_{start_time}_to_{end_time}.csv'
            merged_df.to_csv(os.path.join(blends_path, output_name), index=False)
            print(f"Created merged file: {output_name}")
    return fps

def eyetracker2blendshapes(eyetracker_path='./installers/tobii/recordings', blends_path='./blendshapes', date='2024-08-27',
                           fps=9.1):
    """
    Match and merge eyetracking data with blendshapes data.
    
    Args:
        eyetracker_path: Path to directory containing eyetracking TSV files
        blends_path: Path to directory containing merged blendshape CSV files
        date: Date string to filter files (format: YYYY-MM-DD)
    """
    import re
    from datetime import datetime, timedelta
    
    # Get merged blendshapes and eyetracking files
    blend_files = [f for f in os.listdir(blends_path) 
                   if '_merged_group' in f and date in f and not 'aligned' in f]  # Changed to match any nickname
    eye_files = [f for f in os.listdir(eyetracker_path) 
                 if date in f]
    print(eye_files, blend_files)
    # Parse timestamps
    blend_times = []
    blend_pattern = r'(.+?)_merged_group\d+_(\d{4}-\d{2}-\d{2}\$\d{2}-\d{2}-\d{2})'  # Added nickname capture
    for f in blend_files:
        match = re.search(blend_pattern, f)
        if match:
            nickname = match.group(1)
            start_time = datetime.strptime(match.group(2), '%Y-%m-%d$%H-%M-%S')
            blend_times.append((f, nickname, start_time))
    
    eye_times = []
    # Updated pattern to match both start and end timestamps
    eye_pattern = r'(.+?)_(' + date + r'\$\d{2}-\d{2}-\d{2}-\d{6})_.*\.tsv$'
    for f in eye_files:
        print('f:', f)
        match = re.search(eye_pattern, f)
        print('match:', match)
        if match:
            start_time = datetime.strptime(match.group(2), '%Y-%m-%d$%H-%M-%S-%f')
            eye_times.append((f, start_time))
    
    # Sort by timestamp
    blend_times.sort(key=lambda x: x[2])
    eye_times.sort(key=lambda x: x[1])
    
    # Match pairs within 10 minutes threshold
    matched_pairs = []
    for blend_file, nickname, blend_time in blend_times:
        best_match = None
        min_diff = timedelta(minutes=10)
        
        for eye_file, eye_time in eye_times:
            time_diff = abs(blend_time - eye_time)
            print(f"Time diff between {blend_file} and {eye_file}: {time_diff}")
            if time_diff < min_diff:
                min_diff = time_diff
                best_match = (eye_file, eye_time)
        
        if best_match and min_diff < timedelta(minutes=10):
            matched_pairs.append((blend_file, nickname, best_match[0], (blend_time - best_match[1]).total_seconds()))

    print(f"Matched {len(matched_pairs)} pairs:")
    print(matched_pairs)

    # Process matched pairs
    for blend_file, nickname, eye_file, time_diff in matched_pairs:
        # Load data
        blend_df = process_blendshapes(os.path.join(blends_path, blend_file))
        eye_df = load_eyetracking_data(os.path.join(eyetracker_path, eye_file))
        print('Len of dataframes:', len(blend_df), len(eye_df))
        eye_df = calculate_interest_features(eye_df, video_fps=fps)
        print('Len of dataframes after processing:', len(blend_df), len(eye_df))
        
        # Align data using filename time difference
        if time_diff > 0:  # Eyetracking starts first
            eye_df = drop_initial_timewindow(eye_df, time_diff)
        
        # Make lengths equal by cutting extra rows
        min_len = min(len(blend_df), len(eye_df))
        print('Min len:', min_len)
        blend_df = blend_df.iloc[:min_len]
        eye_df = eye_df.iloc[:min_len]
        print('rusulting lengths:', len(blend_df), len(eye_df))
        
        # Properly copy over chunk and preds from blend_df to eye_df
        eye_df['chunk'] = blend_df['chunk'].values  # Use .values to ensure direct assignment
        eye_df['interest_score'] = 0.5 * eye_df['interest_score'] + 0.5 * blend_df['preds'].values
        
        # Save merged result with nickname
        output_name = f"aligned_{os.path.basename(blend_file)}"
        eye_df.to_csv(os.path.join(blends_path, output_name), index=False)
        print(f"Created aligned file: {output_name}")

def find_top_n_peaks(df, n, delta):
    """
    Find top n peaks by highest interest score values, ensuring minimum time distance between all peaks.
    
    Args:
        df: DataFrame containing 'interest_score', 'timestamp', and 'chunk' columns
        n: Number of peaks to find
        delta: Minimum seconds between peaks (converted to ms internally)
    """
    delta_ms = delta * 1000  # Convert delta from seconds to milliseconds
    
    # Create list of potential peaks sorted by score
    peaks_info = []
    chunk_starts = {chunk: df[df['chunk'] == chunk]['TimeStamp'].iloc[0] 
                   for chunk in df['chunk'].unique()}
    
    # Get indices sorted by interest_score in descending order
    sorted_indices = df['interest_score'].argsort()[::-1]
    
    # Create initial peaks list with metadata
    for idx in sorted_indices:
        chunk = df.loc[idx, 'chunk']
        abs_timestamp = df.loc[idx, 'TimeStamp']
        rel_timestamp = (abs_timestamp - chunk_starts[chunk]) / 1000.0
        score = df.loc[idx, 'interest_score']
        peaks_info.append((idx, abs_timestamp, rel_timestamp, chunk, score))
    
    # Filter peaks ensuring minimum time distance between ALL pairs
    selected_peaks = []
    for peak in peaks_info:
        # Check if this peak is far enough from ALL already selected peaks
        is_valid = True
        if chunk == -1:
            continue
        for selected in selected_peaks:
            if abs(peak[1] - selected[1]) < delta_ms:
                is_valid = False
                break
        
        if is_valid:
            selected_peaks.append(peak)
            if len(selected_peaks) == n:
                break
    
    return selected_peaks

def highlights(video_path='./installers/data_collection/data/hires', blends_path='./blendshapes', highlights_path='./highlights', 
              date='2024-08-27', delta=900, n_highlights=5, screen_recording_path=None):
    import re
    from pathlib import Path
    from datetime import datetime, timedelta

    # Create highlights directory
    Path(highlights_path).mkdir(parents=True, exist_ok=True)
    
    # Load all aligned files
    aligned_files = [f for f in os.listdir(blends_path) 
                    if f.startswith('aligned_') and date in f]
    print('aligned_files:', aligned_files)
    highlight_n = 0

    # If screen recording path provided, cache screen recordings info
    screen_recordings = {}
    if screen_recording_path:
        for rec_file in os.listdir(screen_recording_path):
            if rec_file.endswith('.mp4') and date in rec_file:
                # Extract timestamp from filename (assuming format: *_YYYY-MM-DD$HH-MM-SS-uuuuuu.mp4)
                time_match = re.search(rf'({date}\$\d{{2}}-\d{{2}}-\d{{2}}-\d{{6}})\.mp4$', rec_file)
                if time_match:
                    rec_time = datetime.strptime(time_match.group(1), '%Y-%m-%d$%H-%M-%S-%f')
                    screen_recordings[rec_time] = rec_file

    for aligned_file in aligned_files:
        # Extract start time of the aligned file from its name
        aligned_time_match = re.search(r'merged_group\d+_(\d{4}-\d{2}-\d{2}\$\d{2}-\d{2}-\d{2})', aligned_file)
        if not aligned_time_match:
            print(f"Skipping file {aligned_file} - no timestamp found")
            continue
        aligned_start_time = datetime.strptime(aligned_time_match.group(1), '%Y-%m-%d$%H-%M-%S')
        
        nickname_match = re.search(r'aligned_(.+?)_merged_group', aligned_file)
        if not nickname_match:
            print(f"Skipping file {aligned_file} - no nickname found")
            continue
        nickname = nickname_match.group(1)
        
        # Load aligned data and find peaks
        df = pd.read_csv(os.path.join(blends_path, aligned_file))
        peaks = find_top_n_peaks(df, n_highlights, delta)
        
        # Cache video file information
        video_info = {}
        for video_file in os.listdir(video_path):
            if video_file.endswith('.mp4') and nickname in video_file and date in video_file:
                match = re.match(rf"{nickname}_chunk(\d+)_({date}\$\d{{2}}-\d{{2}}-\d{{2}}-\d{{6}})\.mp4", video_file)
                if match:
                    chunk = int(match.group(1))
                    video_time = datetime.strptime(match.group(2), '%Y-%m-%d$%H-%M-%S-%f')
                    if chunk not in video_info:
                        video_info[chunk] = []
                    video_info[chunk].append((video_file, video_time))
        
        # Process each peak
        for i, (peak_idx, abs_timestamp, rel_timestamp, chunk, score) in enumerate(peaks):
            if chunk not in video_info:
                print(f"No videos found for chunk {chunk}")
                continue
                
            # Get chunk start time from the dataframe
            chunk_data = df[df['chunk'] == chunk]
            if len(chunk_data) == 0:
                print(f"No data found for chunk {chunk}")
                continue
                
            # Calculate absolute time of the highlight
            chunk_start_time = aligned_start_time + timedelta(seconds=chunk_data['TimeStamp'].iloc[0] / 1000)
            highlight_time = chunk_start_time + timedelta(seconds=rel_timestamp)
            

            # Find closest video by timestamp
            closest_video = min(video_info[chunk], 
                              key=lambda x: abs((x[1] - chunk_start_time).total_seconds()))
            

            video_file, video_time = closest_video
            correction_time = (video_time - chunk_start_time).total_seconds()
            time_diff = (highlight_time - video_time).total_seconds()
            time_diff += correction_time
            
            # print out video time and chunk start time
            print(f'Video time: {video_time}, Chunk{chunk} start time: {chunk_start_time}')
            print(f'Using video {video_file} for highligsht at {highlight_time}, time difference: {time_diff:.2f}s')
            
            try:
                # Process webcam video
                video = VideoFileClip(os.path.join(video_path, video_file))
                adjusted_timestamp = max(0, time_diff)
                start_time = max(0, adjusted_timestamp - 60)
                end_time = min(adjusted_timestamp + 60, video.duration)
                
                clip = video.subclipped(start_time, end_time)
                base_name = f"{nickname}_{date}_highlight{highlight_n}_{highlight_time}_score{score:.3f}"
                
                # Save webcam highlight
                clip.write_videofile(
                    os.path.join(highlights_path, f"{base_name}_webcam.mp4"),
                    codec='libx264',
                    audio=False
                )
                
                # Process screen recording if available
                if screen_recording_path:
                    # Find closest screen recording by timestamp
                    closest_rec_time = min(screen_recordings.keys(),
                                         key=lambda x: abs((x - highlight_time).total_seconds()))
                    
                    rec_file = screen_recordings[closest_rec_time]
                    screen_video = VideoFileClip(os.path.join(screen_recording_path, rec_file))
                    
                    # Calculate timing in screen recording
                    screen_time_diff = (highlight_time - closest_rec_time).total_seconds()
                    screen_start = max(0, screen_time_diff - 60)
                    screen_end = min(screen_time_diff + 60, screen_video.duration)
                    
                    screen_clip = screen_video.subclipped(screen_start, screen_end)
                    screen_clip.write_videofile(
                        os.path.join(highlights_path, f"{base_name}_screen.mp4"),
                        codec='libx264',
                        audio=False
                    )
                    screen_clip.close()
                    screen_video.close()
                
                clip.close()
                video.close()
                print(f"Saved highlight: {base_name}")
                highlight_n += 1
                
            except Exception as e:
                print(f"Error processing highlight {i} from {video_file}: {str(e)}")
                continue


def main():
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description='Process screen recordings and generate highlights')
    parser.add_argument('--date', type=str, 
                       default=datetime.now().strftime('%Y-%m-%d'),
                       help='Date to process in YYYY-MM-DD format')
    parser.add_argument('--screen-recordings', type=str,
                       help='Path to screen recordings directory')
    parser.add_argument('--video-path', type=str,
                       default='./installers/data_collection/data/hires',
                       help='Path to webcam videos directory')
    parser.add_argument('--blends-path', type=str,
                       default='./blendshapes',
                       help='Path to save/load blendshapes data')
    parser.add_argument('--highlights-path', type=str,
                       default='./highlights',
                       help='Path to save highlights')
    parser.add_argument('--skip-blendshapes', action='store_true',
                       help='Skip blendshapes processing')
    parser.add_argument('--skip-matching', action='store_true',
                       help='Skip matching processing')
    
    args = parser.parse_args()
    fps = 9.1
    # Process blendshapes
    if not args.skip_blendshapes:
        print(f"Processing blendshapes for date: {args.date}")
        blendshapes_group(video_path=args.video_path, 
                         blends_path=args.blends_path,
                         date=args.date)
        fps = merge_blendshapes(blends_path=args.blends_path,
                         date=args.date)
    
    # Process eye tracking data
    if not args.skip_matching:
        print(f"Processing matching data for date: {args.date}")
        eyetracker2blendshapes(blends_path=args.blends_path,
                              date=args.date,
                              fps=fps)
    
    # Generate highlights
    print(f"Generating highlights for date: {args.date}")
    highlights(video_path=args.video_path,
              blends_path=args.blends_path,
              highlights_path=args.highlights_path,
              date=args.date,
              screen_recording_path=args.screen_recordings)

if __name__ == "__main__":
    main()
