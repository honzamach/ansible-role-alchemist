.. _section-role-alchemist:

Role **alchemist**
================================================================================

Ansible role for convenient installation of the automated build system Alchemist.

* `Ansible Galaxy page <https://galaxy.ansible.com/honzamach/alchemist>`__
* `GitHub repository <https://github.com/honzamach/ansible-role-alchemist>`__
* `Travis CI page <https://travis-ci.org/honzamach/ansible-role-alchemist>`__


Description
--------------------------------------------------------------------------------


This role is responsible for provisioning of **Alchemist** server.

.. note::

    This role supports the :ref:`template customization <section-overview-customize-templates>` feature.


Requirements
--------------------------------------------------------------------------------

This role does not have any special requirements.


Dependencies
--------------------------------------------------------------------------------


This role is dependent on following roles:

* :ref:`accounts <section-role-accounts>`
* :ref:`certified <section-role-certified>`
* :ref:`shibboleth <section-role-shibboleth>`

No other roles have direct dependency on this role.


Managed files
--------------------------------------------------------------------------------

This role directly manages content of following files on target system:

* ``/etc/syslog-ng/syslog-ng.conf``


Role variables
--------------------------------------------------------------------------------


.. envvar:: hm_alchemist__custom_repositories

    List of desired custom Ansible playbook repositories.

    * *Occurence:* **optional**
    * *Datatype:* ``dictionary``
    * *Default value:* ``empty dictionary``


Foreign variables
--------------------------------------------------------------------------------


:envvar:`hm_accounts__users`

    Create custom Git repository for Ansible playbooks for each user.


Usage and customization
--------------------------------------------------------------------------------

This role is (attempted to be) written according to the `Ansible best practices <https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html>`__. The default implementation should fit most users,
however you may customize it by tweaking default variables and providing custom
templates.


Variable customizations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Most of the usefull variables are defined in ``defaults/main.yml`` file, so they
can be easily overridden almost from `anywhere <https://docs.ansible.com/ansible/latest/user_guide/playbooks_variables.html#variable-precedence-where-should-i-put-a-variable>`__.


Template customizations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This roles uses *with_first_found* mechanism for all of its templates. If you do
not like anything about built-in template files you may provide your own custom
templates. For now please see the role tasks for list of all checked paths for
each of the template files.


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


Example Playbook
--------------------------------------------------------------------------------

Example content of inventory file ``inventory``::

    [servers_alchemist]
    localhost

Example content of role playbook file ``playbook.yml``::

    - hosts: servers_alchemist
      remote_user: root
      roles:
        - role: honzamach.alchemist
      tags:
        - role-alchemist

Example usage::

    ansible-playbook -i inventory playbook.yml


License
--------------------------------------------------------------------------------

MIT


Author Information
--------------------------------------------------------------------------------

Jan Mach <honza.mach.ml@gmail.com>
