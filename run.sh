#!/usr/bin/bash

# NOTE: this script is dumb so please put the name
#       of the script you want to run in $1
#       like so: ./run.sh src/in.equilibration [--gpu] [-np N]

# first argument is always the input file
file="$1"
shift

# parsing arguments
while (($#)); do
    case "$1" in
    -np)
        if (($# < 2)); then
            echo "missing value for -np" >&2
            exit 1
        fi
        np=$2
        shift 2
        ;;
    --gpu)
        gpu=true
        shift
        ;;
    *)
        echo "unknown argument: $1" >&2
        exit 1
        ;;
    esac
done

if [[ -z $OMP_NUM_THREADS ]]; then
    OMP_NUM_THREADS=1
    echo "OMP_NUM_THREADS env var is not set, defaulting to 1 thread"
fi

if [[ -z $np ]]; then
    np=$(nproc)
    echo "defaulting to $np cores. you can provide number of cores using \"-np\" arg"
fi

##################
# ACTUAL RUNNING #
##################

echo "using $np cores, $OMP_NUM_THREADS omp threads"

if [[ $gpu == true ]]; then
    echo "running mpirun with gpu util..."
    mpirun -np $np --bind-to core --map-by core lmp -sf gpu -pk gpu 1 -in "$file" "$@"
    exit 0
fi

echo "running mpirun with cpu util only..."
mpirun -np $NPROC --bind-to core --map-by core lmp -sf omp -in "$file" "$@"
