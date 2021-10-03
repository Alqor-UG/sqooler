#!/bin/bash
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate dj_py385

until python /home/ubuntu/Spooler_files/maintainer.py
do
    echo "Restarting"
    sleep 5
done
