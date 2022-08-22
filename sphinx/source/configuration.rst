.. _configuration:

=============
Configuration
=============

.. toctree::

The configuration of the NSE module is stored in an `INI <https://en.wikipedia.org/wiki/INI_file>`_
format file. It's usually named ``config.ini``, but that doesn't matter. A sane default
configuration looks like the following snippet:

.. literalinclude:: _static/default_configuration.ini
    :language: ini

.. only:: builder_html

    Download the default configuration file
    :download:`default_configuration.ini <_static/default_configuration.ini>`
    and adopt it to your needs before starting the program.

The configuration file may contain more key-value pairs which aren't listed
on the following page. Those will be ignored and won't raise any errors.

Global settings
----------------

There may be a top-level section called ``global`` which contains the single key
``hostkey``. It contains the path to a RSA 4096-bit public & private key pair
stored in PEM format. If the section ``global`` is absent, this key must be
the very first entry in the configuration file. Otherwise parsing it may fail.

Gossip settings
---------------

The Gossip section may provide any number of key-value pairs. The only key required
by the NSE module is the ``api_address``. It stores an IP address and port where
a running Gossip module can be reached. That network address should be given as
``<ip_address>:<port>``. Use ``[`` and ``]`` to separate the address from port number
in case of an IPv6 address, for example ``[2001:4ca0:2001:11:226:b9ff:fe7d:84ed]:6001``.

.. note::

    The NSE module heavily depends on the Gossip module to distribute its
    messages in the network. In case the Gossip module is unreachable at
    startup, the program will terminate. If the connection suddenly drops, the
    NSE module will try to reconnect to it permanently, but it can't provide new
    information about the network size (therefore using the most recent values).

.. warning::

    Currently, using hostnames instead of IP addresses doesn't work reliably.

.. warning::

    Support for IPv6 addresses is not as tested as support for IPv4 addresses.

NSE settings
------------

API module
~~~~~~~~~~

.. TODO

Logging
~~~~~~~

.. TODO
    `basicConfig <https://docs.python.org/3/library/logging.html#logging.basicConfig>`_

Database
~~~~~~~~

The database configuration is required in order to properly store peer
identities and history information persistently. The program has been
tested with SQLite and MariaDB databases, but everything supported
by SQLAlchemy should work. There's a key ``database`` which must be the
correct and full database URL ("connection string") to the database
used by this module. See the explanation about database URLs in the
`SQLAlchemy docs <https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls>`_
for more information or head directly to the specification of them in
`RFC 1738 <https://rfc.net/rfc1738.html>`_ (examples of such connection
strings are ``sqlite:///./nse.db`` and ``mysql://user:password@localhost/nse``).

.. note::

    Here's a list of some suggested external drivers for various databases:

      * `sqlite3 <https://docs.python.org/3/library/sqlite3.html>`_
        comes pre-installed with the Python standard library
      * `pymysql <https://pypi.org/project/PyMySQL>`_ is a pure-Python MySQL driver
      * `mysqlclient <https://pypi.org/project/mysqlclient>`_
        is a MySQL driver using the MySQL C libraries
      * `psycopg2 <https://pypi.org/project/psycopg2>`_ is the most popular
        database driver for PostgreSQL

NSE details
~~~~~~~~~~~

.. TODO
