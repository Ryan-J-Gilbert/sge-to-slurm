#!/bin/bash -l
#SBATCH --nodes=1
#SBATCH --job-name=example
#SBATCH --account=my_slurm_account
#SBATCH --time=12:00:00
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=user@example.com
#SBATCH --output=out.log
#SBATCH --error=out.log

echo "job ${SLURM_JOB_ID} task ${SLURM_ARRAY_TASK_ID}"
