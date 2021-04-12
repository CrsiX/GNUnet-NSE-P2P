VoidPhone Pytest
================

This testing module features client and server ('mockup') scripts for testing
API conformity of your respective voidphone module.

The contained mockups also allow for simulation of base functionality (e.g.
information spread by the Gossip module) required for execution of higher layer
modules (e.g. the RPS module).

## Installation

Install Python3 for your operating system.

Now acquire the latest PIP distribution for your operating system. Now install
all python package dependencies for voidphone_pytest by executing

    `pip install -r requirements.txt`

in the repository root directory.

## Structure

    .
    ├── dht_client.py       -- Simple DHT API client. Can interface to DHT API Server
    ├── dht_mockup.py       -- Mockup DHT API server with local storage (simulates real DHT)
    ├── gossip_client.py    -- Simple Gossip API client. Can interface to Gossip API Server
    ├── gossip_mockup.py    -- Mockup Gossip API server. Works like a hub for all connected API clients
    ├── nse_client.py       -- Simple NSE API client. Can interface to NSE API server.
    ├── nse_mockup.py       -- Mockup NSE API server. Provides configurable NSE estimates to clients
    ├── onion_client.py     -- Onion API client. Can interface to Onion API server
    ├── README.md
    ├── requirements.txt
    ├── rps_client.py       -- Simple RPS API client. Can interface to RPS API server
    ├── rps_mockup.py       -- Mockup RPS API server. Provides configurabl RPS responses
    └── util.py

The DHT mockup provides the required store/retrieve operations, but instead of
storing the data in a real DHT, the data is stored locally in process memory.

The Gossip mockup provides the required annoncement/notification functionality
for an API client, but instead of real P2P gossip, notifications and
announcements are directly communicated between Gossip API clients, connected to
the mockup. The Gossip mockup can thus be understood as a central information
broker between multiple, connected API clients.

Both NSE and RPS mockups provide statically configured values/estimates to
connecting clients.

## Usage

Please invoke the scripts with the `-h` option to display the respective
invocation syntax and required parameters, like

    python3 dht_client.py -h

or

    ./dht_client.py -h
