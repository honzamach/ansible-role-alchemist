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


VERBOSE = 0


def verbose_print(msg, level = 1):
    """
    Print given message, but only in case global ``VERBOSE`` flag is set.
    """
    global VERBOSE
    if VERBOSE >= level:
        print(msg)


#-------------------------------------------------------------------------------


def analyze_file(f, file_path, data):
    """
    Analyze given file.
    """
    sr = os.stat(file_path)
    data['file']     = f
    data['path']     = file_path
    data['atime_ts'] = sr.st_atime
    data['mtime_ts'] = sr.st_mtime
    data['ctime_ts'] = sr.st_ctime
    data['adate']    = str(datetime.datetime.fromtimestamp(sr.st_atime))
    data['mdate']    = str(datetime.datetime.fromtimestamp(sr.st_mtime))
    data['cdate']    = str(datetime.datetime.fromtimestamp(sr.st_ctime))
    return data

def statistics_files_distribution(distribution_dir):
    """
    Analyze statistics for given file repository distribution.
    """
    ptrn_whl = re.compile('^([^-]+)-([^-]+)-.*\.(whl)$')
    ptrn_deb = re.compile('^([^_]+)_([^_]+)_([^_]+)\.(deb)$')
    ptrn_tgz = re.compile('^([^-]+)-([^-]+)\.(tar\.gz|tgz)$')

    # Make ourselves recursive default dict for result.
    rdd = lambda: collections.defaultdict(rdd)
    result = collections.defaultdict(rdd)

    file_list = os.listdir(distribution_dir)
    for f in reversed(sorted(file_list)):
        pkg_name = pkg_version = pkg_type = None

        file_path = os.path.join(distribution_dir, f)
        if not os.path.isfile(file_path):
            continue

        while True:
            m = ptrn_whl.match(f)
            if m:
                verbose_print("Processing '.whl' package file: '{}'".format(f))
                pkg_name    = m.group(1)
                pkg_version = m.group(2)
                pkg_type    = m.group(3)
                break

            m = ptrn_deb.match(f)
            if m:
                verbose_print("Processing '.deb' package file: '{}'".format(f))
                pkg_name    = m.group(1)
                pkg_version = m.group(2)
                pkg_type    = m.group(4)
                break

            m = ptrn_tgz.match(f)
            if m:
                verbose_print("Processing '.tgz' package file: '{}'".format(f))
                pkg_name    = m.group(1)
                pkg_version = m.group(2)
                pkg_type    = 'tgz'
                break

            break

        if not pkg_name:
            verbose_print("Skipping package file: '{}'".format(f))
            continue

        if pkg_version == 'latest':
            verbose_print("Skipping 'latest' version package file: '{}'".format(f))
            continue

        fa = analyze_file(f, file_path, {'version': pkg_version})
        result[pkg_name][pkg_type]['versions'][pkg_version] = fa
        if not 'latest' in result[pkg_name][pkg_type]:
            result[pkg_name][pkg_type]['latest'] = fa
        elif fa['mtime_ts'] > result[pkg_name][pkg_type]['latest']['mtime_ts']:
            result[pkg_name][pkg_type]['latest'] = fa

    return result


def statistics_files(repository_dir):
    """
    Analyze statistics for all file repository distributions.
    """
    verbose_print("Processing project 'files' repository directory: '{}'".format(repository_dir))
    result = {}

    ptrn = re.compile('^[^.]')
    distro_list = os.listdir(repository_dir)
    for d in sorted(distro_list):
        distro_path = os.path.join(repository_dir, d)
        if not os.path.isdir(distro_path):
            continue
        if ptrn.match(d):
            verbose_print("Processing distribution directory: '{}'".format(d))
            result[d] = statistics_files_distribution(distro_path)
        else:
            verbose_print("Skipping directory: '{}'".format(d))
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
    ptrn = re.compile('(.*)\|(.*)\|(.*)\s+.*/([^/]+\.deb)')

    try:
        output = subprocess.check_output('reprepro -V -b {} dumpreferences'.format(repository_dir), shell=True, stderr=subprocess.STDOUT)
        output = output.decode('utf-8')
        lines = output.split("\n")
        for l in lines:
            l = l.strip()
            m = ptrn.match(l)
            if m:
                verbose_print("Found package: '{}'".format(m.group(0)))
                result[m.group(1)][m.group(4)] = 1
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

    parser = argparse.ArgumentParser(
                description = 'Generate project statistics for given project'
            )

    # Positional mandatory arguments.
    parser.add_argument('projectdir', type=str, help='path to project directory')

    # Optional arguments.
    parser.add_argument('--verbose', '-v', default=0,     action='count',      help='increase output verbosity')
    parser.add_argument('--force',   '-f', default=False, action='store_true', help='overwrite existing files')

    args = parser.parse_args()

    #---------------------------------------------------------------------------

    VERBOSE = args.verbose

    verbose_print("Processing project directory: '{}'".format(args.projectdir))

    stats = {}
    stats['files'] = statistics_files(os.path.join(args.projectdir, 'files'))
    stats['deb']   = statistics_deb(os.path.join(args.projectdir,   'deb'))
    stats['git']   = statistics_git(os.path.join(args.projectdir,   'repo.git'))

    verbose_print("Detected project statistics:")
    verbose_print(pprint.pformat(stats))

    target_file = os.path.join(args.projectdir, '.statistics.json')
    if args.force or not os.path.isfile(target_file):
        with open(target_file, "w") as fh:
            json.dump(stats, fh)
        verbose_print("Written statistics to target file: '{}'".format(target_file))
    else:
        verbose_print("Target statistics file already exists: '{}'".format(target_file))
