"""
Package containing helper functionality to make use of
the three different protocols used in this project:

  * Module :mod:`protocols.api <p2p_nse5.protocols.api>` is responsible
    for interacting with the other modules of the VoidPhone P2P application
    (e.g. the Gossip module as server or the RPS module as client)
  * Module :mod:`protocols.p2p <p2p_nse5.protocols.p2p>` is responsible
    for handling the protocol messages which are delivered by Gossip
    and are used to spread information about the network size
"""
