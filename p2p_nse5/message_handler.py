from msilib.schema import Error
import struct
import asyncio

from typing import Dict, Callable
from .protocols.msg_types import MessageType

class MessageHandler:
    def handle_message(self, message):
        try:
            #TODO Probably replace that with unpack_incoming_messages method
            data = struct.unpack('!2H', data)
            msgtype = data[1]

            #TODO replace None by writer
            if (data[1] == MessageType.NSE_QUERY):
                self.handle_query(data, None)
            elif (data[1] == MessageType.GOSSIP_NOTIFICATION):
                self.handle_notification(self, data, None)
            else:
                print("Unreognized MessageType")

        except Exception:
            print("Something went wrong")

    # Handles a query request call
    async def handle_query(self, data, writer):
        # TODO Replace first 0 by "get_peer_estimation" and second 0 by "get_std_deviation"
        # Write the estimate
        estimate = self.assemble_answer(self, 0, 0)
        writer.write(estimate)
        await writer.drain()
        writer.close()

    async def handle_notification(self, data, writer):
        pass


    def assemble_answer(self, peers, std_deviation):
        return struct.pack('!2H2I', 16, MessageType.NSE_ESTIMATE, int(peers), int(std_deviation))