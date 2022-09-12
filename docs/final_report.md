# P2P Final Report

Team name: NSE-5

GitLab repository: [`NSE-5`](https://gitlab.lrz.de/netintum/teaching/p2psec_projects_2022/NSE-5)

Names of team members:

 - Christian Plass (`ge96raf`)
 - Luis Kleinheinz (`ge96cek`)

Chosen module: NSE

## Program docs

We've built a whole documentation of the project and our source code using `sphinx`.
It can be automatically generated using `make html` in the `sphinx/` directory.
There's also a set of pre-built HTML pages in the `docs/final_report/` directory, which
allow to easily read the documentation in the `docs/final_report/index.html` file.

## Changes to assumptions in the midterm report

We mostly stuck to the assumptions lined out in the midterm report.

There are some notable changes we made since then, though:

1. The message format for our P2P messages has slightly changed. The reserved field was moved
   to the beginning of the structure and marked as a version field. That's because having a 
   version field allows for later extension easily. Furthermore, one reserved byte was not very useful.
2. We re-structured parts of the implementation, e.g. the `APIServer` does not exist anymore
   and was replaced by specific protocol handlers.
3. We've implemented a bunch of improvements to the configuration, docs and CLI utility features
   that make working with our project much easier.

## Architecture of the package

### Logical structure

The `Manager` class from the `entrypoint` module is the main class of our implementation,
since it schedules NSE rounds and starts the Gossip client and the NSE server protocol.
The Gossip client reacts to `GOSSIP_NOTIFICATION` messages from the Gossip transport,
while the NSE server reacts to `NSE_QUERY` messages from any incoming TCP connection
(which may be limited to localhost connections, though). The NSE scheduler executes
the `RoundHandler` (from `nse.py`) for every new iteration of the network flooding mechanism.

Other modules:

 - `persistence`: provides database models and session utilities
 - `config`: holds configuration format and loading utilities
 - `utils`: provides generic helpers not directly related to other modules, e.g. the CLI
 - `protocols`: this package provides abstractions to the API and P2P protocols used by higher-level modules

### Process architecture

Our implementation doesn't make use of threads, because it would interfere with our usage of Python's asynchronous capabilities via `asyncio`.
Furthermore, we only spawn one worker process, even though that means certain limitations through the Python GIL.

### Networking

It's a TCP-based `asyncio` server which receives API connections from other modules on localhost and answers those requests,
together with two other `asyncio`-based client protocols for NSE flooding and communication with Gossip.

### Security measures

We generally don't trust any incoming data. This means we strongly check all incoming messages for validity and drop anything invalid.

The P2P messages of our protocol require a proof of work (as described in the GNUnet specification) to make it harder for adversaries to launch a Sybil attack.
The P2P message itself isn't encrypted but signed with the RSA public key of the sender, which is also included in the message.
To make pre-processing of flood messages even harder, the public key must be hashed along its proximity and the current round.

The API specification doesn't allow or require using encryption. Data at rest isn't encrypted, either.

### Tree view

    NSE-5/
    |-- default_configuration.ini
    |-- docs/
    |   |-- final_report/
    |   |-- final_report.md
    |   |-- initial_report.md
    |   `-- midterm_report.md
    |-- LICENSE
    |-- p2p_nse5/
    |   |-- config.py
    |   |-- entrypoint.py
    |   |-- gossip.py
    |   |-- __init__.py
    |   |-- __main__.py
    |   |-- nse.py
    |   |-- persistence.py
    |   |-- protocols/
    |   |   |-- api.py
    |   |   |-- __init__.py
    |   |   `-- p2p.py
    |   `-- utils.py
    |-- README.md
    |-- requirements.txt
    |-- sphinx/
    |   |-- make.bat
    |   |-- Makefile
    |   |-- requirements.txt
    |   |-- source/
    |   |   |-- codebase/
    |   |   |   |-- config.rst
    |   |   |   |-- entrypoint.rst
    |   |   |   |-- gossip.rst
    |   |   |   |-- index.rst
    |   |   |   |-- nse.rst
    |   |   |   |-- persistence.rst
    |   |   |   |-- protocols.rst
    |   |   |   `-- utils.rst
    |   |   |-- conf.py
    |   |   |-- configuration.rst
    |   |   |-- index.rst
    |   |   |-- installation.rst
    |   |   |-- license.rst
    |   |   |-- nse_protocol.rst
    |   |   |-- _static/
    |   |   `-- _templates/
    `-- tests/
        |-- cli.py
        |-- correctness.py
        |-- __init__.py
        |-- __main__.py
        |-- mockup/
        |-- private_keys/
        |-- static/
        |-- tools.py
        `-- utils.py

## Future work

To make it faster than the speed of light, we could rewrite it in Rust™.

One conceptual improvement could be to implement a direct communication channel between the NSE modules
to achieve higher throughput and allow for some higher-level features like notifications (the original
GNUnet protocol proposes to send a high proximity message to other peers with low proximity directly).

## Workload Distribution

Chris spend more time implementing the project's tests, utilities, config and protocols.

Luis spend more time implementing the first API server and getting started with Python networking.

The project structure as well its required protocols were conceived together.
We also proof-read each other's code regularly, too.

## Effort spent for the project

Issue | Name | Chris | Luis
--- | --- | --- | ---
1 | Initial Report | 1h 45m | 1h 45m 
2 | Basic Project Structure | 3h 15m | 2h
3 | Mid-term Report | 2h 15m | 2h 15m
4 | CI Pipeline | 45m | 0m
5 | Researching | 3h | 4h
6 | Designing our P2P Protocol | 2h | 1h 
7 | Documenting | 5h 45m | 0m
8 | API server | 7h 15m | 5h
9 | Database & configuration | 5h | 2h
10 | Gossip client | 3h 40m | 1h
11 | Unittests | 9h 30m | 1h 30m
12 | IP addresses only | 0m | 0m
13 | Incoming messages | 2h 50m | 4h
14 | Default config | 1h 30m | 0m
15 | Endterm report | 2h 15m | 2h 15m 
16 | Horizontal communication | 0m | 0m
||||
| | Total | 50h 45m | 26h 45m
