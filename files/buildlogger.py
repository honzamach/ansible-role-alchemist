#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Author: Jan Mach <jan.mach@cesnet.cz>
# Copyright (C) since 2016 CESNET, z.s.p.o (http://www.ces.net/)
# Use of this source is governed by the MIT license, see LICENSE file.
#-------------------------------------------------------------------------------


"""
...
"""


__version__ = "1.0"
__author__  = "Jan Mach <jan.mach@cesnet.cz>"


import os
import time
import datetime
import json
import argparse


VERBOSE = 0


def verbose_print(msg, level = 1):
    """
    Print given message, but only in case global ``VERBOSE`` flag is set.
    """
    global VERBOSE
    if VERBOSE >= level:
        print(msg)


#-------------------------------------------------------------------------------

def load_buildlog(logfile):
    """
    Load given buildlog file.
    """
    try:
        with open(logfile, "r") as lfh:
            return json.load(lfh)
    except FileNotFoundError:
        return {}

def save_buildlog(logfile, buildlog):
    """
    Save given buildlog into file.
    """
    with open(logfile, "w") as lfh:
        json.dump(buildlog, lfh)

#-------------------------------------------------------------------------------


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                description = 'Generate project statistics for given project'
            )

    # Positional mandatory arguments.
    parser.add_argument('projectdir', type=str, help='path to project directory')

    # Optional arguments.
    parser.add_argument('--verbose', '-v', default=0, action='count', help='increase output verbosity')

    # Named mandatory arguments
    parser.add_argument('--codename',    required=True, type=str, help='codename')
    parser.add_argument('--gpgkey',      required=True, type=str, help='gpgkey')
    parser.add_argument('--suite',       required=True, type=str, help='suite')
    parser.add_argument('--version',     required=True, type=str, help='version')
    parser.add_argument('--project',     required=True, type=str, help='project')
    parser.add_argument('--branch',      required=True, type=str, help='branch')
    parser.add_argument('--revision',    required=True, type=str, help='revision')
    parser.add_argument('--buildername', required=True, type=str, help='buildername')
    parser.add_argument('--buildnumber', required=True, type=int, help='buildnumber')

    args = parser.parse_args()

    #---------------------------------------------------------------------------

    VERBOSE = args.verbose

    verbose_print("Processing project directory: '{}'".format(args.projectdir))

    buildlog_file = os.path.join(args.projectdir, '.buildlog.json')

    buildlog = load_buildlog(buildlog_file)
    if not args.codename in buildlog:
        buildlog[args.codename] = []

    curt = time.time()
    record = {
        'ts':          curt,
        'datetime':    str(datetime.datetime.utcfromtimestamp(curt)) + 'Z',
        'codename':    args.codename,
        'gpgkey':      args.gpgkey,
        'suite':       args.suite,
        'version':     args.version,
        'project':     args.project,
        'branch':      args.branch,
        'revision':    args.revision,
        'buildername': args.buildername,
        'buildnumber': args.buildnumber,
    }
    buildlog[args.codename].append(record)

    save_buildlog(buildlog_file, buildlog)
