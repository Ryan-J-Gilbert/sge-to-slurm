#!/bin/bash -l
#$ -P my_project
#$ -N example
#$ -l h_rt=12:00:00
#$ -j y
#$ -o out.log
#$ -m ea
#$ -M user@example.com

echo "job $JOB_ID task $SGE_TASK_ID"
