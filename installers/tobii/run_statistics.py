import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# import scipy.stats as stats
# import seaborn as sns
import os
import re
from datetime import timedelta, datetime


# Function for the basic data modification
def from_timer_to_date(timer_string, y, month, d, h, m, s, micro):
    recS = datetime(
        year=y, month=month, day=d, hour=h, minute=m, second=s, microsecond=micro
    )
    # the timer is expressed in milliseconds so we need to retrieve the microseconds
    # print(recS+ timedelta(microseconds=float(timer_string)*1000))
    return str(recS + timedelta(microseconds=float(timer_string) * 1000)).split()[0]


def from_timer_to_timestamp(timer_string, y, month, d, h, m, s, micro):
    recS = datetime(
        year=y, month=month, day=d, hour=h, minute=m, second=s, microsecond=micro
    )
    # the timer is expressed in milliseconds so we need to retrieve the microseconds
    list_info = (
        str(recS + timedelta(microseconds=float(timer_string) * 1000))
        .split()[1]
        .split(":")
    )
    return "{}:{}:{}".format(list_info[0], list_info[1], list_info[2].split(".")[0])


def get_millis_elapsed(timer_string, y, month, d, h, m, s, micro):
    recS = datetime(
        year=y, month=month, day=d, hour=h, minute=m, second=s, microsecond=micro
    )
    # the timer is expressed in milliseconds so we need to retrieve the microseconds
    return (
        str(recS + timedelta(microseconds=float(timer_string) * 1000))
        .split()[1]
        .split(":")[-1]
        .split(".")[1]
    )


# Function to check if the person is blinking
def isBlinking(row):
    if row["ValidityRight"] and row["ValidityLeft"] and row["Dilation_avg"] == -1.0:
        return True
    return False


def avg_pupil_dilation(row):
    if row["PupilSizeLeft"] == -1.0 or row["PupilSizeRight"] == -1.0:
        return -1.0
    else:
        return round((row["PupilSizeLeft"] + row["PupilSizeRight"]) / 2.0, 4)


# Import all the files which are test files or timestamps files
def create_csv(path="./tobii/recordings/"):
    # print('\n')

    files = [
        f
        for f in os.listdir(path)
        if f.endswith(".tsv") and f.startswith("calibration")
    ]
    # print(files)
    df = None
    list_of_data = []
    columns = [
        "Timestamp",
        "GazePointXLeft",
        "GazePointYLeft",
        "ValidityLeft",
        "GazePointXRight",
        "GazePointYRight",
        "ValidityRight",
        "GazePointX",
        "GazePointY",
        "PupilSizeLeft",
        "PupilValidityLeft",
        "PupilSizeRight",
        "PupilValidityRight",
    ]

    # for each test file save its data into a dataframe
    for index, file in enumerate(files):
        # print(files)
        f_name_r = path + file
        # get the timestamp of start recording
        start_recording = f_name_r.split("_")[1].split("$")[1]
        mode = "r"
        fileR = open(f_name_r, mode=mode)

        # remove without start and end spaces
        last_word = "PupilValidityRight"
        content = fileR.read().split(last_word)[1]
        lines = content.split("\n")
        # remove the log lines
        real_content = lines[1:-1]
        # if it is the first file
        df = pd.DataFrame(columns=columns)
        # retrieve all the data to insert in a pandas dataframe as a list of lists
        rows_for_pd = [element.split() for element in real_content]

        # insert row by row in the dataframe
        for i, el in enumerate(rows_for_pd):
            df.loc[i] = el
        name = file.split("_")[0]
        df.insert(0, "Username", name.split("USER")[-1])

        # get all these information on the start recording values
        timestamp = f_name_r.split("_")[1].split("$")[1].split("-")
        date_rec = f_name_r.split("_")[1].split("$")[0].split("-")

        y = int(date_rec[0])
        month = int(date_rec[1])
        d = int(date_rec[2])
        h = int(timestamp[0])
        m = int(timestamp[1])
        s = int(timestamp[2])
        micro = int(timestamp[3])
        df.insert(1, "Year_Month_day", datetime.now())
        df.insert(3, "MicrosecElapsed", -1.0)
        df["Year_Month_day"] = df["Timestamp"].apply(
            from_timer_to_date, args=(y, month, d, h, m, s, micro)
        )
        df["MicrosecElapsed"] = df["Timestamp"].apply(
            get_millis_elapsed, args=(y, month, d, h, m, s, micro)
        )
        df["Timestamp"] = df["Timestamp"].apply(
            from_timer_to_timestamp, args=(y, month, d, h, m, s, micro)
        )
        # print(df)
        list_of_data.append(df)
    # print(list_of_data)
    # Join all the dataframe together and create a unique dataset
    merged_df = pd.concat(list_of_data, ignore_index=True)
    merged_df["PupilSizeLeft"] = merged_df["PupilSizeLeft"].astype(
        float, errors="ignore"
    )
    merged_df["PupilSizeRight"] = merged_df["PupilSizeRight"].astype(
        float, errors="ignore"
    )
    merged_df["ValidityLeft"] = merged_df["ValidityLeft"].astype(bool, errors="ignore")
    merged_df["ValidityRight"] = merged_df["ValidityRight"].astype(
        bool, errors="ignore"
    )

    # df=df.replace('-1','NaN')
    # df.to_csv('csv_file.csv', index=False)
    # retrieve the values
    # df=pd.read_csv('csv_file.csv', header=0)

    # creation of a column for the average pupil dilation
    merged_df["Dilation_avg"] = -1.0
    merged_df["Dilation_avg"] = merged_df.apply(avg_pupil_dilation, axis=1)

    # print(merged_df.info())
    # # TODO: check correctness and draw up statistics
    # merged_df['isBlinking']=merged_df.apply(isBlinking, axis=1)
    # print(merged_df.head())
    timenow = "{:%Y-%m-%d$%H-%M-%S-%f}".format(datetime.now())
    merged_df.to_csv(f"{path}eyetrackerdata_{timenow}.csv", index=False)

    # delete the rest of the data
    files = [
        f
        for f in os.listdir(path)
        if f.endswith(".tsv") and f.startswith("calibration")
    ]
    for file in files:
        os.remove(f"{path}{file}")

    # plot which displays the pupil size
    # sns.displot(data=merged_df, x="Dilation_avg", hue="Username", multiple="stack", kind="kde")
    plt.show()
