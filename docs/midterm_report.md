# P2P Midterm Report

## Information

Team name: NSE-5

GitLab repository: [`NSE-5`](https://gitlab.lrz.de/netintum/teaching/p2psec_projects_2022/NSE-5)

Names of team members:

 - Christian Plass (`ge96raf`)
 - Luis Kleinheinz (`ge96cek`)

Chosen module: NSE

## Changes to your assumptions in the initial report

We wanted to implement the **GNUnet NSE** algorithm, and we stick to this decision.

We also wanted to target **GNU+Linux** as operating system, which we also stick to. Debian GNU/Linux will be the main distribution of our tests.
Furthermore, **Python3** (at least v3.9) is used as implementation language, as outlined in the initial report.

One thing we couldn't achieve until now is writing unittests for our module implementation, but this may be done in the future.

Regarding additional libraries, we now make use of the following third-part libraries:

- `pydantic` for validating and mapping configuration files to pydantic's dataclasses
- `pycryptodome` for easy handling of RSA public & private keys
- `SQLAlchemy` for interacting with a small SQLite database for persistent storage

## Architecture of your module

### Logical structure

The `APIServer` (`server` module) is the main class of our implementation which handles incoming queries of other modules.
It's capable of handling `NSE_QUERY` and `GOSSIP_NOTIFICATION` messages (both processed by the `nse` module).
It makes use of some other helper functionalities in the other modules, e.g. for message parsing (`protocols` package), database handling (`persistence` module) and configuration loading (`config` module).

### Process architecture

Our implementation doesn't make use of threads, because it would interfere with our usage of Python's asynchronous capabilities via `asyncio`.
Furthermore, we only spawn one worker process, even though that means certain limitations through the Python GIL.

### Networking

It's a TCP-based `asyncio` server which receives API connections from other modules on localhost and answers those requests.

### Security measures

We generally don't trust any incoming data. This means we strongly check all incoming messages for validity and drop anything invalid.

The P2P messages of our protocol require a proof of work (as described in the GNUnet specification) to make it harder for adversaries to launch a Sybil attack.
The P2P message itself isn't encrypted but signed with the RSA public key of the sender, which is also included in the message.

The API specification doesn't allow or require using encryption. Data at rest isn't encrypted, either.

## The peer-to-peer protocol

### Message formats

Our P2P message is derived from the official GNUnet NSE [technical report](https://grothoff.org/christian/nse-techreport.pdf).
It was changed in various aspects, e.g. in making Sybil attacks even harder by hashing the current round time and proximity together with the RSA public key, and is described below:

```
2 bytes    | hop count (updated at each relaying peer)
1 byte     | reserved for future use (currently ignored)
1 byte     | claimed proximity in bits
2 bytes    | length of the RSA public key in bytes (see below)
8 bytes    | time of the round as UNIX timestamp
8 bytes    | random nonce for the proof of work
var bytes  | RSA public key in DEM binary format
512 bytes  | 4096-bit RSA signature of everything except the first 2 bytes
```

Those P2P messages are exchanged via the Gossip transport.

For API message formats consult the specification document.

### Reasoning why the messages are needed

It wouldn't work otherwise. GNUnet NSE is no passive algorithm but rather has to send its "flood messages".

### Exception handling

Invalid or corrupted incoming messages are silently ignored.

Connection breaks to the Gossip module are considered rare, but they are handled by repeating reconnection attempts.

## Future Work

Connecting the different parts of our implementation hasn't been finished so far. Furthermore, the GNUnet NSE algorithm itself hasn't been finished as we wanted to focus on the `APIServer` implementation first.

One thing we couldn't achieve until now is writing unittests for our module implementation, but this may be done in the future.
Using multiple processes on different ports would probably increase module throughput. However, this requires to use a productive database server, since a SQLite file is not performant enough.

## Workload Distribution

Since we haven't completely finished the project yet, the following is the preliminary result:

Chris spend more time writing a configuration, setting up the database and CI pipeline and starting a project layout.

Luis spend more time implementing the API server and getting started with Python networking.

## Effort spent for the project

Issue | Name | Chris | Luis
--- | --- | --- | ---
1 | Initial Report | 1h 45m | 1h 45m 
2 | Basic Project Structure | 3h 15m | 2h
3 | Mid-term Report | 2h 15m | 2h 15m
4 | CI Pipeline | 45m | 0m
5 | Researching | 2h 15m | 3h
6 | Designing our P2P Protocol | 2h | 1h 
7 | Documenting | 0m | 0m
8 | API server | 1h | 4h
9 | Database & configuration | 2h 30m | 0m
||||
| | Total | 15h 45m | 14h
