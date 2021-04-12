#!/usr/bin/python3

import argparse
import hexdump
import socket
import struct
import sys

from util import sync_bad_packet, connect_socket, sync_read_message

NSE_ADDR = '127.0.0.1'
NSE_PORT = 7201

NSE_QUERY = 520
NSE_ESTIMATE = 521

def send_nse_query(sock):
    msize = 4
    buf = struct.pack(">HH", msize, NSE_QUERY)
    sock.send(buf)
    print("[+] Sent NSE QUERY...")

def main():
    host = NSE_ADDR
    port = NSE_PORT

    # parse commandline arguments
    usage_string = ("Run an NSE API client.")
    cmd = argparse.ArgumentParser(description=usage_string)
    cmd.add_argument("-a", "--address",
                     help="Server address to connect to")
    cmd.add_argument("-p", "--port",
                     help="Server port to connect to")
    cmd.add_argument("-g", "--cont", action="store_true",
                     help="Optionally continue sending requests")
    args = cmd.parse_args()

    if args.address is not None:
        host = args.address

    if args.port is not None:
        port = int(args.port)

    sock = connect_socket(host, port)
    print("[+] Connected to NSE module:", (host, port))

    while True:
        send_nse_query(sock)
        msg = sync_read_message(sock)

        try:
            msize, mtype, peers, dev = struct.unpack(">HHII", msg)
        except Exception as e:
            sync_bad_packet(msg, sock, f"{e}")

        if mtype != NSE_ESTIMATE:
            sync_bad_packet(msg, sock, f"Unexpected mtype {mtype} received")

        print(f"[+] Received NSE_ESTIMATE({peers}, {dev})")

        if not args.cont:
            break

        try:
            input("Press enter to send another request")
        except KeyboardInterrupt:
            print(f"\n[i] SIGINT received, shutting down")
            break

    sock.close()

if __name__ == "__main__":
    main()
