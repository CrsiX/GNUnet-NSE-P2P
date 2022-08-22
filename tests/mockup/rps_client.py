#!/usr/bin/python3

import argparse
import socket
import struct

from util import sync_bad_packet, connect_socket, sync_read_message

SERV_ADDR = "127.0.0.1"
SERV_PORT = 7101

RPS_QUERY = 540
RPS_PEER = 541


def send_rps_query(sock):
    size = 4
    buf = struct.pack(f">HH",
                      size,
                      RPS_QUERY)
    sock.send(buf)
    print(f"[+] Sent RPS query...")


def main():
    host = SERV_ADDR
    port = SERV_PORT

    # parse commandline arguments
    usage_string = ("Run an RPS API client that requests a peer.")
    cmd = argparse.ArgumentParser(description=usage_string)
    cmd.add_argument("-a", "--address",
                     help="Server address to connect to")
    cmd.add_argument("-p", "--port",
                     help="Server port to connect to")
    cmd.add_argument("-g", "--cont", action='store_true',
                     help="Optionally continue sending requests")
    args = cmd.parse_args()

    if args.address is not None:
        host = args.address

    if args.port is not None:
        port = int(args.port)

    # open a socket and connect to RPS server
    s = connect_socket(host, port)

    while True:
        send_rps_query(s)
        inbuf = sync_read_message(s)

        # sanity check incoming reply
        if inbuf == b'':
            print('[-] Connection closed. Exiting.')
            s.close()
            return -1

        try:
            insize, intype, inport, nports, ipf = struct.unpack(">HHHBB",
                                                                inbuf[:8])
            portmap = {}
            for i in range(nports):
                start = 8 + i * 4
                end = start + 4
                app, port = struct.unpack(">HH", inbuf[start:end])
                portmap[app] = port

            if 1 == ipf:
                iplen = 16
            else:
                iplen = 4

            inaddr = inbuf[end:end + iplen]
            inaddr = socket.inet_ntoa(inaddr)
            inkey = inbuf[end + iplen:]

        except Exception:
            sync_bad_packet(inbuf, s)

        if intype != RPS_PEER:
            sync_bad_packet(inbuf, s, "[-] Packet not of type RPS_PEER:")

        print("[+] Received RPS_PEER:")

        print(f"\nIP address: {inaddr}\nPortmap:")
        for key in portmap.keys():
            print(f"\t{key} => {portmap[key]}")

        if not args.cont:
            break

        try:
            input("Please press enter to continue with another request"
                  + " interation")
        except KeyboardInterrupt:
            break

    s.close()


if __name__ == '__main__':
    main()
