#!/usr/bin/bash

# TODO: hybrid

# NOTE: you can use "lscpu" command to check
#       how many physical CPU cores are available

summary="benchmark-summary.txt"
: > "$summary"

while (($#)); do
    case "$1" in
        -ranks)
            ranks=$2
            shift 2
            ;;
        -gpu)
            gpu=$2
            shift 2
            ;;
        -clean)
            clean=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [[ -z $ranks ]]; then
    ranks=$(nproc)
    echo "defaulting max MPI rank tested to $ranks. you can provide number of MPI ranks using \"-ranks\" arg"
fi

if [[ ${gpu:-} -ne 0 ]]; then
	echo "=== benchmarking using $gpu GPU(s) ==="

    for ((np = 1; np <= $ranks; np++)); do
        file_name="bm.gpu.${np}x${omp}"
        omp=$(( ranks / np ))

        ./run.sh src/in.equilibration -np $np -gpu $gpu -omp $omp \
            -var eq_run_steps 5000 \
            -var seg_run_steps 5000 \
            -var file_name $file_name

        {
            echo
            echo "=== MPI ranks: $np, threads/rank: $omp ==="
            grep -E '^(Loop time|CPU use)' logs/equilibrations/"$file_name".log

            if grep -q 'Performance' logs/equilibrations/"$file_name".log; then
                echo
                grep --color=always 'Performance:' logs/equilibrations/"$file_name".log
                echo
            fi
        } >> "$summary"

        if [[ -n ${clean:-} ]]; then
            rm logs/equilibrations/"$file_name".log
            rm dumps/equilibrations/"$file_name".atom
            rm restarts/equilibrations/"$file_name".restart
        fi
    done

	exit 0
fi

echo "=== benchmarking using CPU only ==="

for ((np = 1; np <= $ranks; np++)); do
    file_name="bm.cpu.${np}x${omp}"
    omp=$(( ranks / np ))

    ./run.sh src/in.equilibration -np $np -omp $omp \
        -var eq_run_steps 5000 \
        -var seg_run_steps 5000 \
        -var file_name $file_name

    {
        echo
        echo "=== MPI ranks: $np, threads/rank: $omp ==="
        grep -E '^(Loop time|CPU use)' logs/equilibrations/"$file_name".log

        if grep -q 'Performance' logs/equilibrations/"$file_name".log; then
            echo
            grep --color=always 'Performance:' logs/equilibrations/"$file_name".log
            echo
        fi
    } >> "$summary"

    if [[ -n ${clean:-} ]]; then
        rm logs/equilibrations/"$file_name".log
        rm dumps/equilibrations/"$file_name".atom
        rm restarts/equilibrations/"$file_name".restart
    fi
done
