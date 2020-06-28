#!/bin/bash

PATH_BIN_PYTHON=$(which python3)
PATH_BIN_PIP="$(which pip)"


if [ -z "$PATH_BIN_PYTHON" ]
then
  # Some desktop MacOS systems struggle to locate node in daemon. Make an
  # educated guess

  PATH_BIN_PYTHON="/usr/local/bin/python3"
fi

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PATH_APP="$CURRENT_DIR/app"

param_install=""
install_requirements=false

# If the install command-line param is null, go ahead with install of all
# requirements.txt dependencies

sudo $PATH_BIN_PIP install -r requirements.txt

sudo pip3 install paho-mqtt
sudo pip3 install pillow
sudo pip3 install opencv-python==4.1.2.30

echo "[CAMERA-MACOS] Booting."
cd "$PATH_APP"

# Run the service

echo "[CAMERA-MACOS] Starting service."

$PATH_BIN_PYTHON boot.py
