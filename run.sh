#!/usr/bin/bash

NPROCS=2

mpirun -np $NPROCS lmp -in "src/$1"
