#!/usr/bin/python3

import argparse
import asyncio
import socket
import struct

from util import bad_packet, read_message, handle_client

NSE_ADDR = "127.0.0.1"
NSE_PORT = 7201
NSE_PEER_ESTIMATE = 1337
NSE_DEVIATION = 42

NSE_QUERY = 520
NSE_ESTIMATE = 521


async def handle_nse_query(buf, reader, writer):
    raddr, rport = writer.get_extra_info('socket').getpeername()
    print(f"[+] {raddr}:{rport} >>> NSE_QUERY")

    msize = 12
    buf = struct.pack(">HHII", msize, NSE_ESTIMATE,
                      NSE_PEER_ESTIMATE,
                      NSE_DEVIATION)

    try:
        writer.write(buf)
        await writer.drain()
    except Exception as e:
        print(f"[-] Failed to send NSE_ESTIMATE: {e}")
        await bad_packet(reader, writer)
        return False

    print(f"[+] {raddr}:{rport} <<< NSE_ESTIMATE({NSE_PEER_ESTIMATE}, "
          + f"{NSE_DEVIATION})")

    return True


async def handle_message(buf, reader, writer):
    ret = False
    header = buf[:4]
    body = buf[4:]

    mtype = struct.unpack(">HH", header)[1]
    if mtype == NSE_QUERY:
        ret = await handle_nse_query(buf, reader, writer)
    else:
        await bad_packet(reader, writer,
                         f"Unknown message type {mtype} received",
                         header)
    return ret


def main():
    global NSE_PEER_ESTIMATE, NSE_DEVIATION
    host = NSE_ADDR
    port = NSE_PORT

    # parse commandline arguments
    usage_string = ("Run an NSE module mockup.")
    cmd = argparse.ArgumentParser(description=usage_string)
    cmd.add_argument("-a", "--address",
                     help="Bind server to this address")
    cmd.add_argument("-p", "--port",
                     help="Bind server to this port")
    cmd.add_argument("-e", "--estimate",
                     help="Estimate to provide to clients")
    cmd.add_argument("-d", "--deviation",
                     help="Standard devation to provide to clients")
    args = cmd.parse_args()

    if args.address is not None:
        host = args.address
    if args.port is not None:
        port = args.port
    if args.estimate is not None:
        NSE_PEER_ESTIMATE = int(args.estimate)
    if args.deviation is not None:
        NSE_DEVIATION = int(args.deviation)

    # create asyncio server to listen for incoming API messages
    loop = asyncio.get_event_loop()
    handler = lambda r, w, mhandler=handle_message: handle_client(r,
                                                                  w,
                                                                  mhandler)
    serv = asyncio.start_server(handler,
                                host=host, port=port,
                                family=socket.AddressFamily.AF_INET,
                                reuse_address=True,
                                reuse_port=True)
    loop.create_task(serv)
    print(f"[+] NSE mockup listening on {host}:{port}")

    try:
        loop.run_forever()
    except KeyboardInterrupt as e:
        print("[i] Received SIGINT, shutting down...")
        loop.stop()


if __name__ == '__main__':
    main()
