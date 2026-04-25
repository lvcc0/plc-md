#!/usr/bin/bash

NPROCS=2

mpirun -np $NPROCS lmp -in $1
