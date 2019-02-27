#!/usr/bin/env python3
#-------------------------------------------------------------------------------
# Author: Jan Mach <jan.mach@cesnet.cz>
# Copyright (C) since 2016 CESNET, z.s.p.o (http://www.ces.net/)
# Use of this source is governed by the MIT license, see LICENSE file.
#-------------------------------------------------------------------------------


"""
Utility script for generating files from given templates and given variables.
"""


__version__ = "1.0"
__author__  = "Jan Mach <jan.mach@cesnet.cz>"


import os
import re
import pprint
import argparse


from jinja2 import Environment, FileSystemLoader


VERBOSE = 0


def verbose_print(msg, level = 1):
    """
    Print given message, but only in case global ``VERBOSE`` flag is set.
    """
    global VERBOSE
    if VERBOSE >= level:
        print(msg)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
                description = 'Generate files from given templates'
            )

    # Positional mandatory arguments.
    parser.add_argument('template', type=str, help='name of the template')
    parser.add_argument('target',   type=str, help='name of the target file')

    # Optional arguments.
    parser.add_argument('--verbose', '-v', default=0,     action='count',      help='increase output verbosity')
    parser.add_argument('--force',   '-f', default=False, action='store_true', help='overwrite existing files')

    parser.add_argument('--template-dir', type=str, default='./templates', help='directory with Jinja2 templates')
    parser.add_argument('--variable', action='append', type=lambda kv: kv.split("="), dest='variables', default=[], help='variables to enter into template')

    args = parser.parse_args()

    #---------------------------------------------------------------------------

    VERBOSE = args.verbose

    templ_env  = Environment(loader=FileSystemLoader(args.template_dir))
    verbose_print("Using template directory '{}'".format(args.template_dir))

    templ_file_name = '{}.j2'.format(args.template)
    templ_file = templ_env.get_template(templ_file_name)
    verbose_print("Using template '{}'".format(templ_file_name))

    variables = dict(args.variables)
    verbose_print("Using template variables {}".format(pprint.pformat(variables)), level = 2)

    content = templ_file.render(**variables)
    verbose_print("Rendered content:", level = 2)
    verbose_print(content, level = 2)

    if args.force or not os.path.isfile(args.target):
        with open(args.target, "w") as fh:
            fh.write(content)
        verbose_print("Written content to target file '{}'".format(args.target))
    else:
        verbose_print("Target file already exists '{}'".format(args.target))

