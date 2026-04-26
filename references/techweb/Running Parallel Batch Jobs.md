# Running Parallel Batch Jobs

## Content

* [Running *N* single-processor jobs on a compute node with *N* (or more) cores](#single)
* [Running shared-memory multithreaded batch jobs](#mthread)
* [Running an OpenMP program](#openmp)
* [Running an MPI program](#mpi)
* [Parallel Environment resources and time limits](#pe)
* [Running GPU jobs](#gpu)

## Running *N* single-processor jobs on a compute node with *N* (or more) cores

Below is an example batch script which runs 4 programs:

```
#!/bin/bash -l
prog1 < myinput1 > myoutput1 &
prog2 < myinput2 > myoutput2 &
prog3 < myinput3 > myoutput3 &
prog4 < myinput4 > myoutput4 &
wait
```

When you submit your job to the queue, you should request the matching number of processors:

```
scc1$ qsub -pe omp 4  myscript
```

You can run up to N jobs, where N is the number of requested processors (please see accepted values of N for **omp** Parallel Environment (PE) in the table below in the section [Parallel environment resources and time limits](#pe)).

## Running shared-memory multithreaded batch jobs

Multithreaded jobs are, in general, to be submitted to the shared-memory queue using the **omp** (or **smp** ) PE. Applications belonging to this category include any jobs using multiple processors on a single node, such as MATLAB, pthreads, Stata, and OpenMP.

```
scc1$ qsub -pe omp 4 -b y a.out
```

The PE command line option (*i.e.,* `-pe omp 4` , or equivalently*,* `-pe smp 4`) lets you request resources with the batch scheduler; you are still responsible for making sure that the proper number of threads is specified for the underlying parallel paradigm.

## Running an OpenMP program

Use the **omp** PE to run OpenMP applications. There are a couple of ways to define the number of processors required by an OpenMP application:

1. The number of threads is set by the function `omp_set_num_threads` in the source code and then the executable is submitted with the `qsub` command requesting the matching number of threads:

   ```
   scc1$ qsub -pe omp 4 -b y a.out
   ```
2. The most convenient way is to set the `OMP_NUM_THREADS` environment variable inside a job script. The number of requested cores for a job is stored in the environment variable `NSLOTS`, so within a job script these can be used together:

   ```
   #!/bin/bash -l
   #$ -pe omp 8
   export OMP_NUM_THREADS=$NSLOTS
   your_prog ...args...
   ```
3. The environment variable `OMP_NUM_THREADS` is set prior to the job submission and then passed to the `qsub` command using the `-V` option:

   ```
   scc1$ export OMP_NUM_THREADS=4
   scc1$ qsub -pe omp 4 -V -b y a.out
   ```
4. The environment variable `OMP_NUM_THREADS` is passed through the `qsub` command:

   ```
   scc1$ qsub -pe omp 4 -v OMP_NUM_THREADS=4 -b y a.out
   ```

## Running an MPI program

MPI jobs should be submitted with the PE option appropriately set to request the desired number of processors needed for the job. The following is an example of an abbreviated batch script for the MPI job submission:

```
#!/bin/bash -l
#
#$ -pe mpi_28_tasks_per_node 56
#
# Invoke mpirun.
# SGE sets $NSLOTS as the total number of processors (32 for this example)
#
module load openmpi/4.1.5
mpirun -np $NSLOTS ./mpi_program arg1 arg2 ...
```

See the [programming](https://www.bu.edu/tech/support/research/software-and-programming/programming/multiprocessor/#MPI/) page for information on how to compile MPI programs.

#### Full version of a sample MPI script

```
#!/bin/bash -l
#
# Sample SGE script for running mpi jobs on Boston University's SCC
#
# How to use this script: qsub mpi_batch_script
#
# Note: A line of the form "#$ qsub_option" is interpreted
#       by qsub as if "qsub_option" was passed to qsub on
#       the command line.
#
# Set the hard runtime (aka wallclock) limit for this job,
# default is 12 hours. Format: -l h_rt=HH:MM:SS
#$ -l h_rt=24:00:00
#
# Invoke the mpi Parallel Environment for N processors.
# There is no default value for N, it must be specified.
# -pe parallel-environment N
#$ -pe mpi_28_tasks_per_node 56

# Merge stderr into the stdout file, to reduce clutter.
#$ -j y

# Have the system send you mail when your job is aborted or ends
#$ -m ae

## end of qsub options

# openmpi is the standard MPI library
module load openmpi/4.1.5
# By default, the script is executed in the directory from which
# it was submitted with qsub. You can change directory ...
# cd somewhere

# The NSLOTS variable is set by SGE to the number of processors requested
# with the "-pe" option. Use it with mpirun to avoid inconsistency

# Most common usage
mpirun -np $NSLOTS ./mpi_program

# Use the following if your executable requires input arguments
#mpirun -np $NSLOTS ./mpi_program arg1 arg2 ...

# You can use fewer cores if needed, for example to run 8
# processes on 2 28-core nodes use the ppr "process per resource"
# to run 4 tasks per node. Each compute node has dual CPU sockets
# so run 2 tasks per socket:
# -pe mpi_28_tasks_per_node 56
# 2 nodes, 4 procs per node, 8 total.
# mpirun --map-by ppr:2:socket ./mpi_program
```

## Parallel Environment (PE) resources and time limits

Table 2. The *-pe* parallel environment.

| parallel-environment | Purpose | Allocation Rule | values of *N* | Maximum runtime |
| --- | --- | --- | --- | --- |
| omp (or smp) | Multiple processors on a single node | All *N* requested processors on a single node  (node may be shared with other jobs) | 1, 2, 3, …, 28; 36 | 720 hrs |
| mpi\_64\_tasks\_per\_node | MPI | Whole 64-processor node(s) | **128**,…, 1024 | 120 hrs |
| mpi\_28\_tasks\_per\_node | MPI | Whole 28-processor node(s) | 28,56,84, …, 448 | 120 hrs |

* + The **omp** PE is primarily intended for any jobs using multiple processors on a single node. The value of N can be set to any number between 1 and 28 and can also be set to 36. Use N=36 is to request a very large-memory (1024 GB) node. To make best use of available resources on the SCC, the optimal choices are N=1, 4, 8, 16, 28, 32, or 36.
  + The **mpi\_64\_tasks\_per\_node** PE can be used for N as a multiple of 64. This leads to allocations of whole 64-processor nodes. For jobs sensitive to memory availability, this PE will guaranteed the maximum memory promised for each assigned node. In addition, because intra-node communication is usually more efficient than inter-node communication, this PE might provide better overall performance. The maximum N is 1024 (that is 16 nodes). The maximum runtime is 120 hours for multiple nodes. Note there is a minimum of 2 nodes (N=128) for this PE.
  + The **mpi\_28\_tasks\_per\_node** PE can be used for N as a multiple of 28. This leads to allocations of whole 28-processor nodes. For jobs sensitive to memory availability, this PE will guaranteed the maximum memory promised for each assigned node. In addition, because intra-node communication is usually more efficient than inter-node communication, this PE might provide better overall performance. The maximum N is 448 (that is 16 nodes). The maximum runtime is 120 hours for multiple nodes (N>=56), while it is 720 hours for a single node (N=28).

* If your application can run on multiple nodes but doesn’t use MPI you will need a specialized PE. Send mail to help@scc.bu.edu and we’ll create an appropriate PE for you.

## Running GPU jobs

Access to GPU enabled nodes is via the batch system (qsub/qsh/qrsh/qlogin). The GPU enabled nodes support all of the standard batch options in addition to the [GPU specific options](https://www.bu.edu/tech/support/research/software-and-programming/programming/multiprocessor/gpu-computing/#RUNNINGONGPUS).

Source: https://www.bu.edu/tech/support/research/system-usage/running-jobs/parallel-batch/