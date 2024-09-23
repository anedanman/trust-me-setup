#!/bin/bash

cd /home/$(whoami)/trust-me-setup/installers/tobii
/home/$(whoami)/miniconda3/envs/tobii/bin/python run_tobii.py --uname "$@"

