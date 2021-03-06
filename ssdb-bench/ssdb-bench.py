#!/usr/bin/env python
#coding: utf-8
#file   : bench.py
#author : ning
#date   : 2014-05-18 20:45:10


import os
import re
import sys
import time
import copy
import threading
import logging
import commands
import psutil
import json

from pcl import common
from subprocess import Popen, PIPE

PWD = os.path.dirname(os.path.realpath(__file__))
WORKDIR = os.path.join(PWD,  '../')
LOGPATH = os.path.join(WORKDIR, 'log/bench.log')

sys.path.append(os.path.join(WORKDIR, 'lib/'))

from bench_conf import *

g_qps = 0
g_stat = {}

class LoadThread(threading.Thread):
    def run(self):
        global g_qps
        num = 1000000000
        #num = 100000
        cmd = 'redis-benchmark  -p 8888 -t set -n %s -r 100000000000 -d 100' % num
        p = Popen(cmd, shell=True, stdout=PIPE, bufsize=1024)

        for line in iter(lambda: p.stdout.readline(), ''):
            line = str(line).strip()
            #print(">>> " + line)
            if line.startswith('SET'):
                g_qps = line.split()[1]

        cmd = 'redis-benchmark  -p 8888 -t get -n %s -r 100000000000 -d 100' % num
        p = Popen(cmd, shell=True, stdout=PIPE, bufsize=1024)
        for line in iter(lambda: p.stdout.readline(), ''):
            line = str(line).strip()
            #print(">>> " + line)
            if line.startswith('GET'):
                g_qps = line.split()[1]

class IoStatThread(threading.Thread):
    def run(self):
        global g_stat
        while True:
            g_stat = IoStatThread.call_iostat(DEV, INTERVAL)

    @staticmethod
    def call_iostat(dev, interval):
        cmd = 'iostat -kxt %d 2' % interval
        out = commands.getoutput(cmd)
        lines = out.split('\n')
        lines.reverse()

        def line_to_dict(line):
            #Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
            fields = line.split()

            stat = {}
            stat['rrqm/s']   = fields[1]
            stat['wrqm/s']   = fields[2]
            stat['r/s']      = fields[3]
            stat['w/s']      = fields[4]
            stat['rkB/s']    = fields[5]
            stat['wkB/s']    = fields[6]

            stat['avgrq-sz'] = fields[7]
            stat['avqqu-sz'] = fields[8]

            stat['await']    = fields[9]
            stat['svctm']    = fields[10]
            stat['util']     = fields[11]
            return stat

        for line in lines:
            if line.startswith(dev):
                return line_to_dict(line)

def get_disk_usage(path):
    cmd = 'du -s %s' % path
    out = commands.getoutput(cmd)
    return int(out.split()[0])

def get_proc(proc_name):
    for proc in psutil.process_iter():
        if common.strstr(proc.name(), proc_name):
            return proc

def my_json_encode(j):
    return json.dumps(j, cls=common.MyEncoder)

proc = get_proc(PROC)
def dostat():
    global g_stat
    g_stat['qps'] = g_qps
    g_stat['ts'] = time.time()
    g_stat['du'] = get_disk_usage(DATA_DIR)
    g_stat['cpu'] = proc.get_cpu_percent(interval=1)
    g_stat['mem-rss'] = proc.get_memory_info().rss
    g_stat['mem-vms'] = proc.get_memory_info().vms
    #print g_stat

    fout = file('stat.log', 'a+')
    print >> fout, my_json_encode(g_stat)
    fout.close()

class StatThread(threading.Thread):
    def run(self):
        while True:
            try:
                dostat()
                time.sleep(INTERVAL)
            except Exception, e:
                print time.time(), 'got Exception:', e

def main():
    """docstring for main"""
    common.system('rm stat.log')
    fout = file('stat.log', 'a+')
    print >> fout, 'benchmark start!!!!!!!!!!!!!!!!!!!!!!!!'
    fout.close()

    logging.debug(PWD)
    LoadThread().start()
    IoStatThread().start()

    StatThread().start()

if __name__ == "__main__":
    main()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
