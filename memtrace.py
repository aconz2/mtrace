#!/usr/bin/env python3

import subprocess
import random
import sys
import argparse
import os
import re
import tempfile
import time

def rerun_in_systemd(rest, properties={}):
    env = dict(os.environ)
    env['MEMTRACE_IN_SYSTEMD'] = '1'
    args = [
        '--quiet',
        '--collect',
        '--user',
        '--scope',
        # '--unit', 'memtrace',  # TODO these arent getting cleaned up
        '--unit', 'memtrace' + str(int(time.time())),
    ]
    for k, v in properties.items():
        args.extend(('--property', f'{k}={v}'))

    args.extend(('python3', __file__))
    args.extend(rest)

    os.execvpe('systemd-run', args, env)

cgroup_fs_prefix = '/sys/fs/cgroup'

# Why is there a double colon in some?
# 1:net_cls:/
# 0::/
def parse_cgroup_line(line):
    """returns (number, middle ns name (?), path)"""
    return re.search(r'(\d+):(\w*):(.+)', line).groups()

def get_cgroups():
    with open('/proc/self/cgroup') as fh:
        return list(map(parse_cgroup_line, fh))

def find_memtrace_cgroup(cgroups):
    for _, _, path in cgroups:
        if 'memtrace' in path:
            return cgroup_fs_prefix + path
    raise KeyError('missing unit named `memtrace`')

# anything in /proc/<pid>/status is racing the kernel since cat happens in userspace
    # cat("/proc/%d/status", pid);
    # printf("---\n");
    # cat("/proc/%d/cmdline", curtask->pid);
    # printf("---\n");

# exit* covers exit and exit_group
# execve* covers execve and execveat
def run_bpf(cgroup):
    prog = r'''
    tracepoint:syscalls:sys_enter_exit* /cgroup == cgroupid("MYCGROUP")/ {
      printf("%lu exit  %s pid=%d ppid=%d start=%lu ", nsecs, comm, curtask->pid, curtask->real_parent->pid, curtask->start_time);
      printf("rss=%lu vm=%lu total_vm=%lu\n", curtask->mm->hiwater_rss, curtask->mm->hiwater_vm, curtask->mm->total_vm);
    }
    tracepoint:syscalls:sys_enter_execve* /cgroup == cgroupid("MYCGROUP")/ { printf("%lu exec  %s %d | ", nsecs, comm, curtask->pid); join(args->argv); }
    tracepoint:sched:sched_process_fork /cgroup == cgroupid("MYCGROUP")/ { printf("%lu sched %d %d\n", nsecs, args->parent_pid, args->child_pid); }
    '''.replace('\n', ' ').replace('MYCGROUP', cgroup)
    print('Running in', cgroup)

    with tempfile.TemporaryFile('w+') as tf:
        bpftrace = subprocess.Popen(
            ['sudo', 'bpftrace', '--btf', '-e', prog],
            stdout=tf,
        )

        # # I think this is an okay thing to do with the file object without dup-ing
        while True:
            tf.seek(0)
            line = tf.readline()
            if line.startswith('Attaching'):
                break
            time.sleep(0.1)

        proc = subprocess.Popen(sys.argv[1:])
        proc.wait()
        time.sleep(0.1)

        bpftrace.kill()

        tf.seek(0)
        data = tf.read()
        print(data)

        print(f'bpftrace.pid={bpftrace.pid}')
        print(f'python3 pid={os.getpid()} ppid={os.getppid()}')

if __name__ == '__main__':

    if os.getenv('MEMTRACE_IN_SYSTEMD'):
        memtrace_cgroup = find_memtrace_cgroup((get_cgroups()))
        print(memtrace_cgroup)
        run_bpf(memtrace_cgroup)

    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('--memory-limit', default=None)
        parser.add_argument('--memory-high', default=None)
        parser.add_argument('--memory-swap', default=None)
        args, rest = parser.parse_known_args()

        params = {}
        if args.memory_limit: params['MemoryLimit'] = args.memory_limit
        if args.memory_high:  params['MemoryHigh']  = args.memory_high
        if args.memory_swap:  params['MemorySwap']  = args.memory_swap

        rerun_in_systemd(rest, params)
