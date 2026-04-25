#!/usr/bin/bash

# we don't want this to be ran with sudo
if [ ! -z "$SUDO_USER" ]; then
    echo "don't sudo this, please"
    exit 1
fi

read -p "Soft [s] or Hard [h] loading for shear modelling: " choice

case $choice in
    [Ss] *)
        echo "You selected Soft-loading (constant force)"
        SHEAR_SCRIPT="in.shear-soft"        
        ;;
    [Hh] *)
        echo "You selected Hard-loading (constant speed)"
        SHEAR_SCRIPT="in.shear-hard"
        ;;
    *)
        echo "Invalid choice, aborting"
        exit 1
        ;;
esac

# create venv if it doesn't exist
[ -d "venv" ] || python -m venv venv

# TODO: should install python packages here actually

# activate venv
source venv/bin/activate

# make "run.sh" executable if it's not
[ -x "run.sh" ] || chmod +x "run.sh"

#######################
# ACTUAL CALCULATIONS #
#######################

./run.sh in.equilibration
./run.sh $SHEAR_SCRIPT

python position.py
python velocity.py
