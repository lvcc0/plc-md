#!/usr/bin/bash

# TODO: hybrid

# ABOUT: super basic benchmark script.
#        just iterates through all available configurations
#        and logs efficiency every iteration

# NOTE: you can use "lscpu" command to check
#       how many physical CPU cores are available

STEPS=3000
TEST_FILE=src/in.equilibration

# parsing arguments
while (($#)); do
    case "$1" in
        # max number of MPI ranks tested
        -ranks)
            ranks=$2
            shift 2
            ;;
        # how many (if any) GPUs to utilize
        -gpu)
            gpu=$2
            shift 2
            ;;
        # delete dumps, restarts, logs
        -clean)
            clean=true
            shift
            ;;
        # skip all other args
        *)
            shift
            ;;
    esac
done

# defaulting ranks if not provided by the "-ranks" arg
if [[ -z $ranks ]]; then
    ranks=$(nproc)
    echo "defaulting max MPI rank tested to $ranks. you can provide number of the max MPI rank using \"-ranks\" arg."
fi

# getting current mode (cpu/gpu) and setting a name for a summary file
mode=$( [[ ${gpu:-} -ne 0 ]] && echo "gpu" || echo "cpu" )
summary="benchmark_${mode}_$(date +%d-%m-%y_%H-%M).log"

# setting the header in the summary file (and clearing it)
if [[ "$mode" == "cpu" ]]; then
    echo "=== benchmarking using CPU only ===" > "$summary"
else
    echo "=== benchmarking using $gpu GPU(s) ===" > $"summary"
fi

for ((np = 1; np <= $ranks; np++)); do
    omp=$(( ranks / np ))
    file_name="bm.${mode}.${np}x${omp}"

    log_name=logs/equilibrations/"$file_name".log
    dump_name=dumps/equilibrations/"$file_name".atom
    restart_name=restarts/equilibrations/"$file_name".restart

    # actually running lammps
    if [[ "$mode" == "cpu" ]]; then
        ./run.sh "$TEST_FILE" -np $np -omp $omp \
            -var eq_run_steps $STEPS \
            -var seg_run_steps $STEPS \
            -var file_name "$file_name"
    else
        ./run.sh "$TEST_FILE" -np $np -omp $omp -gpu $gpu \
            -var eq_run_steps $STEPS \
            -var seg_run_steps $STEPS \
            -var file_name "$file_name"
    fi

    # logging results in the summary file
    {
        echo
        echo "=== MPI ranks: $np, threads/rank: $omp ==="
        grep -E '^(Loop time|.*CPU use)' "$log_name"

        if grep -q 'Performance' "$log_name"; then
            echo
            grep 'Performance:' "$log_name"
        fi
    } >> "$summary"

    # cleaning up if the corresponding arg was given
    if [[ -n ${clean:-} ]]; then
        rm "$log_name"
        rm "$dump_name"
        rm "$restart_name"
    fi
done
