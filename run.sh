#!/bin/bash

NPROCS=2
INPUT_FILE="plc-md.lmp"

mpirun -np $NPROCS lmp -in $INPUT_FILE
