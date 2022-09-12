.. P2P Network Size Estimation documentation master file, created by
   sphinx-quickstart on Mon Jun 13 23:52:06 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Documentation for P2P Network Size Estimation
=============================================

This project aims at implementing a Network Size Estimation (NSE) service
in an unstructured P2P network in the context of a VoIP application.
It uses the GNUnet NSE algorithm in a slightly changed configuration
to estimate the number of peers that are actively participating in the P2P
network. It relies on another module, Gossip, to work properly.

.. TODO: Write short summary of the project

Most important libraries used in this project:

  * `PyCryptodome <https://www.pycryptodome.org/>`_ for handling RSA keys and their functionality
  * `Pydantic <https://pydantic-docs.helpmanual.io>`_ for some convenience
    features while parsing and handling the configuration
  * `SQLAlchemy <https://sqlalchemy.org>`_ as SQL database ORM for SQLite or MySQL/MariaDB

Table of contents
-----------------

.. toctree::
    :maxdepth: 2

    installation
    configuration
    nse_protocol
    codebase/index
    license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
