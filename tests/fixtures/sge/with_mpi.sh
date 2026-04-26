#!/bin/bash
#$ -P my_project
#$ -q short
#$ -pe mpi_28_tasks_per_node 224

mpirun -np $NSLOTS ./app
