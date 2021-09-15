#!/bin/bash
until python maintainer.py
do
    echo "Restarting"
    sleep 5
done
