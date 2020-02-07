.. _section-role-alchemist:

Role **alchemist**
================================================================================

.. note::

    This documentation page and role itself is still work in progress.

* `Ansible Galaxy page <https://galaxy.ansible.com/honzamach/alchemist>`__
* `GitHub repository <https://github.com/honzamach/ansible-role-alchemist>`__
* `Travis CI page <https://travis-ci.org/honzamach/ansible-role-alchemist>`__

Ansible role for convenient installation of the automated build system **Alchemist**.

**Table of Contents:**

* :ref:`section-role-alchemist-installation`
* :ref:`section-role-alchemist-dependencies`
* :ref:`section-role-alchemist-usage`
* :ref:`section-role-alchemist-variables`
* :ref:`section-role-alchemist-files`
* :ref:`section-role-alchemist-author`

This role is part of the `MSMS <https://github.com/honzamach/msms>`__ package.
Some common features are documented in its :ref:`manual <section-manual>`.


.. _section-role-alchemist-installation:

Installation
--------------------------------------------------------------------------------

To install the role `honzamach.alchemist <https://galaxy.ansible.com/honzamach/alchemist>`__
from `Ansible Galaxy <https://galaxy.ansible.com/>`__ please use variation of
following command::

    ansible-galaxy install honzamach.alchemist

To install the role directly from `GitHub <https://github.com>`__ by cloning the
`ansible-role-alchemist <https://github.com/honzamach/ansible-role-alchemist>`__
repository please use variation of following command::

    git clone https://github.com/honzamach/ansible-role-alchemist.git honzamach.alchemist

Currently the advantage of using direct Git cloning is the ability to easily update
the role when new version comes out.


.. _section-role-alchemist-dependencies:

Dependencies
--------------------------------------------------------------------------------

This role is dependent on following roles:

* :ref:`accounts <section-role-accounts>`
* :ref:`certified <section-role-certified>`
* :ref:`shibboleth <section-role-shibboleth>`

No other roles have dependency on this role.


.. _section-role-alchemist-usage:

Usage
--------------------------------------------------------------------------------

Example content of inventory file ``inventory``::

    [servers_alchemist]
    your-server

Example content of role playbook file ``role_playbook.yml``::

    - hosts: servers_alchemist
      remote_user: root
      roles:
        - role: honzamach.alchemist
      tags:
        - role-alchemist

Example usage::

    # Run everything:
    ansible-playbook --ask-vault-pass --inventory inventory role_playbook.yml


.. _section-role-alchemist-variables:

Configuration variables
--------------------------------------------------------------------------------


Internal role variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. envvar:: hm_alchemist__remove_packages

    List of packages defined separately for each linux distribution and package manager,
    that MUST NOT be present on target system. Any package on this list will be removed
    from target host. This role currently recognizes only ``apt`` for ``debian``.

    * *Datatype:* ``dict``
    * *Default:* (please see YAML file ``defaults/main.yml``)
    * *Example:*

    .. code-block:: yaml

        hm_alchemist__remove_packages:
          debian:
            apt:
              - syslog-ng
              - ...

.. envvar:: hm_alchemist__install_packages

    List of packages defined separately for each linux distribution and package manager,
    that MUST be present on target system. Any package on this list will be installed on
    target host. This role currently recognizes only ``apt``, ``pip3`` and ``pip2`` for
    ``debian``.

    * *Datatype:* ``dict``
    * *Default:* (please see YAML file ``defaults/main.yml``)
    * *Example:*

    .. code-block:: yaml

        hm_alchemist__install_packages:
          debian:
            apt:
              - syslog-ng
              - ...
            pip3:
              - setuptools

.. envvar:: hm_alchemist__home_buildmaster

    Home directory for Buildbot master.

    * *Datatype:* ``string``
    * *Default:* ``/home/buildbot/master``

.. envvar:: hm_alchemist__home_buildworkers

    Home directory for local buildbot workers.

    * *Datatype:* ``string``
    * *Default:* ``/home/buildbot/workers``

.. envvar:: hm_alchemist__home_projects

    Home directory for all projects.

    * *Datatype:* ``string``
    * *Default:* ``/var/projects``

.. envvar:: hm_alchemist__account_buildbot

    Name of the Buildbot user account.

    * *Datatype:* ``string``
    * *Default:* ``buildbot``

.. envvar:: hm_alchemist__change_port

    Port number for listening for changes.

    * *Datatype:* ``integer``
    * *Default:* ``9999``

.. envvar:: hm_alchemist__change_user

    Change authentication: user

    * *Datatype:* ``string``
    * *Default:* ``change``

.. envvar:: hm_alchemist__change_passwd

    Change authentication: password

    * *Datatype:* ``string``
    * *Default:* ``changepw``

.. envvar:: hm_alchemist__worker_port

    Buildbot worker configuration: Port number.

    * *Datatype:* ``integer``
    * *Default:* ``9989``

.. envvar:: hm_alchemist__worker_passwd

    Buildbot worker configuration: Password.

    * *Datatype:* ``string``
    * *Default:* ``workerpasswd``


Foreign variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


:envvar:`hm_accounts__users`

    Create custom Git repository for Ansible playbooks for each designated user.


.. _section-role-alchemist-files:

Managed files
--------------------------------------------------------------------------------

.. note::

    This role supports the :ref:`template customization <section-overview-role-customize-templates>` feature.

This role manages content of following files on target system:

* ``/etc/....conf``


.. _section-role-alchemist-author:

Author and license
--------------------------------------------------------------------------------

| *Copyright:* (C) since 2019 Honza Mach <honza.mach.ml@gmail.com>
| *Author:* Honza Mach <honza.mach.ml@gmail.com>
| Use of this role is governed by the MIT license, see LICENSE file.
|
