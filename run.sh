#!/usr/bin/bash

# NOTE: this script is dumb so please put the name
#       of the script you want to run in $1
#       like so: ./run.sh src/in.equilibration [--gpu] [-np N]

# first argument is always the input file
file="$1"
shift

args=()

# parsing arguments:
# $np - number of MPI ranks used (gpu package doesn't mean gpu util only!)
# $omp - number of OpenMP threads per MPI rank
# $gpu - number of GPUs to use (disables omp pk, enables gpu pk)
while (($#)); do
    case "$1" in
        -np)
            np=$2
            shift 2
            ;;
        -omp)
            omp=$2
            shift 2
            ;;
        -gpu)
            gpu=$2
            shift 2
            ;;
        *)
            args+=("$1")
            shift
            ;;
    esac
done

if [[ -z $np ]]; then
    np=$(nproc)
    echo "defaulting to $np MPI ranks. you can provide number of MPI ranks using \"-np\" arg"
fi

if [[ -z $omp ]]; then
    if [[ -z $OMP_NUM_THREADS ]]; then
        echo "OMP_NUM_THREADS env var is not set, defaulting to 1 thread"
        omp=1
    else
        omp=$OMP_NUM_THREADS
    fi
fi

echo "using $np MPI ranks x $omp OpenMP threads"

###                                   ###
# RUNNING WITH GPU PACKAGE AND SUFFIXES #
###                                   ###

if [[ ${gpu:-} -ne 0 ]]; then
    echo "running mpirun with $gpu GPU(s)..."

    OMP_NUM_THREADS=$omp \
    OMP_PLACES=cores \
    OMP_PROC_BIND=close \
    mpirun -np $np --bind-to core --map-by core lmp -sf gpu -pk gpu $gpu omp $omp -in "$file" "${args[@]}"

    exit 0
fi

###                                   ###
# RUNNING WITH OMP PACKAGE AND SUFFIXES #
###                                   ###

echo "running mpirun with CPU util only..."

OMP_NUM_THREADS=$omp \
OMP_PLACES=cores \
OMP_PROC_BIND=close \
mpirun -np $np --bind-to core --map-by core lmp -sf omp -pk omp $omp -in "$file" "${args[@]}"
