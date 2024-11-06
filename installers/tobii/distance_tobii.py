from pygaze.eyetracker import EyeTracker
from pygaze._eyetracker.libtobii import TobiiProTracker


class DistanceTobii(TobiiProTracker):
    """
    A class that uses the EyeTracker class from PyGaze but also logs the distance
    """
    def __init__(self, display, **args):
        super().__init__(display, **args)
        self._write_header = self.new_write_header
        self._write_sample = self.new_write_sample

    def new_write_header(self):
        self.datafile.write('\t'.join(['TimeStamp',
                                    'Event',
                                    'GazePointXLeft',
                                    'GazePointYLeft',
                                    'ValidityLeft',
                                    'GazePointXRight',
                                    'GazePointYRight',
                                    'ValidityRight',
                                    'GazePointX',
                                    'GazePointY',
                                    'PupilSizeLeft',
                                    'PupilValidityLeft',
                                    'PupilSizeRight',
                                    'PupilValidityRight',
                                    'DistanceLeft',      # New column
                                    'DistanceRight',     # New column
                                    'AverageDistance'    # New column
                                    ]) + '\n')
        self._flush_to_file()

    def new_write_sample(self, sample):
        _write_buffer = ""
        # write timestamp and gaze position for both eyes
        left_gaze_point = self._norm_2_px(sample['left_gaze_point_on_display_area']) if sample['left_gaze_point_validity'] else (-1, -1)  # noqa: E501
        right_gaze_point = self._norm_2_px(sample['right_gaze_point_on_display_area']) if sample['right_gaze_point_validity'] else (-1, -1)  # noqa: E501
        _write_buffer += '\t{}\t{}\t{}\t{}\t{}\t{}'.format(
            left_gaze_point[0],
            left_gaze_point[1],
            sample['left_gaze_point_validity'],
            right_gaze_point[0],
            right_gaze_point[1],
            sample['right_gaze_point_validity'])

        # if no correct sample is available, data is missing
        if not (sample['left_gaze_point_validity'] or sample['right_gaze_point_validity']):  # not detected
            ave = (-1.0, -1.0)
        # if the right sample is unavailable, use left sample
        elif not sample['right_gaze_point_validity']:
            ave = left_gaze_point
        # if the left sample is unavailable, use right sample
        elif not sample['left_gaze_point_validity']:
            ave = right_gaze_point
        # if we have both samples, use both samples
        else:
            ave = (int(round((left_gaze_point[0] + right_gaze_point[0]) / 2.0, 0)),
                   (int(round(left_gaze_point[1] + right_gaze_point[1]) / 2.0)))

        # write gaze position, based on the selected sample(s)
        _write_buffer += '\t{}\t{}'.format(ave[0], ave[1])

        left_pupil = sample['left_pupil_diameter'] if sample['left_pupil_validity'] else -1
        right_pupil = sample['right_pupil_diameter'] if sample['right_pupil_validity'] else -1

        _write_buffer += '\t{}\t{}\t{}\t{}'.format(
            round(left_pupil, ndigits=4),
            sample['left_pupil_validity'],
            round(right_pupil, ndigits=4),
            sample['right_pupil_validity'])

        # Add distance calculations
        left_distance = round(sample['left_gaze_origin_in_user_coordinate_system'][2] / 10, 1) if sample['left_gaze_origin_validity'] else -1
        right_distance = round(sample['right_gaze_origin_in_user_coordinate_system'][2] / 10, 1) if sample['right_gaze_origin_validity'] else -1

        # Calculate average distance using same logic as gaze points
        if not (sample['left_gaze_origin_validity'] or sample['right_gaze_origin_validity']):
            avg_distance = -1
        elif not sample['right_gaze_origin_validity']:
            avg_distance = left_distance
        elif not sample['left_gaze_origin_validity']:
            avg_distance = right_distance
        else:
            avg_distance = round((left_distance + right_distance) / 2.0, 1)

        # Add distances to write buffer
        _write_buffer += '\t{}\t{}\t{}'.format(
            left_distance,
            right_distance,
            avg_distance)

        # Write buffer to the datafile
        self.log(_write_buffer)
