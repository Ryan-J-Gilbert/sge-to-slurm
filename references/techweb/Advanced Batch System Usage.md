# Advanced Batch System Usage

## Content

* [Job dependency control](#depend)
* [Submitting Array Jobs](#array)
* [Customize qsub settings with .sge\_request](#sge_request)
* [Job Environment](#jobenv)

## Job dependency control

Out of necessity or for better throughput, an application may spawn a series of batch jobs which may be required to run in a specific order. For these applications, the job dependency can be controlled, in general, with the `qsub -hold_jid` option (see [man qsub](http://scv.bu.edu/cgi-bin/perl/manscript/SCC/qsub/1)). The procedure described below is applicable to both single- and multi-processor batch jobs. Here are two examples:

* **Example 1.** All batch jobs in the group need to run in a specific sequence.

  ```
  scc1$ qsub -N job1 script1
  scc1$ qsub -N job2 -hold_jid job1 script2
  scc1$ qsub -N job3 -hold_jid job2 script3
  ```
* **Example 2.** A designated job must wait until the remaining jobs in the group have completed (aka post-processing).
  In this example, `lastjob` won’t start until `job1, job2,` and `job3` have completed.

  ```
  scc1$ qsub -N job1 script1
  scc1$ qsub -N job2 script2
  scc1$ qsub -N job3 script3
  scc1% qsub -N lastjob -hold_jid "job*" script4
  ```

In both examples, the use of the “`-N`” option to assign job names makes job identification easier as the names of the referenced jobs are known a priori; this is especially helpful in the second example because a wild card (\*) can be used effectively. Note that the above procedures are also applicable to parallel batch jobs (*i.e.* with the `-pe` switch). As an alternative to the manual job-by-job submission shown above (for conceptual demonstration), incorporating all the steps into a script is more practical. For a complete example, visit [Running Multiple Batch Jobs With qsub Array Job Option](https://www.bu.edu/tech/support/research/software-and-programming/common-languages/matlab/matlab-batch#ARRAYJOB).

## Submitting Array Jobs

If you submit many jobs at the same time that are largely identical, you should submit them as array jobs. Array jobs are easier to manage, faster to submit, and they greatly reduce the load on the scheduler. An array job executes multiple independent copies of the same job script. These multiple copies are referred to as “tasks” and are scheduled independently as resources become available, i.e. the tasks are not scheduled all at once. The number of tasks to be executed is set using the `-t start-end[:step]` option to the `qsub` command, where `start` is the index of the first task (it has to be 1 or more, it can not be 0), `end` is the index number of the last task, and `step` is an optional step size (step size defaults to 1 if unspecified). Here’s an example of using this command:

```
scc % qsub -t 1-25 myscript.sh
```

The above command will submit an array job consisting of 25 tasks, numbered from 1 to 25. Since the step size was not specified, the default step size of 1 will be used. Each task will independently execute the `myscript.sh` job file. The batch system sets the `SGE_TASK_ID` environment variable, which can be used inside the script to pass the task ID to the program. Below is an example of how you can utilize that environment variable in the job file:

```
#!/bin/bash -l
# Specify that we will be running an Array job with 25 tasks numbered 1-25
#$ -t 1-25
# Request 1 core for my job
#$ -pe omp 1
# Give a name to my job
#$ -N my_array_job
# Join the output and error streams
#$ -j y

# Run my R script and give it the $SGE_TASK_ID environment
# variable as a command-line argument
Rscript myRfile.R $SGE_TASK_ID
```

There is a more  [advanced example code here](https://www.bu.edu/tech/support/research/system-usage/running-jobs/batch-script-examples/#ARRAY) as well.

When running the `qstat -u  USER_ID`  command to check on the status of the Array job, the running tasks will be listed as separate lines, each with the corresponding task ID visible under the “ja-task-ID” column. All the remaining tasks that are not running, i.e. are queued, will be listed as a single line, their task IDs will be aggregated also under the “ja-task-ID” column (see the code block below, at the far right).

```
[aaly@scc1]$ qstat -u aaly
job-ID  prior   name       user         state submit/start at     queue                          slots ja-task-ID
-----------------------------------------------------------------------------------------------------------------
4960245 0.11489 my_array_j aaly         r     02/25/2021 20:31:37 johnsonlab.q-pub@scc-cb4.scc.b    14 1
4960245 0.11012 my_array_j aaly         r     02/25/2021 20:31:37 saimath-pub@scc-gc4.scc.bu.edu    14 2
4960245 0.10774 my_array_j aaly         r     02/25/2021 20:31:37 saimath-pub@scc-gc4.scc.bu.edu    14 3
4960245 0.10630 my_array_j aaly         r     02/25/2021 20:31:37 montilab-pub@scc-zl4.scc.bu.ed    14 4
4960245 0.10535 my_array_j aaly         r     02/25/2021 20:31:37 montilab-pub@scc-zl4.scc.bu.ed    14 5
4960245 0.10535 my_array_j aaly         r     02/25/2021 20:31:37 boas-pub@scc-x07.scc.bu.edu       14 6
4960245 0.10535 my_array_j aaly         r     02/25/2021 20:31:37 boas-pub@scc-x07.scc.bu.edu       14 7
4960245 0.10535 my_array_j aaly         r     02/25/2021 20:31:37 peloso-pub@scc-tr4.scc.bu.edu     14 8
4960245 0.10535 my_array_j aaly         r     02/25/2021 20:31:37 kolaczyk-pub@scc-ym1.scc.bu.ed    14 9
4960245 0.10535 my_array_j aaly         r     02/25/2021 20:31:37 anderssongroup-pub@scc-zk1.scc    14 10
4960245 0.10535 my_array_j aaly         r     02/25/2021 20:31:37 apolkovnikov-pub@scc-zk2.scc.b    14 11
4960245 0.00000 my_array_j aaly         qw    02/25/2021 20:29:33                                   14 12-25:1
```

In the above output of `qstat` the submitted array job is composed of 25 tasks. Tasks 1-11 are running, and each is listed as a separate entry. Tasks 12-25 are still in the queue waiting to be scheduled; they appear as a single entry.

Notice all the tasks carry the same job “name”; here they are called `my_array_job` (there’s no room to display the entire name in the column, so it is truncated). It is important to give a distinct name to your Array jobs. In addition, it is not recommended to assign a name to the output file using `-o` option in the qsub file. This is because all the tasks will write to the same file.

In the event that an array job was submitted by mistake, simply delete all tasks with:

```

scc1$ qdel job_ID
```

Once the array job has finished, there will an output file for each task that has run. We can execute the `ls` command to see them as below:

```
[aaly@scc1]$ ls
myscript.sh               my_array_job.o4960245.12  my_array_job.o4960245.16  my_array_job.o4960245.2   my_array_job.o4960245.23  my_array_job.o4960245.4  my_array_job.o4960245.8
my_array_job.o4960245.1   my_array_job.o4960245.13  my_array_job.o4960245.17  my_array_job.o4960245.20  my_array_job.o4960245.24  my_array_job.o4960245.5  my_array_job.o4960245.9
my_array_job.o4960245.10  my_array_job.o4960245.14  my_array_job.o4960245.18  my_array_job.o4960245.21  my_array_job.o4960245.25  my_array_job.o4960245.6  myRfile.R
my_array_job.o4960245.11  my_array_job.o4960245.15  my_array_job.o4960245.19  my_array_job.o4960245.22  my_array_job.o4960245.3   my_array_job.o4960245.7
```

By running the `ls` command we see the output files of the array job listed. The output file naming format is `job_name.o&ltjob_id&gt.&lttask_id>`. In the above example, the job name is `my_array_job`, the job id is `4960245`, and the task id is between 1 and 25. Thus, we see the corresponding output file for each task in the Array job.

## Customize qsub with .sge\_request

With the current batch scheduler, a user may create a `.sge_request` file (in their home directory) to customize preferred or frequently used `qsub` settings. These settings will be in effect for all subsequent `qsub` (or `qsh`) batch submissions. Here is what the `.sge_request` file might look like:

```
# .sge_request file must reside in home directory
#
# Send me mail when job gets aborted or ends normally
-m ae

# I want email sent to this email address (instead of default BU email)
-M myname@gmail.com

# I have multiple projects, I want jobs charged to this project
-P projectname
```

Your batch script, `my_batch_script`, need not include those options already defined in `.sge_request`. However, if you do, they will take precedence over those in `.sge_request`. Furthermore, any option that appears on the `qsub` command line input will supersede that which is in `.sge_request` and `my_batch_script`. Here is an example

```
scc1$ qsub -m a -l h_rt=48:00:00 my_batch_script
```

The above batch job will only send email if the job is aborted, not if it ends normally as the `.sge_request` indicated. The combination of the other options specified in the `.sge_request` and on the command line will also take effect.

## Job Environment

A few *pseudo* environment variables are allowed to be used in the path specified with the `-e` and `-o` options:

`$HOME` – home directory on execution machine
`$USER` – user ID of job owner
`$JOB_ID` – current job ID
`$JOB_NAME` – current job name (see -N option)
`$HOSTNAME` – name of the execution host
`$TASK_ID` – array job task index number

This *pseudo* environment variables can only be used for the above scheduler options and cannot be used further in the script. They also should not be confused with the regular environment variables that cannot be used to within scheduler options, but can be used within the script:

`SGE_O_HOST` – the name of the host on which the submitting client is running.
`SGE_TASK_ID` – The index number of the current array job task.
`SGE_TASK_FIRST` – The index number of the first array job task.
`SGE_TASK_LAST` – The index number of the last array job task.
`SGE_TASK_STEPSIZE` – The step size of the array job specification.
`HOME` – The user’s home directory path.
`HOSTNAME` – The hostname of the node on which the job is running.
`JOB_ID` – A unique identifier assigned by the scheduler when the job was submitted.
`JOB_NAME` – The job name.
`NHOSTS` – The number of hosts in use by a parallel job.
`NSLOTS` – The number of queue slots in use by a parallel job.

See the manual of the `qsub` command for the full list of the SGE environment.

Source: https://www.bu.edu/tech/support/research/system-usage/running-jobs/advanced-batch/