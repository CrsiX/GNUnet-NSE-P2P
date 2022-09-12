.. _installation:

============
Installation
============

.. toctree::

System requirements
-------------------

Around 70 MiB of RAM and a single CPU core are fine
to run the NSE module, but the more the better.

This project was developed under and tested with Debian GNU/Linux. It might
work with other operating systems of the Linux family as well as other
UNIX systems, as long as those support the required libraries. We do not
"officially" support Windows and Mac OS and have no plans to do so.

Prerequisites
-------------

It's recommended to use another system user with almost no privileges
to run the module for security purposes, e.g. ``nse`` or ``nse5``.
Choose a name and stick to it during this setup. A simple tool to
create a new user on a Debian-like machine is ``adduser``.

You need to have at least `Python 3.9 <https://www.python.org/downloads>`_
with ``pip`` and ``venv`` installed on your system. Those can be installed
using ``apt install python3-pip python3-venv`` on Debian-like systems and
using ``dnf install python3-pip`` on Fedora-like systems.

Even though the API works with a single SQLite database, it's highly
recommended to utilize a deployment-grade database server. MySQL and MariaDB
are currently "officially" supported, but all SQL database backends with
drivers for ``sqlalchemy`` should be fine, too.

Additionally, you either need ``git`` or download the project files as archive.

Database configuration
----------------------

For a SQLite database, the following steps are not required.

Log into your database server. It requires an account that can create
users, databases and set privileges. You can choose any user and database name
you want. **Do not forget to change the password of the new database user!**
For a MySQL / MariaDB server, the following snippet should do the trick:

.. code-block:: sql

    CREATE USER 'nse5'@localhost IDENTIFIED BY 'password';
    CREATE DATABASE nse5_db;
    GRANT ALL PRIVILEGES ON nse5_db.* TO 'nse5'@localhost;
    FLUSH PRIVILEGES;

In case you want to be able to perform unittests with the database,
you should also create a second database and call it something like
``nse5_test`` or so, because it may be cleared by the unittests.

Installation instructions
-------------------------

The following steps should be executed as your target user (e.g. ``nse`` or ``nse5``).

1. Clone the repository or copy the whole project to your server and ``cd`` into it.
2. Create and enable a virtual environment for the Python packages:

    .. code-block::

        python3 -m venv venv
        source venv/bin/activate

3. Install the minimally required Python packages:

    .. code-block::

        pip3 install -r requirements.txt

    .. note::

        We don't enforce any database drivers as dependencies in the
        ``requirements.txt`` file. The database driver must be installed extra.
        We "officially" support SQLite and MySQL / MariaDB, but everything
        supported by `SQLAlchemy <https://docs.sqlalchemy.org/en/14/dialects>`_
        may work. See :ref:`configuration` for more information.

    .. note::

        On Alpine Linux, you need the additional packages ``gcc``, ``g++`` and
        ``libc-dev``. On Debian GNU/Linux, you may need the ``build-essential`` package.

4.  Choose a configuration filename, e.g. ``config.ini``, and create a new config file:

    .. code-block::

        python3 -m p2p_nse5 new -c config.ini

5.  Edit the newly created configuration file ``config.ini``.
    Refer to :ref:`configuration` for more information about
    available options and their meaning. To get started quickly,
    it's enough to just configure the following values:

      * the path to the host key file (RSA 4096-bit private key in PEM format)
      * the API address of the Gossip module
      * the API address of the NSE module
      * the database connection string (if omitted, a temporary SQLite will be used)

    .. note::

        If you don't have a RSA 4096-bit private key yet, you can generate a
        fresh one with the following command:

        .. code-block::

            python3 -m p2p_nse5 generate <path>

        **Do not re-use any private key previously used in other projects!**

Execution
---------

You can now easily start the NSE module and API using the ``run`` command:

.. code-block::

    $ python3 -m p2p_nse5 run --help
    usage: p2p_nse5 run [-h] [-c <file>] [-d <URL>] [-g <address>] [-l <address>] [-p <file>]

    optional arguments:
      -h, --help    show this help message and exit
      -c <file>     configuration filename (defaults to 'default_configuration.ini')
      -d <URL>      overwrite full database connection string
      -g <address>  overwrite address of the Gossip API server
      -l <address>  overwrite local API listen address
      -p <file>     overwrite path to the RSA private key

.. code-block::

    python3 -m p2p_nse5 run

Systemd service
---------------

On systemd-enabled systems, it's recommended to add a systemd service
to start the NSE module API automatically. A sample unit file for systemd
is shown below. Note that since the NSE module requires the Gossip module
to be reachable at startup, it should have a dependency for the other
service. Don't blindly copy this example, make sure that it fits your needs:

.. code-block:: ini

    [Unit]
    Description=P2P NSE(5) module API
    After=network-online.target p2p-gossip.service
    Wants=network-online.target p2p-gossip.service

    [Service]
    Type=simple
    ExecStart=/srv/NSE-5/venv/bin/python3 -m p2p_nse5 run -c config.ini
    User=nse5
    WorkingDirectory=/srv/NSE-5
    Restart=always
    SyslogIdentifier=p2p-nse5

    [Install]
    WantedBy=multi-user.target
