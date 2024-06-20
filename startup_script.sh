#!/bin/bash

# source ~/miniconda3/etc/profile.d/conda.sh

source "C:/Users/sebas/miniconda3/etc/profile.d/conda.sh"

echo $(conda --version);

# Tobii
TOBII_PATH="C:/Users/sebas/Desktop/repos/trust-me-setup/installers/tobii/run_tobii.sh";
RGB_PATH="C:/Users/sebas/Desktop/repos/trust-me-setup/installers/data_capture/capture_data.py";


#"path/to/tobii/file"

conda activate tobii

# Presume it is calibrated
chmod +x "$TOBII_PATH"

$("$TOBII_PATH") &
echo "Started recording tobii"


conda activate trust-me

$(python "$RGB_PATH") &
echo "Started recording RGB"


wait
echo "Done"
