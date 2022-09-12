.. _nse_protocol:

================
NSE P2P protocol
================

.. toctree::

Structure of P2P messages
-------------------------

+-----+-----------+----------------------------------------------------------------------+--------+
| No. | Size      | Description                                                          | Hashed |
+=====+===========+======================================================================+========+
| 1   | 1 byte    | version field, reserved for future use (currently ignored)           | False  |
+-----+-----------+----------------------------------------------------------------------+--------+
| 2   | 2 bytes   | hop count (updated at each relaying peer, relevant in P2P mode only) | False  |
+-----+-----------+----------------------------------------------------------------------+--------+
| 3   | 1 byte    | claimed proximity in bits                                            | True   |
+-----+-----------+----------------------------------------------------------------------+--------+
| 4   | 2 bytes   | length of the RSA public key in bytes (see below)                    | True   |
+-----+-----------+----------------------------------------------------------------------+--------+
| 5   | 8 bytes   | time of the round as UNIX timestamp                                  | True   |
+-----+-----------+----------------------------------------------------------------------+--------+
| 6   | 8 bytes   | random nonce for the proof of work                                   | True   |
+-----+-----------+----------------------------------------------------------------------+--------+
| 7   | var bytes | RSA public key in DEM binary format                                  | True   |
+-----+-----------+----------------------------------------------------------------------+--------+
| 8   | 512 bytes | 4096-bit RSA signature of everything except the first 2 bytes        | False  |
+-----+-----------+----------------------------------------------------------------------+--------+

The ``Hashed`` column specifies whether the field is part of the proof of work
challenge. This proof of work is calculated as the SHA256 hash of the
concatenation of all those five fields. If that hash has it's first `x` bits
set to zero, the proof of work is valid (where `x` is a natural number between
0 and 255).

.. note::

    The field ``hop count`` is currently ignored, since we're using the
    Gossip module for spreading those packets in the network. However,
    it would be possible to use it in a future project, where reliance
    on another transport module isn't possible, or when the Gossip
    module is only used to spread information about existing peers,
    so that the NSE module would try to connect itself to other peers.
    To sum it up, leaving ``hop count`` in place was a design decision
    for future extensibility. Same applies to the ``version`` field.
