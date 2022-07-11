import asyncio
import struct

# from .protocols import api  # TODO: Use the methods provided by that module
from .protocols.msg_types import MessageType


class APIServer:
    def __init__(self, port):
        self.server = None
        self.port = port

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
