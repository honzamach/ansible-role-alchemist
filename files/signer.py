#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Author: Jan Mach <jan.mach@cesnet.cz>
# Copyright (C) since 2016 CESNET, z.s.p.o (http://www.ces.net/)
# Use of this source is governed by the MIT license, see LICENSE file.
#-------------------------------------------------------------------------------


"""
Utility script for signing all ``^.*\.(whl|deb|tar|gz)$`` files in given cache
directory with SHA256 and given GPG key.
"""


__version__ = "1.0"
__author__  = "Jan Mach <jan.mach@cesnet.cz>"


import os
import re
import pprint
import argparse
import subprocess


VERBOSE  = False


def verbose_print(msg, level = 1):
    """
    Print given message, but only in case global ``VERBOSE`` flag is set.
    """
    global VERBOSE
    if VERBOSE > level:
        print(msg)

def sign_sha256(file_path, force):
    """
    Sign given file with SHA256.
    """
    signature_path = "{}.sha256".format(file_path)
    if force or not os.path.isfile(signature_path):
        cmd = "sha256sum {} > {}".format(file_path, signature_path)
        verbose_print(" - launching command {}".format(pprint.pformat(cmd)))
        subprocess.call(cmd, shell=True)
        verbose_print(" - generated SHA256 signature '{}'".format(signature_path))
    else:
        verbose_print(" - signature already exists '{}'".format(signature_path))


def sign_gpg(gpg_bin, gpg_key, file_path, force):
    """
    Sign given file using given gpg binary with given GPG key.
    """
    signature_path = "{}.gpgsig".format(file_path)
    if force or not os.path.isfile(signature_path):
        cmd = "{} --default-key {} --output {} --detach-sig {}".format(gpg_bin, gpg_key, signature_path, file_path)
        verbose_print(" - launching command {}".format(pprint.pformat(cmd)))
        subprocess.call(cmd, shell=True)
        verbose_print(" - generated GPG signature '{}' with key '{}'".format(signature_path, gpg_key))
    else:
        verbose_print(" - signature already exists '{}'".format(signature_path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                description = 'Secure all packages in given cache directory'
            )

    # Positional mandatory arguments.
    parser.add_argument('gpgkey', type=str, help='GPG key id to sign files with')
    parser.add_argument('cache',  type=str, help='path to directory cache')

    # Optional arguments.
    parser.add_argument('--verbose', '-v', default=0,     action='count',      help='increase output verbosity')
    parser.add_argument('--force',   '-f', default=False, action='store_true', help='overwrite existing signatures')

    parser.add_argument('--file-ptrn',   type=str, default='^.*\.(whl|deb|tar|gz|zip)$', help='pattern for which files to sign')
    parser.add_argument('--gpg-version', type=int, default=1, choices=[1, 2],            help='which version of gpg to use')

    args = parser.parse_args()

    #---------------------------------------------------------------------------

    VERBOSE = args.verbose

    gpg_bin = "gpg" if args.gpg_version == 1 else "gpg2"
    verbose_print("Using GPG binary: '{}'".format(gpg_bin))

    os.chdir(args.cache)
    verbose_print("Processing directory cache: '{}'".format(args.cache))

    ptrn = re.compile(args.file_ptrn)
    verbose_print("Using cache file pattern: '{}'".format(args.file_ptrn))

    file_list = os.listdir(args.cache)
    for f in sorted(file_list):
        if not os.path.isfile(f):
            continue
        if ptrn.match(f):
            verbose_print("Processing file: '{}'".format(f))
            sign_sha256(f, args.force)
            sign_gpg(gpg_bin, args.gpgkey, f, args.force)
        else:
            verbose_print("Skipping file: '{}'".format(f))
