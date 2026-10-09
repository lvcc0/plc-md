#!/usr/bin/bash

# NOTE: this script is dumb so please put the name
#       of the script you want to run in $1
#       like so: ./run.sh src/in.equilibration [--gpu]


# !! set this variable to cores available !! #
NPROC=0


if [ -z $OMP_NUM_THREADS ]; then
    OMP_NUM_THREADS=1
    echo "OMP_NUM_THREADS env var is not set, defaulting to 1 thread"
fi

if [ $NPROC -eq 0 ]; then
    NPROC=$(nproc)
    echo "NPROC var is not set, defaulting to $NPROC cores"
    echo "please, set NPROC var in the \"run.sh\" script"
fi

echo "using $NPROC cores, $OMP_NUM_THREADS omp threads"

file="$1"
shift

args=()

# filter "--gpu" from actual lmp flags
for arg in "$@"; do
    if [[ "$arg" != "--gpu" ]]; then
        args+=("$arg")
    fi
done

if [[ " $* " == *" --gpu "* ]]; then
    echo "running mpirun with gpu util..."
    mpirun -np $NPROC --bind-to core --map-by core lmp -sf gpu -pk gpu 1 -in "$file" "${args[@]}"
    exit 0
fi

echo "running mpirun with cpu util only..."
mpirun -np $NPROC --bind-to core --map-by core lmp -sf omp -in "$file" "${args[@]}"
