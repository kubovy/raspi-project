#!/usr/bin/env bash

cd $(dirname $0)
sudo -u pi git pull
if [[ -z $1 || -z $2 ]]; then
    python ./main.py --help
    exit 1
fi

sudo pigpiod # If needed

# Edit the following line
sudo python ./main.py $1 $2 -d -m comma,separated,modules,here
