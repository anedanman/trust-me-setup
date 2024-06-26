Code for capturing data from 2x RGB cameras, thermal camera, depth camera and audio.

Entry point is `capture_data.py`. It runs the data collection of each device in a separate process. 

The environment that works both with tobii and this code is specified in `environment.yml` file. You can create a new conda environment from that file with the following command: `conda env create -n <name> -f environment.yml`.
