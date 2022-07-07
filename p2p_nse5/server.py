import asyncio
import struct

from .protocols import api
from .protocols.msg_types import MessageType


class APIServer:
    def __init__(self, port):
        self.server = None
        self.port = port

    # Check if request has the right length and message-type as specified
    def validate_request(self, data):
        try:
            data = struct.unpack('!2H', data)
            return data[0] == 4 and data[1] == MessageType.NSE_QUERY
        except Exception:
            return False

    # Check if answer has the right length and message-type as specified
    def validate_answer(self, data):
        try:
            data = struct.unpack('!2H2I', data)
            return data[0] == 12 and data[1] == MessageType.NSE_ESTIMATE
        except Exception:
            return False

    # Assembles answer in a struct wtih length 16, correct message type, and the estimates from the parameter
    def assemble_answer(peers, std_deviation):
        return struct.pack('!2H2I', 16, MessageType.NSE_ESTIMATE, int(peers), int(std_deviation))

    # Handles a query request call
    async def handle_request(self, reader, writer):
        print("Handle request")
        data = await reader.read()

        # Validate the incoming request
        if self.validate_request(self, data):
            # TODO Replace first 0 by "get_peer_estimation" and second 0 by "get_std_deviation"
            # Write the estimate
            estimate = self.assemble_answer(0, 0)
            writer.write(estimate)
            await writer.drain()
        writer.close()

    # Starts the API Server and runs the event loop
    async def start_api_server(self):
        event_loop = asyncio.get_running_loop()
        self.server = await event_loop.create_server(self.handle_request, "127.0.0.1", self.port)
        print("Server started")
        async with self.server:
            await self.server.serve_forever()

    # Stops API Server
    def stop_api_server(self, event_loop):
        if self.server is not None:
            self.server.close()
            event_loop.run_until_complete(self.server.wait_closed())
            self.server = None


if __name__ == "__main__":
    server = APIServer(1337)
    asyncio.run(server.start_api_server())
