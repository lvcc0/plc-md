#!/usr/bin/bash

# we don't want this to be ran with sudo
if [ ! -z "$SUDO_USER" ]; then
    echo "don't sudo this, please"
    exit 1
fi

read -p "Soft [s] or Hard [h] loading for shear modelling: " choice

case $choice in
    [Ss])
        echo "You selected Soft-loading (constant force)"
        SHEAR_SCRIPT="in.shear-soft"        
        ;;
    [Hh])
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

# activate venv
source venv/bin/activate

# checking for packages
while IFS=read -r line || [ -n "$line" ]; do
    # skip empty lines
    [[ -z "$line" || "$line" == /#* ]] && continue

    # getting package name
    pkg=$(echo "$line" | sed 's/[<>=!].*//')

    # trying to import found pkg
    python -c "import $pkg" 2>/dev/null

    if [ $? -eq 0 ]; then
        echo -e "\e[32m[v] $pkg is installed.\e[0m"
    else
        echo -e "\e[31m[x] $pkg is not installed. trying to install $line...\e[0m"
        pip install "$line"

        if [ $? -eq 0 ]; then
            echo -e "\e[32m[v] success: $line\e[0m"
        else
            echo -e "\e[31m[x] error: $line\e[0m"
        fi
    fi
done < "requirements.txt"

# make "run.sh" executable if it's not
[ -x "run.sh" ] || chmod +x "run.sh"

#######################
# ACTUAL CALCULATIONS #
#######################

if [[ " $* " == *" --gpu "* ]]; then
	./run.sh src/in.equilibration --gpu
	./run.sh src/$SHEAR_SCRIPT --gpu
else
	./run.sh src/in.equilibration
	./run.sh src/$SHEAR_SCRIPT
fi

python src/position.py
python src/velocity.py
