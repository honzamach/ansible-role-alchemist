# -*- python -*-
# ex: set filetype=python:
#----------------------- <+++ansible-managed-file+++> -------------------------+
#
#                             IMPORTANT WARNING
#
#  This file is managed remotely by Ansible orchestration tool. Any local
#  changes will be overwritten without any notice !!! You have been warned !!!
#
#----------------------- <+++ansible-managed-file+++> -------------------------+


__author__  = 'Jan Mach <honza.mach.ml@gmail.com>'


import unittest
import pprint

#
# Custom libraries
#
import bb_alchemist
bb_alchemist.initialize(
    'alchemist.domain.org',
    '../../proxy_launcher.sh'
)


class TestBuildbotAlchemist(unittest.TestCase):

    config = {
        'name': 'test',
        'repo_url': 'file://somewhere/test/repo.git',
        'home_dir': '/var/projects/test',
        'metadata': {
            'homepage': 'https://test.project',
            'description': 'Test project',
            'bugtrack': 'https://test.project',
            'master_repo': 'https://test.project/repo.git'
        },
        'build_modules': {
            'doc':   {'workers': ['worker-test'], 'basedir': '/var/tmp', 'builddir': '_build'},
            'whl':   {'mtype': 'whl', 'workers': ['worker-test'], 'pypi_account': 'test_account'}
        },
        'distributions': [
            {
                'label': 'Test Project - Production code',
                'description': 'Debian package repository for project Test and related projects (production code)',
                'suite': 'stable',
                'codename': 'production',
                'branch': 'master',
                'architectures': [
                    'i386',
                    'amd64',
                    'source'
                ],
                'components': [
                    'main'
                ],
                'gpg_key': '777F04E3A5949061'
            },
            {
                'label': 'Test Project - Development code',
                'origin': 'Test Project (development code)',
                'suite': 'unstable',
                'codename': 'development',
                'branch': 'devel',
                'architectures': [
                    'i386',
                    'amd64',
                    'source'
                ],
                'components': [
                    'main'
                ],
                'description': 'Debian package repository for project Test and related projects (development code)',
                'gpg_key': '777F04E3A5949061'
            }
        ],
        'build': ['doc', 'whl']
    }

    def test_01_initializations(self):
        self.maxDiff = None

        project = bb_alchemist.AlchemistProject(**self.config)
        self.assertEqual(
            str(project),
            'test'
        )
        self.assertEqual(
            repr(project),
            "AlchemistProject(test, m: {'whl': AlchemistModuleWheel(whl), 'doc': AlchemistModuleDoc(doc)}, d: [AlchemistDistro(production, stable), AlchemistDistro(development, unstable)], b: AlchemistBuild(['doc', 'whl']))"
        )
        self.assertEqual(
            project.get_build_sequence(),
            ['test-doc', 'test-whl']
        )

        pprint.pprint(project.gen_sch_checkout())
        pprint.pprint(project.gen_sch_force())
        pprint.pprint(project.gen_sch_try())
        pprint.pprint(project.gen_sch_triggers())
        pprint.pprint(project.gen_builders())


#-------------------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()
