#!/usr/bin/bash

# NOTE: check for OMP_NUM_THREADS env var!
#       more often than not it should be 2:
#
#export OMP_NUM_THREADS=2

# NOTE: this script is dumb so please put the name
#       of the script you want to run in $1
#       like so: ./run.sh src/in.eqilibration [--gpu]

NPROCS=2

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
    mpirun -np $NPROCS --bind-to core --map-by core lmp -sf gpu -pk gpu 1 -in "$file" "${args[@]}"
	exit 0
fi

echo "running mpirun with cpu util only..."
mpirun -np $NPROCS --bind-to core --map-by core lmp -sf omp -in "$file" "${args[@]}"
