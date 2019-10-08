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


import os
import re
import json
import weakref
import logging
from past.builtins import basestring

from buildbot.plugins import worker, steps, schedulers, util

LOGGER = logging.getLogger('bb_alchemist')

#
# Custom global constants.
#
PATH_PROXY_LAUNCHER = None
FQDN_MASTER_SERVER  = None
WORKER_DIR          = None

WORKERS  = None
PROJECTS = None


def initialize(master_server, proxy_launcher, worker_dir):
    """
    This method must be called before using the library to properly initialize
    important internal configurations.
    """
    global FQDN_MASTER_SERVER, PATH_PROXY_LAUNCHER, WORKER_DIR  # pylint: disable=locally-disabled,global-statement
    FQDN_MASTER_SERVER  = master_server
    PATH_PROXY_LAUNCHER = proxy_launcher
    WORKER_DIR          = worker_dir


def setup_workers(config):
    """
    Setup Alchemist worker objects according to the given configuration.
    """
    global WORKERS  # pylint: disable=locally-disabled,global-statement
    WORKERS = {}
    for worker_name, worker_cfg in config.items():
        WORKERS[worker_name] = AlchemistWorker(**worker_cfg)
    return WORKERS


def get_workers():
    """
    Get dictionary of all currently set up Alchemist worker objects.
    """
    global WORKERS  # pylint: disable=locally-disabled,global-statement
    return WORKERS


def setup_projects(config):
    """
    Setup Alchemist project objects according to the given configuration.
    """
    global PROJECTS  # pylint: disable=locally-disabled,global-statement
    PROJECTS = {}
    for project_name, project_cfg in config.items():
        PROJECTS[project_name] = AlchemistProject(**project_cfg)
    return PROJECTS

def get_projects():
    """
    Get dictionary of all currently set up Alchemist project objects.
    """
    global PROJECTS  # pylint: disable=locally-disabled,global-statement
    return PROJECTS


#===============================================================================


def is_important_always(change):  # pylint: disable=locally-disabled,unused-argument
    """
    Dummy callback that deems all code changes important.
    """
    return True

@util.renderer
def cb_any_compute_properties(props):
    """
    Buildbot renderer for assigning additional build properties.
    """
    metadata = props.getProperty('metadata')
    project  = props.getProperty('project')
    branch   = props.getProperty('branch')
    if not branch:
        branch = 'master'

    if isinstance(metadata, basestring):
        metadata = json.loads(metadata)

    codename = metadata[project][branch]['codename']
    suite    = metadata[project][branch]['suite']
    gpgkey   = metadata[project][branch]['gpgkey']

    return {
        'build_codename': codename,
        'build_suite':    suite,
        'build_gpgkey':   gpgkey
    }

def cb_any_detect_version(rc, stdout, stderr):
    """
    Callback for analyzing stdout output of the command and detecting version
    string.
    """
    val = 'unknown'
    mtch = re.match(r'^\s*([-.0-9a-zA-Z]+)\s*$', stdout)
    if mtch:
        val = mtch.group(1)
    return { 'build_version': val }

def cb_any_detect_whl(rc, stdout, stderr):
    """
    Callback for analyzing stdout output of the command and detecting version
    string.
    """
    val = 'unknown'
    mtch = re.match(r'^\s*(?:\./)?([-_0-9a-zA-Z]+)\s*$', stdout)
    if mtch:
        val = mtch.group(1)
    val = re.sub(r"[-_.]+", "-", val).lower()
    return { 'package_whl': val }

def cb_detect_production(step):
    """
    Detection of production level build.
    """
    if step.getProperty('build_codename') == 'production':
        return True
    return False

def cb_detect_notproduction(step):
    """
    Detection of not production level build.
    """
    if step.getProperty('build_codename') == 'production':
        return False
    return True


#===============================================================================


class AlchemistWorker(object):
    """
    Object representation of Alchemist pre-build setup.
    """
    def __init__(self, name, setup = None, properties = None):
        self.name   = name
        self.setup  = setup
        self.props  = properties or {}

    def __repr__(self):
        return 'AlchemistWorker(%s)' % (self.name)

    def generate_worker(self, password, admin_email):
        """
        Generate buildbot configuration for this worker.
        """
        tmp =  worker.Worker(
            self.name,
            password,
            notify_on_missing = [admin_email],
            missing_timeout = 300,
            properties = self.props
        )
        LOGGER.info(
            "Generated WORKER '%s'",
            self.name
        )
        return tmp


#===============================================================================


