# Batch Script Examples

## Content

* [Basic Batch Script](#BASIC)
* [Batch Script With Frequently Used Options](#FREQUENT)
* [Large Memory Jobs](#MEMORY)
* [Array Job Script](#ARRAY)
* [Basic Parallel Job (Single Node)](#OMP)
* [MPI Job Script](#MPI)
* [GPU Job Script](#GPU)
* [Use Own Buy-in Compute Nodes](#BUYIN)
* [Using the Data Transfer Node to transfer files to the SCC (separate web page)](https://www.bu.edu/tech/support/research/system-usage/transferring-files/cloud-applications/#DTN)

## Basic Batch Script[🔗](#BASIC)

Here is an example of a basic script for the Shared Computing Cluster (SCC). The first line in the script specifies the interpreter – shell. Lines that start with #$ symbols are used to specify the Sun Grid Engine (SGE) options used by the `qsub` command. All other lines that start with the # symbol are comments that provide details for each option. The program and its optional input arguments are at the end of the script, preceded by a module statement if needed. If the `module` command is used in the script the first line should contain the “-l” option to ensure proper command interpretation by the system. See [General job submission directives](https://www.bu.edu/tech/support/research/system-usage/running-jobs/submitting-jobs/#job-options) for a list of other SGE options.

```
#!/bin/bash -l

# Set SCC project
#$ -P my_project

# Specify hard time limit for the job.
#   The job will be aborted if it runs longer than this time.
#   The default time, also selected here, is 12 hours.  You can increase this up to 720:00:00 for single processor jobs but your job will take longer to start.
#$ -l h_rt=12:00:00

module load python3/3.13.8
python -V
```

## Batch Script With Frequently Used Options[🔗](#FREQUENT)

Here is an example of a script with frequently used options:

```
#!/bin/bash -l

# Set SCC project
#$ -P my_project

# Specify hard time limit for the job.
#   The job will be aborted if it runs longer than this time.
#   The default time is 12 hours
#$ -l h_rt=12:00:00

# Send an email when the job finishes or if it is aborted (by default no email is sent).
#$ -m ea

# Give job a name
#$ -N example

# Combine output and error files into a single file
#$ -j y

# Keep track of information related to the current job
echo "=========================================================="
echo "Start date : $(date)"
echo "Job name : $JOB_NAME"
echo "Job ID : $JOB_ID  $SGE_TASK_ID"
echo "=========================================================="

module load python3/3.13.8
python -V
```

## Large Memory Jobs[🔗](#MEMORY)

Jobs requiring **more than 4 GB of memory** should include appropriate qsub options for the amount of memory needed for your job.

The SCC has a variety of nodes, each with a different number of cores along with varying amounts of memory. Jobs that require up to 64 GB can share memory resources on the same node. Jobs that require more than 64 GB need to request a whole node. The `qsub` options in the table below will schedule your job to a node with enough resources to complete your job. The [Technical Summary](https://www.bu.edu/tech/support/research/computing-resources/tech-summary/) page describes the configuration of the different types of nodes on the SCC. For more information about available processing and memory resources, visit our  [Resources Available for your Jobs](https://www.bu.edu/tech/support/research/system-usage/running-jobs/resources-jobs/#memory) page.

The table below gives suggestions for appropriate qsub options for different ranges of memory your job may need. See our [Allocating Memory for your Job](https://www.bu.edu/tech/support/research/system-usage/running-jobs/allocating-memory-for-your-job/) webpage to estimate the amount of memory your job requires.

|  |  |  |  |
| --- | --- | --- | --- |
| Requesting Node Resources | | | |
| Job Resource Requirements | | | `qsub` Options |
|  |  |  |  |
| --- | --- | --- | --- |
| **Partial Node** | **≤ 16 GB** | Request **4** **cores.** | **-pe omp** *4* |
| **≤ 32 GB** | Request **8** **cores.** | **-pe omp** *8* |
| **≤ 64 GB** | Request **8 cores** on a machine with at least 128 GB of RAM. | **-pe omp** *8*  **-l mem\_per\_core**=*8G* |
| **Whole Node** | **≤ 128 GB** | Request a whole node with **16 cores** and at least **128 GB** of RAM. | **-pe omp** *16* |
| **≤ 192 GB** | Request a whole node with **28 cores** and at least **192 GB** of RAM. | **-pe omp** *28* |
| **≤ 256 GB** | Request a whole node with **16 cores** and at least **256 GB** of RAM. | **-pe omp** *16*  **-l mem\_per\_core**=*16G* |
| Request a whole node with **28 cores** and at least **256 GB** of RAM. | **-pe omp** *28*  **-l mem\_per\_core**=*9G* |
| **≤ 384 GB** | Request a whole node with **28 cores** and at least **384 GB** of RAM. | **-pe omp** *28*  **-l mem\_per\_core**=*13G* |
| **≤ 512 GB** | Request a whole node with **28 cores** and at least **512 GB** of RAM. | **-pe omp** *28*  **-l mem\_per\_core**=*18G* |
| **≤ 1 TB** | Request a whole node with **36 cores** and at least **1 TB** of RAM. | **-pe omp** *36* |

To request large memory resources in OnDemand, add the appropriate **qsub** options from the summary table above to the *Extra qsub options* text field in the OnDemand form. Below is an example of requesting a node with at least 512 GB of memory:

![](/tech/files/2021/11/ondemand_large_memory_job-1-636x93.png)

An example batch script for a job that requires 500 GB of RAM:

```
#!/bin/bash -l

# Set SCC project
#$ -P my_project

# Request a whole 28 processor node with at least 512 GB of RAM
#$ -pe omp 28
#$ -l mem_per_core=18G

module load python3/3.13.8
python -V
```

## Array Job Script[🔗](#ARRAY)

If you submit many jobs at the same time that are largely identical, you can submit them as an array job. Array jobs are easier to manage, faster to submit, and they greatly reduce the load on the scheduler.

For example, if you have many different input files, but want to run the same program on all of them, you can use an array job with a single script:

```
#!/bin/bash -l

# Set SCC project
#$ -P my_project

# Submit an array job with 3 tasks
#$ -t 1-3

# Get all csv files in current directory, select the one that correspond to the task ID and pass it to the program
inputs=($(ls *.csv))
taskinput=${inputs[$(($SGE_TASK_ID-1))]}

./my_program $taskinput
```

Within your code, you can query the task ID using the appropriate function. Below are some common examples in Python, R, and MATLAB:

```

# Python
import os
id = os.getenv('SGE_TASK_ID')

# R
id <- as.numeric(Sys.getenv("SGE_TASK_ID"))

% MATLAB
id = str2num(getenv('SGE_TASK_ID'));

```

## Basic Parallel Job (Single Node)[🔗](#OMP)

Below is a basic example of a script that requests a parallel environment for a multi-threaded or multi-processor job on a single node. You can request up to 36 cores for your parallel jobs. We recommend that you request 1,2,3,4,8,16,28, or 36. Requesting other numbers of cores might result in a longer waiting time in the queue. (Note: some buy-in nodes have 20 or 32 core machines)

```
#!/bin/bash -l

# Set SCC project
#$ -P my_project

# Request a parallel environment with 8 cores
#$ -pe omp 8

# When a parallel environment is requested the environment variable NSLOTS is set to the number of cores requested. This variable can be used within a program to setup an appropriate number of threads or processors to use.
# For example, some programs rely on the environment variable OMP_NUM_THREADS for parallelization:
OMP_NUM_THREADS=$NSLOTS

./my_program input_args
```

Within your code, you can query how many cores your script requested from the batch system. Below are some common examples in Python, R, and MATLAB:

```

# Python
import os
ncores = os.getenv('NSLOTS')

# R
ncores <- as.numeric(Sys.getenv("NSLOTS"))

% MATLAB
ncores = str2num(getenv('NSLOTS'));

```

## MPI Job Script[🔗](#MPI)

The SCC has 3 sets of nodes dedicated to run MPI jobs. One set has 16-core nodes with 128 GB each, connected by 56 GB/s FDR Infiniband. The second set has 36 nodes with 256GB each connected by 100 GB/s EDR Infiniband.  The third set has 36 nodes with 28 CPU cores with 192 GB of memory each, connected by 100 GB/s EDR Infiniband. You can request up to 256 cores on the 16-core nodes and up to 448 cores on the 28-core nodes. For multi-node MPI jobs the time limit is 120 hours (5 days). Below is an example of a script running an MPI job on 28-core nodes:

```
#!/bin/bash -l

# Set SCC project
#$ -P my_project

# Request 8 nodes with 28 core each
#$ -pe mpi_28_tasks_per_node 224

# When a parallel environment is requested the environment variable NSLOTS is set to the number of cores requested. This variable can then be used to set up the total number of processors used by the MPI job:
mpirun -np $NSLOTS ./my_mpi_program input_args
```

## GPU Job Script[🔗](#GPU)

There are several types of GPU cards available on the SCC. Each has its own compute capability and amount of memory.  It is important to know the compute capability and memory requirements of your program and request appropriate GPUs.  You can view a list of GPUs available on the SCC by executing `qgpus` command in a terminal window. For a detailed list, run `qgpus -v`.  For more information on GPU job options see the [GPU computing](https://www.bu.edu/tech/support/research/software-and-programming/programming/multiprocessor/gpu-computing/) page.

When you use `-l gpu_c` flag to specify a compute capability, your job will be assigned a node with a GPU that has *at least* the capability that you requested. For example, for `-l gpu_c=6.0`, you may get a GPU that has 6.0, 7.0, or higher compute capability:

```
#!/bin/bash -l

# Set SCC project
#$ -P my_project

# Request 4 CPUs
#$ -pe omp 4

# Request 1 GPU
#$ -l gpus=1

# Specify the minimum GPU compute capability.
#$ -l gpu_c=7.0

# As an example, use the academic-ml module to get Python with machine learning.
module load miniconda
module load academic-ml/fall-2025
conda activate fall-2025-pyt
python my_pytorch_prog.py
```

## Use Own Buy-in Compute Nodes[🔗](#BUYIN)

Those people who are members of projects that have access to Buy-in Compute Group hardware can restrict their jobs to running on that hardware only. Doing this can significantly increase the wait time before your job starts running but will guarantee that your job is not charged any [SUs](https://www.bu.edu/tech/support/research/account-management/manage-project/#SUS). This option is only available if you submit the job under a project (`-P project`) that has access to [Buy-in](https://www.bu.edu/tech/support/research/computing-resources/service-models/buy-in/) resources. Your monthly report, received on the 3rd of each month, tells you if the projects you belong to have access to any Buy-in Compute resources.

An alternative way to do this, if you know the name of the **queue** associated with the Buy-in Compute Group that you want to use, is to use the “`-q queuename`” option to `qsub` but the method below is simpler and will let you run on any appropriate Buy-in queue you have access to.

If you try to do either of these commands under a project that does not have access to Buy-in Compute group hardware of any sort you will get an error like “`Unable to run job: error: no suitable queues.`” and your job **will not be scheduled**.

```
#!/bin/bash -l

# Set SCC project
#$ -P my_project

# Request my job to run on Buy-in Compute group hardware my_project has access to
#$ -l buyin

# Specify hard time limit for the job.
#   The job will be aborted if it runs longer than this time.
#   The default time is 12 hours
#$ -l h_rt=12:00:00

# Actual commands to run.  Change this appropriately for your codes.
module load python3/3.13.8
python -V
```

Source: https://www.bu.edu/tech/support/research/system-usage/running-jobs/batch-script-examples/