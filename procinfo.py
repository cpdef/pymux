#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re


class ProcessInfo(object):


    def __init__(self):
        self.update()
        

    def update(self):
        processes = [int(entry) for entry in os.listdir("/proc") if entry.isdigit()]
        parent = {}
        children = {}
        commands = {}
        for pid in processes:
            try:
                f = open("/proc/{}/stat".format(pid))
            except IOError:
                continue
            stat = f.read().split()
            f.close()
            cmd = stat[1]
            try:
                ppid = int(stat[3])
            except ValueError:
                ppid = int(hash(stat[3])) # 'S'
            parent[pid] = ppid
            children.setdefault(ppid, []).append(pid)
            commands[pid] = cmd
        self.parent = parent
        self.children = children
        self.commands = commands
        

    def all_children(self, pid):
        cl = self.children.get(pid, [])[:]
        #print(cl)
        for child_pid in cl:
            cl.extend(self.all_children(child_pid))
        return cl


    def dump(self, pid, _depth=0):
        print(" " * (_depth*2), pid, self.commands[pid])
        for child_pid in self.children.get(pid, []):
            self.dump(child_pid, _depth+1)


    def cwd(self, pid):
        try:
            path = os.readlink("/proc/{}/cwd".format(pid))
        except OSError:
            return
        return path

    def get_stat(self, pid): 
        try:         
            f = open("/proc/{}/stat".format(pid))
            stat = f.read().split()
        except IOError:
            return
        except ProcessLookupError:
            return
        return stat

    def get_cmdline(self, pid):
        try:
            f = open("/proc/{}/cmdline".format(pid), 'rb') 
        except IOError:
            return
        cmdline = f.read()
        cmdline = cmdline.replace(b'\x00', b' ')
        return cmdline.decode('utf-8')


if __name__ == "__main__":
    pid = 1
    pi = ProcessInfo()
    pi.update()
    #pi.dump(8122)
    children = pi.all_children(0)

    print(pi.cwd(1))
