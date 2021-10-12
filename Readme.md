This is a WIP tool to capture the peak memory usage of a full process tree using BPF and cgroups. The original intention is to record the memory usage of everything that happens when you do a `make -j` for instance.

# memtrace


This is some initial testing I've done.

What I've discovered is that in the BPF program, `curtask->mm->total_vm * 4K` corresponds to what `/proc/<pid>/status` reports for `VmPeak`. Which is slightly weird because looking at [the source](https://github.com/torvalds/linux/blob/f6274b06e326d8471cdfb52595f989a90f5e888f/fs/proc/task_mmu.c#L59) there is no multiplication going on or counting in page sizes.

I'm also currently missing an `exec` log of `a.out` by `time`.

```
→ gcc allocatealot.c

→ ./memtrace.py bash -c '/usr/bin/time --verbose ./a.out 100000000'
Running scope as unit: memtrace1634001647.scope
/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/memtrace1634001647.scope
Running in /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/memtrace1634001647.scope
# this is output by a.out from /proc/self/exe
Name:	a.out
Umask:	0022
State:	R (running)
Tgid:	710930
Ngid:	0
Pid:	710930
PPid:	710929
TracerPid:	0
Uid:	1000	1000	1000	1000
Gid:	1000	1000	1000	1000
FDSize:	64
Groups:	10 18 973 984 1000
NStgid:	710930
NSpid:	710930
NSpgid:	710909
NSsid:	583493
VmPeak:	  100004 kB
VmSize:	  100004 kB
VmLck:	       0 kB
VmPin:	       0 kB
VmHWM:	   98780 kB
VmRSS:	   98780 kB
RssAnon:	   97744 kB
RssFile:	    1036 kB
RssShmem:	       0 kB
VmData:	   97848 kB
VmStk:	     132 kB
VmExe:	       4 kB
VmLib:	    1480 kB
VmPTE:	     232 kB
VmSwap:	       0 kB
HugetlbPages:	       0 kB
CoreDumping:	0
THP_enabled:	1
Threads:	1
SigQ:	1/63277
SigPnd:	0000000000000000
ShdPnd:	0000000000000000
SigBlk:	0000000000000000
SigIgn:	0000000000000000
SigCgt:	0000000000000000
CapInh:	0000000000000000
CapPrm:	0000000000000000
CapEff:	0000000000000000
CapBnd:	000001ffffffffff
CapAmb:	0000000000000000
NoNewPrivs:	0
Seccomp:	0
Seccomp_filters:	0
Speculation_Store_Bypass:	thread vulnerable
SpeculationIndirectBranch:	conditional enabled
Cpus_allowed:�����
# This is a.out giving us its own pid and ppid
a.out pid=710930 ppid=710929
# This is /usr/bin/time --verbose output
	Command being timed: "./a.out 100000000"
	User time (seconds): 0.19
	System time (seconds): 0.04
	Percent of CPU this job got: 98%
	Elapsed (wall clock) time (h:mm:ss or m:ss): 0:00.24
	Average shared text size (kbytes): 0
	Average unshared data size (kbytes): 0
	Average stack size (kbytes): 0
	Average total size (kbytes): 0
	Maximum resident set size (kbytes): 99104
	Average resident set size (kbytes): 0
	Major (requiring I/O) page faults: 0
	Minor (reclaiming a frame) page faults: 48894
	Voluntary context switches: 1
	Involuntary context switches: 23
	Swaps: 0
	File system inputs: 0
	File system outputs: 0
	Socket messages sent: 0
	Socket messages received: 0
	Signals delivered: 0
	Page size (bytes): 4096
	Exit status: 0
# This is the captured bpftrace output
Attaching 5 probes...
379483771095321 sched 710909 710929
379483771459990 exec  python3 710929 | bash -c /usr/bin/time --verbose ./a.out 100000000
379483771674126 exec  python3 710929 | bash -c /usr/bin/time --verbose ./a.out 100000000
379483771860133 exec  python3 710929 | bash -c /usr/bin/time --verbose ./a.out 100000000
379483772028720 exec  python3 710929 | bash -c /usr/bin/time --verbose ./a.out 100000000
379483773528058 exec  bash 710929 | /usr/bin/time --verbose ./a.out 100000000
379483774044888 sched 710929 710930
379483774116545 exec  time 710930 | ./a.out 100000000
379484017424731 exit  a.out pid=710930 ppid=710929 start=379483774037717 rss=95 vm=600 total_vm=25001
379484022060702 exit  time pid=710929 ppid=710909 start=379483771085377 rss=102 vm=603 total_vm=589

# this is from metrace.py diagnostic info
bpftrace.pid=710923
python3 pid=710909 ppid=583493
```
