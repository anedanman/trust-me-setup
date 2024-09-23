#!/bin/bash

PID_DIR="/home/dis/trust-me-setup/tmp/pids/tobiish"
echo $$ > "$PID_DIR"

cd /home/$(whoami)/trust-me-setup/installers/tobii
/home/$(whoami)/miniconda3/envs/tobii/bin/python run_tobii.py