class AlchemistBuildModule(object):
    """
    Base class for all Alchemist build modules.
    """
    BUILDDIR = 'build'

    def __init__(self, project, name, mtype, workername, properties = None):
        self.project = weakref.ref(project)
        self.worker  = weakref.ref(WORKERS[workername])
        self.name    = name
        self.mtype   = mtype
        self.props   = properties or {}

    def __str__(self):
        return self.name

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.name)

    #---------------------------------------------------------------------------

    def _gen_steps_git(self):
        """
        Build step factory: Fetch latest codebase from Git repository.
        """
        return [
            steps.Git(
                name            = 'fetching codebase',
                description     = 'fetching codebase',
                descriptionDone = 'fetched codebase',
                repourl         = self.project().repo_url,
                mode            = 'full',
                submodules      = self.project().subrepos,
                haltOnFailure   = True
            )
        ]

    def _gen_steps_set_build_props(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: Set additional dependent build properties for any project.
        """
        return [
            steps.SetProperties(
                name            = 'setting build properties',
                description     = 'setting build properties',
                descriptionDone = 'set build properties',
                properties      = cb_any_compute_properties
            )
        ]

    def _gen_steps_detect_version(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: Detect name of the generated package.
        """
        return [
            steps.SetPropertyFromCommand(
                name            = 'detecting version',
                description     = 'detecting package version',
                descriptionDone = 'detected version',
                command         = [PATH_PROXY_LAUNCHER, 'make', 'show-version'],
                extract_fn      = cb_any_detect_version,
                workdir         = self.BUILDDIR,
                haltOnFailure   = True
            )
        ]

    def _gen_steps_tree_size(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: Calculate the size of project code tree.
        """
        return [
            steps.TreeSize(
                name            = 'calculating size',
                description     = 'calculating codebase size',
                descriptionDone = 'calculated size',
                workdir         = self.BUILDDIR,
                haltOnFailure   = True
            )
        ]

    def _gen_steps_envstats_gen(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: Generate build environment statistics.
        """
        return [
            steps.ShellCommand(
                name            = 'generating envstats',
                description     = 'generating envstats',
                descriptionDone = 'generated envstats',
                command         = [
                    PATH_PROXY_LAUNCHER,
                    '/opt/alchemist/bin/envstats.py',
                    '--verbose',
                    '--force',
                    util.Interpolate('.buildenv-%(prop:build_codename)s.json')
                ],
                workdir         = self.BUILDDIR,
                haltOnFailure   = True
            )
        ]

    def _gen_steps_envstats_upload(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: Upload build environment statistics.
        """
        return [
            steps.FileUpload(
                name            = 'uploading envstats',
                description     = 'uploading envstats',
                descriptionDone = 'uploaded envstats',
                workdir         = self.BUILDDIR,
                workersrc       = util.Interpolate('.buildenv-%(prop:build_codename)s.json'),
                masterdest      = util.Interpolate('%s/.buildenv-%%(prop:build_codename)s.json' % self.project().home_dir)
            )
        ]

    def _gen_steps_envstats_chp(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: MASTER - Ensure correct permissions for build environment statistics file.
        """
        return [
            steps.MasterShellCommand(
                name            = 'chmoding envstats',
                description     = 'chmoding envstats',
                descriptionDone = 'chmoded envstats',
                command         = util.Interpolate('chmod 0644 %s/.buildenv-%%(prop:build_codename)s.json' % self.project().home_dir),
                workdir         = '/var/tmp',
                haltOnFailure   = True
            )
        ]

    def _gen_steps_projstats_gen(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: MASTER - Generate project statistics.
        """
        return [
            steps.MasterShellCommand(
                name            = 'generating projstats',
                description     = 'generating projstats',
                descriptionDone = 'generated projstats',
                command         = [
                    '/opt/alchemist/bin/projectstats.py',
                    '--verbose',
                    '--force',
                    '%s' % self.project().home_dir
                ],
                workdir         = '/var/tmp',
                haltOnFailure   = True
            )
        ]

    def _gen_steps_debrepo_list(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: MASTER - Listing contents of Debian repository (mainly for debugging purposes).
        """
        return [
            steps.MasterShellCommand(
                name            = 'listing repository',
                description     = 'listing debian repository',
                descriptionDone = 'listed repository',
                command         = util.Interpolate('reprepro -V -b %s/deb -C main list %%(prop:build_codename)s' % self.project().home_dir),
                workdir         = '/var/tmp',
                haltOnFailure   = True
            )
        ]

    def _gen_steps_filerepo_list(self):  # pylint: disable=locally-disabled,no-self-use
        # MASTER: Listing contents of file repository (mainly for debugging purposes).
        return [
            steps.MasterShellCommand(
                name            = 'listing repository',
                description     = 'listing file repository',
                descriptionDone = 'listed repository',
                command         = util.Interpolate('ls -alR %s/files/%%(prop:build_codename)s/' % self.project().home_dir),
                workdir         = '/var/tmp',
                haltOnFailure   = True
            )
        ]

    def _gen_steps_filerepo_sign(self):  # pylint: disable=locally-disabled,no-self-use
        # MASTER: Generating the package signatures in file repository.
        return [
            steps.MasterShellCommand(
                name            = 'signing files',
                description     = 'signing files',
                descriptionDone = 'signed files',
                command         = [
                    '/opt/alchemist/bin/signer.py',
                    '--verbose',
                    util.Property('build_gpgkey'),
                    util.Interpolate('%s/files/%%(prop:build_codename)s' % self.project().home_dir)
                ],
                workdir         = '/var/tmp',
                haltOnFailure   = True
            )
        ]

    def _gen_steps_log_build(self):  # pylint: disable=locally-disabled,no-self-use
        """
        Build step factory: MASTER - Generate project build log.
        """
        return [
            steps.MasterShellCommand(
                name            = 'logging build',
                description     = 'logging build',
                descriptionDone = 'logged build',
                command         = [
                    '/opt/alchemist/bin/buildlogger.py',
                    '--verbose',
                    util.Interpolate("--codename=%(prop:build_codename)s"),
                    util.Interpolate("--gpgkey=%(prop:build_gpgkey)s"),
                    util.Interpolate("--suite=%(prop:build_suite)s"),
                    util.Interpolate("--version=%(prop:build_version)s"),
                    util.Interpolate("--project=%(prop:project)s"),
                    util.Interpolate("--branch=%(prop:branch)s"),
                    util.Interpolate("--revision=%(prop:got_revision)s"),
                    util.Interpolate("--buildername=%(prop:buildername)s"),
                    util.Interpolate("--buildnumber=%(prop:buildnumber)s"),
                    '%s' % self.project().home_dir
                ],
                workdir         = '/var/tmp',
                haltOnFailure   = True
            )
        ]

    #---------------------------------------------------------------------------

    def _gen_build_factory(self):
        raise NotImplementedError()

    def generate_builder(self):
        """
        Generate builder configuration for this build module.
        """
        builder_name = '%s-%s' % (self.project().name, self.name)
        builder = util.BuilderConfig(
            name       = builder_name,
            workername = self.worker().name,
            factory    = self._gen_build_factory(),
            tags       = [
                'project-%s' % self.project().name,
                'build-%s' % self.mtype
            ],
            properties = self.props
        )

        LOGGER.info(
            "[%s] Generated BUILDER '%s'",
            self.project().name,
            builder_name
        )
        return builder


class AlchemistBuildCheck(AlchemistBuildModule):  # pylint: disable=locally-disabled,too-few-public-methods
    """
    Alchemist build module for checking the project (unit tests, linting, ...).
    """
    def __init__(self, project, name, mtype, workername, properties = None, **params):
        AlchemistBuildModule.__init__(self, project, name, mtype, workername, properties)

    def _gen_build_factory(self):
        step_list = []

        # Include common pre-build steps.
        step_list.extend(self._gen_steps_git())
        step_list.extend(self._gen_steps_detect_version())
        step_list.extend(self._gen_steps_set_build_props())
        step_list.extend(self._gen_steps_tree_size())

        # Install project dependencies.
        step_list.append(steps.ShellCommand(
            name            = 'installing dependencies',
            description     = 'installing dependencies',
            descriptionDone = 'installed dependencies',
            command         = [PATH_PROXY_LAUNCHER, 'make', 'deps'],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Check project code with pyflakes.
        step_list.append(steps.PyFlakes(
            name            = 'checking pyflakes',
            description     = 'checking pyflakes',
            descriptionDone = 'checked pyflakes',
            command         = [PATH_PROXY_LAUNCHER, 'make', 'pyflakes'],
            workdir         = self.BUILDDIR,
            haltOnFailure   = False
        ))

        # Check project code with pylint.
        step_list.append(steps.PyLint(
            name            = 'checking pylint',
            description     = 'checking pylint',
            descriptionDone = 'checked pylint',
            command         = [PATH_PROXY_LAUNCHER, 'make', 'pylint'],
            workdir         = self.BUILDDIR,
            haltOnFailure   = False
        ))

        # Perform unit tests (currently not working).
        step_list.append(steps.ShellCommand(
            name            = 'testing',
            description     = 'testing codebase',
            descriptionDone = 'testing',
            command         = [PATH_PROXY_LAUNCHER, 'make', 'test'],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Include common post-build steps.
        step_list.extend(self._gen_steps_envstats_gen())
        step_list.extend(self._gen_steps_envstats_upload())
        step_list.extend(self._gen_steps_envstats_chp())

        # MASTER: Regenerate project statistics.
        step_list.extend(self._gen_steps_projstats_gen())

        return util.BuildFactory(step_list)


class AlchemistBuildBench(AlchemistBuildModule):  # pylint: disable=locally-disabled,too-few-public-methods
    """
    Alchemist build module for benchmarking the project.
    """
    def __init__(self, project, name, mtype, workername, properties = None, **params):
        AlchemistBuildModule.__init__(self, project, name, mtype, workername, properties)

    def _gen_build_factory(self):
        """
        Helper: Generate build factory for project codebase benchmarking.
        """
        step_list = []

        # Include common pre-build steps.
        step_list.extend(self._gen_steps_git())
        step_list.extend(self._gen_steps_detect_version())
        step_list.extend(self._gen_steps_set_build_props())
        step_list.extend(self._gen_steps_tree_size())

        # Install project dependencies.
        step_list.append(steps.ShellCommand(
            name            = 'installing dependencies',
            description     = 'installing dependencies',
            descriptionDone = 'installed dependencies',
            command         = [PATH_PROXY_LAUNCHER, 'make', 'deps'],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Check project code with pyflakes.
        step_list.append(steps.ShellCommand(
            name            = 'benchmarking',
            description     = 'benchmarking',
            descriptionDone = 'benchmarked',
            command         = [PATH_PROXY_LAUNCHER, 'make', 'benchmark'],
            workdir         = self.BUILDDIR,
            haltOnFailure   = False
        ))

        # Include common environment detection steps.
        step_list.extend(self._gen_steps_envstats_gen())
        step_list.extend(self._gen_steps_envstats_upload())
        step_list.extend(self._gen_steps_envstats_chp())

        # MASTER: Regenerate project statistics.
        step_list.extend(self._gen_steps_projstats_gen())

        return util.BuildFactory(step_list)


class AlchemistBuildDoc(AlchemistBuildModule):  # pylint: disable=locally-disabled,too-few-public-methods
    """
    Alchemist build module for building project documentation.
    """
    def __init__(self, project, name, mtype, workername, properties = None, **params):
        AlchemistBuildModule.__init__(self, project, name, mtype, workername, properties)
        self.basedir  = params['basedir']
        self.builddir = params['builddir']
        self.docindex = params.get('docindex', 'index.html')

    def _gen_build_factory(self):
        """
        Helper: Generate build factory for project documentation generation.
        """
        step_list = []

        # Include common pre-build steps.
        step_list.extend(self._gen_steps_git())
        step_list.extend(self._gen_steps_detect_version())
        step_list.extend(self._gen_steps_set_build_props())
        step_list.extend(self._gen_steps_tree_size())

        # Generate metadata for documentation build.
        step_list.append(steps.ShellCommand(
            name            = 'generating metadata',
            description     = 'generating sphinx-doc metadata',
            descriptionDone = 'generated metadata',
            command         = [
                '/opt/alchemist/bin/templater.py',
                '--verbose',
                '--force',
                '--template-dir', '/opt/alchemist/etc/templates',
                '--variable', util.Interpolate('codename=%(prop:build_codename)s'),
                '--variable', util.Interpolate('suite=%(prop:build_suite)s'),
                '--variable', util.Interpolate('bversion=%(prop:build_version)s'),
                '--variable', util.Interpolate('revision=%(prop:got_revision)s'),
                '--variable', util.Interpolate('bnumber=%(prop:buildnumber)s'),
                'sphinx.metadata.json',
                'metadata.json'
            ],
            workdir         = self.basedir,
            haltOnFailure   = True
        ))

        # Generate the documentation.
        step_list.append(steps.ShellCommand(
            name            = 'generating documentation',
            description     = 'generating html documentation',
            descriptionDone = 'generated documentation',
            command         = [PATH_PROXY_LAUNCHER, 'make', 'docs'],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Upload documentation to the master server.
        step_list.append(steps.DirectoryUpload(
            name            = 'uploading documentation',
            description     = 'uploading html documentation',
            descriptionDone = 'uploaded documentation',
            workdir         = self.basedir,
            workersrc       = self.builddir,
            masterdest      = util.Interpolate('/var/tmp/%s-doc-%%(prop:build_codename)s-%%(prop:buildnumber)s/html' % self.project().name),
            url             = util.Interpolate('https://%s/%s/doc/%%(prop:build_codename)s/html/%s' % (FQDN_MASTER_SERVER, self.project().name, self.docindex))
        ))

        # MASTER: Synchronize the documentation to appropriate webserver directory.
        step_list.append(steps.MasterShellCommand(
            name            = 'synchronizing documentation',
            description     = 'synchronizing documentation',
            descriptionDone = 'synchronized documentation',
            command         = util.Interpolate('rsync -r --update --delete --force --progress %s-doc-%%(prop:build_codename)s-%%(prop:buildnumber)s/ %s/doc/%%(prop:build_codename)s' % (self.project().name, self.project().home_dir)),
            workdir         = '/var/tmp',
            haltOnFailure   = True
        ))

        # MASTER: Remove the documentation to from temporary directory.
        step_list.append(steps.MasterShellCommand(
            name            = 'removing temporary',
            description     = 'removing temporary files',
            descriptionDone = 'removed temporary',
            command         = util.Interpolate('rm -rf /var/tmp/%s-doc-%%(prop:build_codename)s-%%(prop:buildnumber)s' % self.project().name),
            workdir         = '/var/tmp',
            haltOnFailure   = True
        ))

        # MASTER: Checking documentation size (invoke as string to force shell expansions).
        step_list.append(steps.MasterShellCommand(
            name            = 'checking size',
            description     = 'checking size',
            descriptionDone = 'checked size',
            command         = 'du -csh %s/doc/*' % self.project().home_dir,
            workdir         = '/var/tmp',
            haltOnFailure   = True
        ))

        # MASTER: Log the successfull build
        step_list.extend(self._gen_steps_log_build())

        return util.BuildFactory(step_list)


class AlchemistBuildDeb(AlchemistBuildModule):  # pylint: disable=locally-disabled,too-few-public-methods
    """
    Alchemist build module for building Debian packages.
    """
    def __init__(self, project, name, mtype, workername, properties = None, **params):
        AlchemistBuildModule.__init__(self, project, name, mtype, workername, properties)
        self.packagename       = params['packagename']
        self.libdir            = params['libdir']
        self.make_target_deps  = params.get('make_target_deps', None)
        self.make_target_build = params.get('make_target_build', 'buildbot')
        self.devserver         = params.get('devserver', None)

    def _gen_build_factory(self):
        """
        Helper: Generate build factory for project Debian package generation.
        """
        step_list = []

        # Include common pre-build steps.
        step_list.extend(self._gen_steps_git())
        step_list.extend(self._gen_steps_detect_version())
        step_list.extend(self._gen_steps_set_build_props())
        step_list.extend(self._gen_steps_tree_size())

        # Install necessary build dependencies.
        if self.make_target_deps:
            step_list.append(steps.ShellCommand(
                name            = 'installing dependencies',
                description     = 'installing dependencies',
                descriptionDone = 'installed dependencies',
                command         = [
                    PATH_PROXY_LAUNCHER,
                    'make',
                    self.make_target_deps
                ],
                workdir         = self.BUILDDIR,
                haltOnFailure   = True
            ))

        # Generate build version information file.
        step_list.append(steps.ShellCommand(
            name            = 'generating metadata',
            description     = 'generating code build metadata',
            descriptionDone = 'generated metadata',
            command         = [
                '/opt/alchemist/bin/templater.py',
                '--verbose',
                '--force',
                '--template-dir', '/opt/alchemist/etc/templates',
                '--variable', util.Interpolate('codename=%(prop:build_codename)s'),
                '--variable', util.Interpolate('suite=%(prop:build_suite)s'),
                '--variable', util.Interpolate('bversion=%(prop:build_version)s'),
                '--variable', util.Interpolate('revision=%(prop:got_revision)s'),
                '--variable', util.Interpolate('bnumber=%(prop:buildnumber)s'),
                'buildmeta.py',
                './%s_buildmeta.py' % self.libdir
            ],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Generate Debian package using appropriate Grunt task.
        step_list.append(steps.ShellCommand(
            name            = 'generating package',
            description     = 'generating debian package',
            descriptionDone = 'generated package',
            command         = [
                PATH_PROXY_LAUNCHER,
                'make',
                self.make_target_build,
                util.Interpolate('BUILD_NUMBER=%(prop:buildnumber)s'),
                util.Interpolate('BUILD_SUITE=%(prop:build_codename)s')
            ],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Detect name of the generated Debian package (invoke as string to force shell expansions).
        step_list.append(steps.SetPropertyFromCommand(
            name            = 'detecting package',
            description     = 'detecting debian package name',
            descriptionDone = 'detected package',
            command         = "find . -maxdepth 1 -name '*.deb' | grep -v latest",
            property        = 'package_file_deb',
            workdir         = os.path.join(self.BUILDDIR, 'debdist'),
            haltOnFailure   = True
        ))

        # Lint debian package.
        step_list.append(steps.DebLintian(
            name            = 'linting package',
            description     = 'linting debian package',
            descriptionDone = 'linted package',
            fileloc         = util.Interpolate('%(prop:package_file_deb)s'),
            workdir         = os.path.join(self.BUILDDIR, 'debdist')
        ))

        # List content of Debian repository before adding package.
        step_list.extend(self._gen_steps_debrepo_list())

        # Include Debian package into repository.
        # TODO: Should be master task and come after upload.
        step_list.append(steps.ShellCommand(
            name            = 'including package',
            description     = 'including debian package',
            descriptionDone = 'included package',
            command         = util.Interpolate('reprepro -V -b %s/deb -C main includedeb %%(prop:build_codename)s %%(prop:package_file_deb)s' % self.project().home_dir),
            workdir         = os.path.join(self.BUILDDIR, 'debdist'),
            haltOnFailure   = True
        ))

        # List content of Debian repository after adding package.
        step_list.extend(self._gen_steps_debrepo_list())

        # List content of repository before adding and signing package.
        step_list.extend(self._gen_steps_filerepo_list())

        # Moving generated Debian package to file repository.
        # TODO: Should be master task and come after upload.
        step_list.append(steps.ShellCommand(
            name            = 'moving package',
            description     = 'moving debian package',
            descriptionDone = 'moved package',
            command         = util.Interpolate("mv -f -t %s/files/%%(prop:build_codename)s %%(prop:package_file_deb)s" % self.project().home_dir),
            workdir         = os.path.join(self.BUILDDIR, 'debdist'),
            haltOnFailure   = True
        ))

        # Generating the package signatures in file repository.
        step_list.extend(self._gen_steps_filerepo_sign())

        # List content of repository after adding and signing package.
        step_list.extend(self._gen_steps_filerepo_list())

        # Include common environment detection steps.
        step_list.extend(self._gen_steps_envstats_gen())
        step_list.extend(self._gen_steps_envstats_upload())
        step_list.extend(self._gen_steps_envstats_chp())

        # MASTER: Regenerate project statistics.
        step_list.extend(self._gen_steps_projstats_gen())

        # Upgrade package on development server.
        if self.devserver:
            step_list.append(steps.MasterShellCommand(
                name            = 'upgrading devserver',
                description     = 'upgrading devserver',
                descriptionDone = 'upgraded devserver',
                command         = 'ssh buildbot@%s "sudo aptitude update && sudo aptitude install %s -y"' % (self.devserver, self.packagename),
                workdir         = '/var/tmp',
                haltOnFailure   = True,
                doStepIf        = cb_detect_notproduction,
            ))

        # MASTER: Log the successfull build
        step_list.extend(self._gen_steps_log_build())

        return util.BuildFactory(step_list)


class AlchemistBuildWheel(AlchemistBuildModule):  # pylint: disable=locally-disabled,too-few-public-methods
    """
    Alchemist build module for building Python packages.
    """
    def __init__(self, project, name, mtype, workername, properties = None, **params):
        AlchemistBuildModule.__init__(self, project, name, mtype, workername, properties)
        self.make_target_deps  = params.get('make_target_deps', None)
        self.make_target_build = params.get('make_target_build', 'buildbot')
        self.pypi_account      = params.get('pypi_account', None)
        self.devserver         = params.get('devserver', None)

    def _gen_build_factory(self):
        """
        Helper: Generate build factory for project
        """
        step_list = []

        # Include common pre-build steps.
        step_list.extend(self._gen_steps_git())
        step_list.extend(self._gen_steps_detect_version())
        step_list.extend(self._gen_steps_set_build_props())
        step_list.extend(self._gen_steps_tree_size())

        # Install necessary build dependencies.
        if self.make_target_deps:
            step_list.append(steps.ShellCommand(
                name            = 'installing dependencies',
                description     = 'installing dependencies',
                descriptionDone = 'installed dependencies',
                command         = [
                    PATH_PROXY_LAUNCHER,
                    'make',
                    self.make_target_deps
                ],
                workdir         = self.BUILDDIR,
                haltOnFailure   = True
            ))

        # Generate the Python packages.
        step_list.append(steps.ShellCommand(
            name            = 'generating packages',
            description     = 'generating python packages',
            descriptionDone = 'generated packages',
            command         = [
                PATH_PROXY_LAUNCHER,
                'make',
                self.make_target_build
            ],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Detect name of the generated Python package file (invoke as string to force shell expansions).
        step_list.append(steps.SetPropertyFromCommand(
            name            = 'detecting package file',
            description     = 'detecting python package file name',
            descriptionDone = 'detected package file',
            command         = "find . -maxdepth 1 -name '*.whl' | grep -v latest",
            property        = 'package_file_whl',
            workdir         = os.path.join(self.BUILDDIR, 'dist'),
            haltOnFailure   = True
        ))

        # Detect name of the generated Python package (invoke as string to force shell expansions).
        step_list.append(steps.SetPropertyFromCommand(
            name            = 'detecting package',
            description     = 'detecting python package name',
            descriptionDone = 'detected package',
            command         = "find . -maxdepth 1 -name '*.whl' | grep -v latest | cut -d '-' -f 1",
            extract_fn      = cb_any_detect_whl,
            workdir         = os.path.join(self.BUILDDIR, 'dist'),
            haltOnFailure   = True
        ))

        # Upload generated Python packages to the master server.
        step_list.append(steps.MultipleFileUpload(
            name            = 'uploading packages',
            description     = 'uploading python packages to master',
            descriptionDone = 'uploaded packages',
            workdir         = os.path.join(self.BUILDDIR, 'dist'),
            workersrcs      = ["%s*" % self.project().name],
            masterdest      = util.Interpolate('/var/tmp/%s-whl-%%(prop:build_codename)s-%%(prop:buildnumber)s/' % self.project().name),
            url             = util.Interpolate('https://%s/%s/files/%%(prop:build_codename)s/' % (FQDN_MASTER_SERVER, self.project().name)),
            glob            = True
        ))

        # MASTER: Remove the packages from temporary directory.
        step_list.append(steps.MasterShellCommand(
            name            = 'removing temporary',
            description     = 'removing temporary files',
            descriptionDone = 'removed temporary',
            command         = util.Interpolate('rm -rf /var/tmp/%s-whl-%%(prop:build_codename)s-%%(prop:buildnumber)s' % self.project().name),
            workdir         = '/var/tmp',
            haltOnFailure   = True
        ))

        # Generate .pypirc for Twine.
        # TODO: Should be master task and come after upload.
        step_list.append(steps.ShellCommand(
            name            = 'generating metadata',
            description     = 'generating pypirc metadata',
            descriptionDone = 'generated metadata',
            command         = [
                '/opt/alchemist/bin/templater.py',
                '--verbose',
                '--template-dir', '/opt/alchemist/etc/templates',
                '--variable', 'username=%s' % self.pypi_account,
                '--variable', util.Interpolate('password=%%(secret:pypi_%s)s' % self.pypi_account),
                'pypi.pypirc',
                '.pypirc'
            ],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Upload the Python packages to PyPI servers.
        # TODO: Should be master task and come after upload.
        step_list.append(steps.ShellCommand(
            name            = 'uploading packages',
            description     = 'uploading python packages to pypi',
            descriptionDone = 'uploaded packages',
            command         = [
                'twine',
                'upload',
                'dist/%s*' % self.project().name,
                '--skip-existing',
                '--config-file',
                '.pypirc'
            ],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True,
            doStepIf        = cb_detect_production,
        ))

        # List content of repository before adding and signing package.
        step_list.extend(self._gen_steps_filerepo_list())

        # Remove generated .pypirc for Twine.
        # TODO: Should be master task and come after upload.
        step_list.append(steps.ShellCommand(
            name            = 'removing metadata',
            description     = 'removing pypirc metadata',
            descriptionDone = 'removed metadata',
            command         = [
                'rm',
                '-f',
                '.pypirc'
            ],
            workdir         = self.BUILDDIR,
            haltOnFailure   = True
        ))

        # Move generated Python packages to appropriate file repository.
        # TODO: Should be master task and come after upload.
        step_list.append(steps.ShellCommand(
            name            = 'moving packages',
            description     = 'moving python packages',
            descriptionDone = 'moved packages',
            command         = util.Interpolate("mkdir -p %s/files/%%(prop:build_codename)s/%%(prop:package_whl)s; mv -f -t %s/files/%%(prop:build_codename)s/%%(prop:package_whl)s %s*" % (self.project().home_dir, self.project().home_dir, self.project().name)),
            workdir         = os.path.join(self.BUILDDIR, 'dist'),
            haltOnFailure   = True
        ))

        # Upgrade package on development server.
        #if devserver:
        #    step_list.append(steps.MasterShellCommand(
        #        name            = 'upgrading devserver',
        #        description     = 'upgrading devserver',
        #        descriptionDone = 'upgraded devserver',
        #        command         = util.Interpolate("ssh buildbot@{} \"pip3 install {} --upgrade\"".format(devserver, project.name)),
        #        workdir         = '/var/tmp',
        #        haltOnFailure   = True,
        #        doStepIf        = cb_detect_notproduction,
        #    ))

        # Generating the package signatures in file repository.
        step_list.extend(self._gen_steps_filerepo_sign())

        # List content of repository after adding and signing package.
        step_list.extend(self._gen_steps_filerepo_list())

        # Include common environment detection steps.
        step_list.extend(self._gen_steps_envstats_gen())
        step_list.extend(self._gen_steps_envstats_upload())
        step_list.extend(self._gen_steps_envstats_chp())

        # MASTER: Regenerate project statistics.
        step_list.extend(self._gen_steps_projstats_gen())

        # MASTER: Log the successfull build
        step_list.extend(self._gen_steps_log_build())

        return util.BuildFactory(step_list)


ALCHEMIST_BUILD_MODULES = {
    'check': AlchemistBuildCheck,
    'bench': AlchemistBuildBench,
    'doc':   AlchemistBuildDoc,
    'deb':   AlchemistBuildDeb,
    'whl':   AlchemistBuildWheel
}


#===============================================================================


class AlchemistDistro(object):
    """
    Object representation of Alchemist project distribution.
    """
    def __init__(self, project, codename, suite, branch, gpg_key, **params):
        self.project = weakref.ref(project)
        self.codename = codename
        self.suite = suite
        self.branch = branch
        self.gpg_key = gpg_key
        self.label = params.get(
            'label',
            'Project %s (%s code)' % (project.name, suite)
        )
        self.description = params.get(
            'description',
            'Project %s - %s level %s code)' % (project.name, suite, codename)
        )
        self.architectures = params.get(
            'architectures',
            list(('i386', 'amd64', 'source'))
        )
        self.components = params.get(
            'components',
            list(('main',))
        )

    def __str__(self):
        return self.codename

    def __repr__(self):
        return 'AlchemistDistro(%s, %s)' % (self.codename, self.suite)


#===============================================================================


class AlchemistBuildSequence(object):
    """
    Object representation of Alchemist build sequence.
    """
    def __init__(self, project, build_sequence):
        self.project = weakref.ref(project)
        self.build_modules = build_sequence

        for module_name in self.build_modules:
            if not project.module_exists(module_name):
                raise ValueError("Invalid module name '%s' used in build sequence for project %s" % (module_name, project.name))

    def __repr__(self):
        return 'AlchemistBuildSequence(%s)' % (repr(sorted(self.build_modules)),)

    #---------------------------------------------------------------------------

    def get_builder_names(self):
        """
        Get list of builder names in this build sequence.
        """
        result = []
        for module in self.build_modules:
            result.append('%s-%s' % (self.project().name, module))
        return result


#===============================================================================


class AlchemistBuildSetup(object):
    """
    Object representation of Alchemist pre-build setup.
    """
    def __init__(self, project, **build_setup):
        self.project = weakref.ref(project)
        self.packages_pip = None
        self.packages_deb = None
        self.commands     = None

        if 'packages_pip' in build_setup:
            self.packages_pip = build_setup['packages_pip']
        if 'packages_deb' in build_setup:
            self.packages_deb = build_setup['packages_deb']
        if 'commands' in build_setup:
            self.commands = build_setup['commands']

    def __repr__(self):
        return 'AlchemistBuildSetup()'


#===============================================================================


class AlchemistProject(object):
    """
    Object representation of Alchemist project.
    """
    parameter_any_force_codebases = [
        util.CodebaseParameter(
            '',
            name = 'Main repository',
            repository = util.FixedParameter(
                name    = 'repository',
                default = ''
            ),
            project = util.FixedParameter(
                name    = 'project',
                default = 'mentat'
            ),
            revision = util.StringParameter(
                name    = 'revision',
                label   = 'Revision:',
                default = ''
            ),
            branch = util.ChoiceStringParameter(
                name    = 'branch',
                label   = 'Branch:',
                choices = ['master', 'release', 'devel'],
                default = 'devel'
            )
        )
    ]
    parameter_any_force_reason = util.StringParameter(
        name     = 'reason',
        label    = 'Reason:',
        default  = 'On-demand forced build',
        required = True,
        size     = 80
    )

    def __init__(self, name, repo_url, home_dir, **params):
        self.name = name
        self.repo_url = repo_url
        self.home_dir = home_dir

        self.subrepos = params.get('subrepos', False)

        self.metadata = self._init_metadata(**params['metadata'])
        self.build_setup = self._init_build_setup(**params['build'])
        self.build_modules = self._init_build_modules(**params['build'])
        self.build = self._init_build_sequence(**params['build'])
        self.distros = self._init_distros(params['distributions'])

    def _init_metadata(self, **metadata):  # pylint: disable=locally-disabled,no-self-use
        result = {}
        for key in ('homepage', 'description', 'bugtrack', 'master_repo'):
            result[key] = metadata.get(key, None)
        return result

    def _init_build_setup(self, **build_params):  # pylint: disable=locally-disabled,no-self-use
        if 'setup' in build_params:
            return AlchemistBuildSetup(self, **build_params['setup'])
        return None

    def _init_build_modules(self, **build_params):  # pylint: disable=locally-disabled,no-self-use
        if 'modules' not in build_params:
            raise ValueError(
                "Missing list of available build modules for project %s" % self.name
            )

        result = {}
        for module_name, module_data in build_params['modules'].items():
            if module_name in result:
                raise ValueError(
                    "Module %s is defined twice for project %s" % (module_name, self.name)
                )

            module_type = module_data.setdefault('mtype', module_name)
            if module_type not in ALCHEMIST_BUILD_MODULES:
                raise ValueError(
                    "Invalid module type %s defined for project %s" % (module_type, self.name)
                )

            module_class = ALCHEMIST_BUILD_MODULES[module_type]
            result[module_name] = module_class(self, module_name, **module_data)

        return result

    def _init_build_sequence(self, **build_params):  # pylint: disable=locally-disabled,no-self-use
        if 'sequence' not in build_params:
            raise ValueError(
                "Missing build sequence definition for project %s" % self.name
            )
        return AlchemistBuildSequence(self, build_params['sequence'])

    def _init_distros(self, distros):  # pylint: disable=locally-disabled,no-self-use
        result = []
        for distro in distros:
            result.append(AlchemistDistro(self, **distro))
        return result

    def __str__(self):
        return self.name

    def __repr__(self):
        return 'AlchemistProject(%s, m: %s, d: %s, b: %s)' % (
            self.name,
            repr(self.build_modules),
            repr(self.distros),
            repr(self.build)
        )

    #---------------------------------------------------------------------------

    def module_exists(self, module_name):
        """
        Check that given build module exists.
        """
        return module_name in self.build_modules

    def get_build_sequence(self):
        """
        Return list containing full build sequence for this project.
        """
        return self.build.get_builder_names()

    def get_all_builder_names(self):
        """
        Get list of all configured builder modules.
        """
        result = ['%s-full' % self.name]
        for module_name in self.build_modules:
            result.append('%s-%s' % (self.name, module_name))
        return result

    #---------------------------------------------------------------------------

    def generate_change_filter(self):
        """
        Doc: https://docs.buildbot.net/current/manual/cfg-schedulers.html#change-filters
        """
        return util.ChangeFilter(
            repository=self.repo_url
        )

    def gen_sch_checkout(self):
        """
        Generate checkout scheduler for this Alchemist project.
        """
        scheduler_name = 'sch-checkout-%s' % self.name
        builder_name   = '%s-full' % self.name
        scheduler = schedulers.AnyBranchScheduler(
            name            = scheduler_name,
            change_filter   = self.generate_change_filter(),
            treeStableTimer = 5,
            builderNames    = [builder_name],
            fileIsImportant = is_important_always,
            properties      = {
                'project': self.name,
                'reason': "Build of project '%s' triggered by repository update" % self.name
            }
        )

        LOGGER.info(
            "[%s] Generated CHECKOUT SCHEDULER '%s' for builder '%s'",
            self.name,
            scheduler_name,
            builder_name
        )
        return [scheduler]

    def gen_sch_force(self):
        """
        Generate all force schedulers for this Alchemist project.
        """
        scheduler_name = 'sch-force-%s' % self.name
        builder_names  = self.get_all_builder_names()
        scheduler = schedulers.ForceScheduler(
            name         = scheduler_name,
            buttonName   = 'Force:%s' % self.name,
            builderNames = self.get_all_builder_names(),
            codebases    = self.parameter_any_force_codebases,
            reason       = self.parameter_any_force_reason
        )

        LOGGER.info(
            "[%s] Generated FORCE SCHEDULER '%s' for builders '%s'",
            self.name,
            scheduler_name,
            ','.join(builder_names)
        )
        return [scheduler]

    def gen_sch_try(self):
        """
        Generate try scheduler for this Alchemist project.
        """
        return [schedulers.Try_Jobdir(
            name         = 'sch-try-%s' % self.name,
            builderNames = ['%s-check' % self.name],
            jobdir       = 'tryjobs-%s' % self.name,
            properties   = {
                'project': self.name,
                'reason': "On-demand build of project '%s' without codebase checkout" % self.name
            }
        )]

    def gen_sch_triggers(self):
        """
        Generate all trigger schedulers for this Alchemist project.
        """
        result = []
        for module_name in sorted(self.build_modules.keys()):
            scheduler_name = 'sch-trg-%s-%s' % (self.name, module_name)
            builder_name   = '%s-%s' % (self.name, module_name)
            result.append(
                schedulers.Triggerable(
                    name         = scheduler_name,
                    builderNames = [builder_name]
                )
            )
            LOGGER.info(
                "[%s] Generated TRIGGER SCHEDULER '%s' for builder '%s'",
                self.name,
                scheduler_name,
                builder_name
            )
        return result

    def gen_builders(self):
        """
        Generate all builder configurations for this Alchemist project.
        """
        result = []
        trs = []

        for module in self.build_modules.values():
            result.append(module.generate_builder())

        for module_name in self.get_build_sequence():
            trigger_name = 'sch-trg-%s' % module_name
            trs.append(steps.Trigger(
                name            = 'do:%s' % module_name,
                description     = 'triggering %s' % module_name,
                descriptionDone = 'done:%s' % module_name,
                schedulerNames  = [trigger_name],
                waitForFinish   = True,
                haltOnFailure   = True
            ))
            LOGGER.info(
                "[%s] Generated TRIGGER STEP for scheduler '%s'",
                self.name,
                trigger_name
            )
        builder_name = '%s-full' % self.name
        result.append(util.BuilderConfig(
            name        = builder_name,
            workernames = ['worker-master'],
            factory     = util.BuildFactory(trs),
            tags        = ['project-%s' % self.name, 'build-full']
        ))
        LOGGER.info(
            "[%s] Generated BUILDER '%s'",
            self.name,
            builder_name
        )

        return result
