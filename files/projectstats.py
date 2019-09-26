#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Author: Jan Mach <jan.mach@cesnet.cz>
# Copyright (C) since 2016 CESNET, z.s.p.o (http://www.ces.net/)
# Use of this source is governed by the MIT license, see LICENSE file.
#-------------------------------------------------------------------------------


"""
Utility script for generating project statistics data file.
"""


__version__ = "1.0"
__author__  = "Jan Mach <jan.mach@cesnet.cz>"


import os
import re
import json
import pprint
import argparse
import datetime
import collections
import subprocess


VERBOSE  = 0

PTRN_WHL = re.compile(r'^([^-]+)-([^-]+)-.*\.(whl)$')
PTRN_DEB = re.compile(r'^([^_]+)_([^_]+)_([^_]+)\.(deb)$')
PTRN_TGZ = re.compile(r'^([^-]+)-([^-]+)\.(tar\.gz|tgz)$')


def verbose_print(msg, level = 1):
    """
    Print given message, but only in case global ``VERBOSE`` flag is set.
    """
    global VERBOSE
    if VERBOSE >= level:
        print(msg)


#-------------------------------------------------------------------------------


def _analyze_file(fname, file_path, data):
    statr = os.stat(file_path)
    data['file']     = fname
    data['path']     = file_path
    data['atime_ts'] = statr.st_atime
    data['mtime_ts'] = statr.st_mtime
    data['ctime_ts'] = statr.st_ctime
    data['adate']    = str(datetime.datetime.fromtimestamp(statr.st_atime))
    data['mdate']    = str(datetime.datetime.fromtimestamp(statr.st_mtime))
    data['cdate']    = str(datetime.datetime.fromtimestamp(statr.st_ctime))
    return data

def _process_file(result, fname, file_path):
    pkg_name  = pkg_version = pkg_type = None
    while True:
        mtch = PTRN_WHL.match(fname)
        if mtch:
            verbose_print("Processing '.whl' package file: '{}'".format(fname))
            pkg_name    = mtch.group(1)
            pkg_version = mtch.group(2)
            pkg_type    = mtch.group(3)
            break

        mtch = PTRN_DEB.match(fname)
        if mtch:
            verbose_print("Processing '.deb' package file: '{}'".format(fname))
            pkg_name    = mtch.group(1)
            pkg_version = mtch.group(2)
            pkg_type    = mtch.group(4)
            break

        mtch = PTRN_TGZ.match(fname)
        if mtch:
            verbose_print("Processing '.tgz' package file: '{}'".format(fname))
            pkg_name    = mtch.group(1)
            pkg_version = mtch.group(2)
            pkg_type    = 'tgz'
            break

        break

    if not pkg_name:
        verbose_print("Skipping package file: '{}'".format(fname))
        return

    if pkg_version == 'latest':
        verbose_print("Skipping 'latest' version package file: '{}'".format(fname))
        return

    fanl = _analyze_file(fname, file_path, {'version': pkg_version})
    result[pkg_name][pkg_type]['versions'][pkg_version] = fanl
    if not 'latest' in result[pkg_name][pkg_type]:
        result[pkg_name][pkg_type]['latest'] = fanl
    elif fanl['mtime_ts'] > result[pkg_name][pkg_type]['latest']['mtime_ts']:
        result[pkg_name][pkg_type]['latest'] = fanl

def _process_subdir(result, subdir):
    file_list = os.listdir(subdir)
    for fname in reversed(sorted(file_list)):
        file_path = os.path.join(subdir, fname)

        if os.path.isfile(file_path):
            _process_file(result, fname, file_path)

        if os.path.isdir(file_path):
            _process_subdir(result, file_path)

def statistics_files_distribution(distribution_dir):
    """
    Analyze statistics for given file repository distribution.
    """

    # Make ourselves recursive default dict for result.
    rdd = lambda: collections.defaultdict(rdd)
    result = collections.defaultdict(rdd)

    _process_subdir(result, distribution_dir)
    return result


