#!/usr/bin/python3

import argparse
import hexdump
import socket
import struct

from Crypto.PublicKey import RSA
from rsa import PublicKey

from util import sync_bad_packet, connect_socket, sync_read_message

ONION_TUNNEL_BUILD = 560
ONION_TUNNEL_READY = 561
ONION_TUNNEL_INCOMING = 562
ONION_TUNNEL_DESTROY = 563
ONION_TUNNEL_DATA = 564
ONION_ERROR= 565
ONION_COVER= 566

ONION_ADDR = "127.0.0.1"
ONION_PORT = 7301

DEST_ADDR = "127.0.0.1"
DEST_PORT = 6304
DEST_KEY = "dest.pub"
DEST_DATA = b'foobar'

def read_pem_to_der(path):
    f = open(path, 'r')
    key = RSA.importKey(f.read())
    return key.exportKey('DER')

def alternative_read_pem_to_der(path):
    f = open(path, 'r')
    key = PublicKey.load_pkcs1(f.read(), 'PEM')
    return key.save_pkcs1('DER')

def send_onion_build(sock, addr, port, keybuf):
    # construct payload
    buflen = 4 + 4 + 4 + len(keybuf)
    buf = struct.pack(">HHHH", buflen, ONION_TUNNEL_BUILD, 0, port)
    buf += socket.inet_aton(addr)
    buf += keybuf

    print("[i] Key in DER form:\n")
    hexdump.hexdump(keybuf)
    print('')

    # Send payload
    sock.send(buf)
    print(f"[+] Sent ONION_TUNNEL_BUILD with target ({addr}:{port})")

    # wait for response and parse
    buf = sync_read_message(sock)
    msize, mtype, mtid = struct.unpack(">HHI", buf[:8])
    mder = buf[8:]

    if mtype != ONION_TUNNEL_READY:
        reason = "Received ONION_ERROR" if mtype == ONION_ERROR else f"Wrong packet type: {mtype} != {ONION_TUNNEL_READY}"
        sync_bad_packet(buf, sock, reason)

    print(f"[+] Got ONION_TUNNEL_READY:\n\tSize: {msize}\n\tTID: {mtid}\n\tKey:")
    hexdump.hexdump(mder)
    return mtid

def send_onion_data(sock, tid, data):
    # build payload
    msize = 4 + 4 + len(data)
    buf = struct.pack(">HHI", msize, ONION_TUNNEL_DATA, tid)
    buf += data
    print(f"[+] Sending ONION_DATA packet...")
    sock.send(buf)

def send_onion_cover(sock, covlen):
    # prepare payload
    buflen = 8
    buf = struct.pack(">HHHH", buflen, ONION_COVER, covlen, 0)

    sock.send(buf)
    print(f"[+] Sent ONION_COVER of length {covlen}, waiting for echo...")

    # wait for the cover traffic to be echoed back
    buf = sync_read_message(sock)
    msize, mtype, mtid = struct.unpack(">HHI", buf[:8])
    mdata = buf[8:]

    if mtype is not ONION_TUNNEL_DATA:
        sync_bad_packet(buf, s, "Wrong packet type")

    print(f"[+] Got ONION_TUNNEL_DATA:\n\tSize: {msize}\n\tTID: {mtid}\n\tData:")
    hexdump.hexdump(mdata)

def send_onion_destroy(sock, tid):
    msize = 8
    buf = struct.pack(">HHI", msize, ONION_TUNNEL_DESTROY, tid)
    sock.send(buf)
    print(f"[+] Sent ONION TUNNEL DESTROY for tid {tid}...")

def main():
    host = ONION_ADDR
    port = ONION_PORT

    peer_addr = DEST_ADDR
    peer_port = DEST_PORT
    peer_key = DEST_KEY
    onion_data = DEST_DATA
    tunnel_id = 1337

    # parse commandline arguments
    usage_string = ("Run an ONION API client. If multiple function switches are"
                    + " given, they are executed in the order: cover, build,"
                    + " data, destroy")
    cmd = argparse.ArgumentParser(description=usage_string)
    cmd.add_argument("-a", "--address",
                     help="Server address to connect to")
    cmd.add_argument("-p", "--port",
                     help="Server port to connect to")
    cmd.add_argument("-b", "--build",
                     help="Send ONION BUILD with this peer address:port to the"
                          + "server")
    cmd.add_argument("-k", "--key",
                     help="Use this key in ONION BUILD requests")
    cmd.add_argument("-d", "--data",
                     help="Send ONION DATA message with this data")
    cmd.add_argument("-i", "--tunnelid",
                     help="Set tunnel ID for standalone ONION DATA"
                          +" / DESTROY messages")
    cmd.add_argument("-c", "--cover",
                     help="Send ONION COVER message of the given length")
    cmd.add_argument("-y", "--destroy", action='store_true',
                     help="Send ONION DESTROY message")
    cmd.add_argument("-g", "--cont", action="store_true",
                     help="Optionally continue sending requests")
    args = cmd.parse_args()

    if args.address is not None:
        host = args.address

    if args.port is not None:
        port = int(args.port)

    if args.key is not None:
        peer_key = args.key

    if args.data is not None:
        if len(args.data) <= 0:
            print(f"[-] Given data must be longer than 1 byte.")
            return -1
        onion_data = bytes(args.data, encoding='utf-8')

    # Currently only supports IPv4 addresses => extend
    if args.build is not None:
        try:
            peer_addr, peer_port = args.build.split(':')
            peer_port = int(peer_port)
        except Exception as e:
            print(f"Failed to parse given peer address/port: {e}. Format should"
                  + f" be address:port")
            return -1

    if args.tunnelid is not None:
        tunnel_id = int(args.tunnelid)

    try:
        while True:
            sock = connect_socket(host, port)
            print("[+] Connected to onion module:", (host, port))

            if args.cover is not None:
                covlen = int(args.cover)
                send_onion_cover(sock, covlen)

            if args.build is not None:
                key = read_pem_to_der(peer_key)
                #key = alternative_read_pem_to_der(peer_key)
                tmpid = send_onion_build(sock, peer_addr, peer_port, key)

            if args.data is not None:
                if args.build is not None:
                    send_onion_data(sock, tmpid, onion_data)
                else:
                    send_onion_data(sock, tunnel_id, onion_data)

            if args.destroy:
                if args.build is not None:
                    send_onion_destroy(sock, tmpid)
                else:
                    send_onion_destroy(sock, tunnel_id)

            if not args.cont:
                break
            input("[i] Press enter to continue with another "
                  + " iteration of requests")
    except KeyboardInterrupt:
        pass
    sock.close()
    print("[i] Connection closed")

if __name__ == "__main__":
    main()
