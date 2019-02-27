#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Author: Jan Mach <jan.mach@cesnet.cz>
# Copyright (C) since 2016 CESNET, z.s.p.o (http://www.ces.net/)
# Use of this source is governed by the MIT license, see LICENSE file.
#-------------------------------------------------------------------------------


"""
Utility script for generating environment statistics data file.
"""


__version__ = "1.0"
__author__  = "Jan Mach <jan.mach@cesnet.cz>"


import os
import re
import json
import pprint
import argparse
import subprocess


VERBOSE = 0


def verbose_print(msg, level = 1):
    """
    Print given message, but only in case global ``VERBOSE`` flag is set.
    """
    global VERBOSE
    if VERBOSE >= level:
        print(msg)


#-------------------------------------------------------------------------------

def statistics_python():
    """
    Detect statistics for current version of Python.
    """
    output = subprocess.check_output('python3 -V', shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    return output.strip()

def statistics_pip():
    """
    Detect statistics for currently installed Python libraries.
    """
    ptrn = re.compile('([^ ]+) \((.+)\)')
    output = subprocess.check_output('pip list', shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    lines = output.split("\n")
    result = {}
    for l in lines:
        l = l.strip()
        m = ptrn.match(l)
        if m:
            result[m.group(1)] = m.group(2)
    return result

def statistics_system():
    """
    Detect system statistics.
    """
    result = {}
    output = subprocess.check_output('uname -o', shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    result['operating-system'] = output.strip()

    output = subprocess.check_output('uname -r', shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    result['kernel-release'] = output.strip()

    output = subprocess.check_output('uname -v', shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    result['kernel-version'] = output.strip()

    output = subprocess.check_output('uname -m', shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    result['machine'] = output.strip()

    ptrn = re.compile('PRETTY_NAME="([^"]+)"')
    output = subprocess.check_output('cat /etc/os-release', shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    lines = output.split("\n")
    for l in lines:
        l = l.strip()
        m = ptrn.match(l)
        if m:
            result['os-release'] = m.group(1)
    return result

#-------------------------------------------------------------------------------


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                description = 'Generate project statistics for given project'
            )

    # Positional mandatory arguments.
    parser.add_argument('target', type=str, help='name of the target file')

    # Optional arguments.
    parser.add_argument('--verbose', '-v', default=0,     action='count',      help='increase output verbosity')
    parser.add_argument('--force',   '-f', default=False, action='store_true', help='overwrite existing files')

    args = parser.parse_args()

    #---------------------------------------------------------------------------

    VERBOSE = args.verbose

    verbose_print("Using target statistics file: '{}'".format(args.target))

    stats = {}
    stats['python'] = statistics_python()
    stats['pip']    = statistics_pip()
    stats['system'] = statistics_system()

    verbose_print("Detected build environment statistics:")
    verbose_print(pprint.pformat(stats))

    if args.force or not os.path.isfile(args.target):
        with open(args.target, "w") as fh:
            json.dump(stats, fh)
        verbose_print("Written statistics to target file: '{}'".format(args.target))
    else:
        verbose_print("Target statistics file already exists: '{}'".format(args.target))