def statistics_files(repository_dir):
    """
    Analyze statistics for all file repository distributions.
    """
    verbose_print("Processing project 'files' repository directory: '{}'".format(repository_dir))
    result = {}

    ptrn = re.compile('^[^.]')
    distro_list = os.listdir(repository_dir)
    for dname in sorted(distro_list):
        distro_path = os.path.join(repository_dir, dname)
        if not os.path.isdir(distro_path):
            continue
        if ptrn.match(dname):
            verbose_print("Processing distribution directory: '{}'".format(dname))
            result[dname] = statistics_files_distribution(distro_path)
        else:
            verbose_print("Skipping directory: '{}'".format(dname))
    return result


#-------------------------------------------------------------------------------


def statistics_deb(repository_dir):
    """
    Analyze statistics for all Debian package repository distributions.
    """
    verbose_print("Processing project 'deb' repository directory: '{}'".format(repository_dir))

    # Make ourselves recursive default dict for result.
    rdd = lambda: collections.defaultdict(rdd)
    result = collections.defaultdict(rdd)

    # Example output lines to be parsed.
    # development|main|amd64 pool/main/m/mentat-ng/mentat-ng_0.2.84_all.deb
    # development|main|i386 pool/main/m/mentat-ng/mentat-ng_0.2.84_all.deb
    ptrn = re.compile(r'(.*)\|(.*)\|(.*)\s+.*/([^/]+\.deb)')

    try:
        output = subprocess.check_output('reprepro -V -b {} dumpreferences'.format(repository_dir), shell=True, stderr=subprocess.STDOUT)
        output = output.decode('utf-8')
        lines = output.split("\n")
        for line in lines:
            line = line.strip()
            mtch = ptrn.match(line)
            if mtch:
                verbose_print("Found package: '{}'".format(mtch.group(0)))
                result[mtch.group(1)][mtch.group(4)] = 1
    except:
        pass
    return result


#-------------------------------------------------------------------------------


def statistics_git(repository_dir):
    """
    Analyze statistics for Git repository.
    """
    verbose_print("Processing project 'git' repository directory: '{}'".format(repository_dir))
    result = {}

    output = subprocess.check_output('git -C {} log --all --pretty=format:"%ci" -1'.format(repository_dir), shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    result['last_commit_date'] = output.strip()

    output = subprocess.check_output('git -C {} log --all --pretty=format:"%ct" -1'.format(repository_dir), shell=True, stderr=subprocess.STDOUT)
    output = output.decode('utf-8')
    result['last_commit_ts'] = output.strip()

    # git log --pretty=format:"Commit: %H%nDate: %ci%nSubject: %s%n%n%b%n---"

    return result


#-------------------------------------------------------------------------------


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser(
        description = 'Generate project statistics for given project'
    )

    # Positional mandatory arguments.
    PARSER.add_argument('projectdir', type=str, help='path to project directory')

    # Optional arguments.
    PARSER.add_argument('--verbose', '-v', default=0,     action='count',      help='increase output verbosity')
    PARSER.add_argument('--force',   '-f', default=False, action='store_true', help='overwrite existing files')

    ARGS = PARSER.parse_args()

    #---------------------------------------------------------------------------

    VERBOSE = ARGS.verbose

    verbose_print("Processing project directory: '{}'".format(ARGS.projectdir))

    stats = {}
    stats['files'] = statistics_files(os.path.join(ARGS.projectdir, 'files'))
    stats['deb']   = statistics_deb(os.path.join(ARGS.projectdir,   'deb'))
    stats['git']   = statistics_git(os.path.join(ARGS.projectdir,   'repo.git'))

    verbose_print("Detected project statistics:")
    verbose_print(pprint.pformat(stats))

    target_file = os.path.join(ARGS.projectdir, '.statistics.json')
    if ARGS.force or not os.path.isfile(target_file):
        with open(target_file, "w") as fh:
            json.dump(stats, fh)
        verbose_print("Written statistics to target file: '{}'".format(target_file))
    else:
        verbose_print("Target statistics file already exists: '{}'".format(target_file))
