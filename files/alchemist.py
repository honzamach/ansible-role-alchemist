#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------- <+++ansible-managed-file+++> -------------------------+
#
#                             IMPORTANT WARNING
#
#  This file is managed remotely by Ansible orchestration tool. Any local
#  changes will be overwritten without any notice !!! You have been warned !!!
#
#
# List of ways of possible improvements:
#
# 1.
# http://docs.buildbot.net/current/manual/cfg-intro.html#testing-the-config-file
# buildbot checkconfig /tmp/masterdir
#
# 2.
# http://docs.buildbot.net/current/manual/cfg-global.html#manhole
#
# 3.
# http://docs.buildbot.net/current/manual/cfg-global.html#input-validation
#
# 4.
# Use renderable list of builders in scheduler to generate list of check builders for unknown branches.
# http://docs.buildbot.net/current/manual/cfg-schedulers.html#configuring-schedulers
# Or perhaps use multiple schedulers with static set f builders and ChangeFilter
# http://docs.buildbot.net/current/manual/cfg-schedulers.html#change-filters
# Or use multiple single branch schedulers and then any branch scheduler with filter
#
# 5. Use owner scheduler property to configure prmary project owner.
# http://docs.buildbot.net/current/manual/cfg-schedulers.html#configuring-schedulers
#
# 6. Set fileIsImportant to none to disble this unused feature.
#
# 7. Use builder config to set environment like pythonpath or path
# http://docs.buildbot.net/current/manual/cfg-builders.html
#
# 8. Use builder config description
# http://docs.buildbot.net/current/manual/cfg-builders.html
#
# 9. Setup collapse requests on builder config
# http://docs.buildbot.net/current/manual/cfg-builders.html
#
# 10. URL for build renderer looks interesting
# http://docs.buildbot.net/current/manual/cfg-properties.html#url-for-build
#
# 11. Perhaps make use ov env paramenter of ShellCommand build step for pythonpath
#
# 12. File exists step could make builds more robust
# http://docs.buildbot.net/current/manual/cfg-buildsteps.html#fileexists
#
# 13. Try to use Sphinx step to generate sphinx documentation
# http://docs.buildbot.net/current/manual/cfg-buildsteps.html#sphinx
#
# 14. Fix uploading packages to the master and he icludes them to the repository
#
# 15.Use deblintian step
# http://docs.buildbot.net/current/manual/cfg-buildsteps.html#deblintian
#
# 16. Check debpbuilder
# http://docs.buildbot.net/current/manual/cfg-buildsteps.html#debpbuilder
#
# 17. Try buildSetSummary
# http://docs.buildbot.net/current/manual/cfg-reporters.html
#
# 18. Buildbot badges
# http://docs.buildbot.net/current/manual/cfg-www.html#badges
#
# 19. Finally get working remote user auth
# http://docs.buildbot.net/current/manual/cfg-www.html#buildbot.www.auth.RemoteUserAuth
#
# 20. Perform maintenance
# http://docs.buildbot.net/current/manual/deploy.html#maintenance
#----------------------- <+++ansible-managed-file+++> -------------------------+

import os

import re
import json
import glob
from flask import Flask, render_template
app = Flask(__name__)


def load_json(filename):
    """
    Load contents of given JSON file and return them as data structures.
    """
    with open(filename, 'r') as fhnd:
        return json.load(fhnd)


def load_projects(projects_path):
    """
    Load all available project metadata.
    """
    result = []

    project_list = os.listdir(projects_path)
    for project_name in sorted(project_list):
        project_path = os.path.join(projects_path, project_name)
        if not os.path.isdir(project_path):
            continue

        project_metadata_file = os.path.join(project_path, '.metadata.json')
        if not os.path.isfile(project_metadata_file):
            continue

        project = load_json(project_metadata_file)

        project_statistics_file = os.path.join(project_path, '.statistics.json')
        if os.path.isfile(project_statistics_file):
            data = load_json(project_statistics_file)
            project['statistics'] = data
        else:
            project['statistics'] = { 'error': 'Missing statistics file {}'.format(project_statistics_file) }

        project['buildenvs'] = {}
        buildenv_files = glob.glob('{}/.buildenv-*.json'.format(project_path))
        ptrn = re.compile(r'^.*\.buildenv-(.*)\.json$')
        for bef in buildenv_files:
            match = ptrn.match(bef)
            if not match:
                continue
            envname = match.group(1)
            data = load_json(bef)
            project['buildenvs'][envname] = data

        result.append(project)

    return result

@app.route('/')
def index():
    """
    Index page view.
    """
    config   = load_json('/opt/alchemist/etc/config.json')
    projects = load_projects(config['projects_path'])

    return render_template(
        'index.html',
        remote_addr = os.environ.get('REMOTE_ADDR', '127.0.0.1'),
        config      = config,
        projects    = projects
    )


#-------------------------------------------------------------------------------


if __name__ == '__main__':
    app.run(
        host  = '127.0.0.1',
        port  = 5000,
        debug = True
    )
