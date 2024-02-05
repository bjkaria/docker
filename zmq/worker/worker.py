from aiohttp import web
import asyncio
import os
import signal
import zmq
import zmq.asyncio

class Worker:
    def __init__(self, zmq_publish_address, zmq_subscribe_address, rest_api_port):
        self.zmq_publish_address = zmq_publish_address
        self.zmq_subscribe_address = zmq_subscribe_address
        self._zmq_context = zmq.asyncio.Context()
        self._zmq_subscribe_socket = self._zmq_context.socket(zmq.SUB)
        self._rest_api_port = rest_api_port
        self.shutdown = False
        self._name = None
        self._id = None
        self._num_processed = 0
        self._app = None
        self._runner = None
        self._site = None

    def signal_handler(self, sig, frame):
        self.shutdown = True
        tasks = asyncio.all_tasks()
        for task in tasks:
            task.cancel()
        print("shutting down")

    async def start_subscription(self):
        self._zmq_subscribe_socket.connect(self.zmq_subscribe_address)
        self._zmq_subscribe_socket.setsockopt_string(zmq.SUBSCRIBE, '')

        try:
            while not self.shutdown:
                message = await self._zmq_subscribe_socket.recv_string()
                print(message)
        finally:
            self._zmq_subscribe_socket.close()

    async def get_status(self, request):
        status = {
            'name': self._name,
            'id': self._id,
            'num_processed': self._num_processed
        }
        return web.json_response(status)

    async def start_rest_api(self):
        self._app = web.Application()
        self._app.router.add_get('/status', self.get_status)
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, '0.0.0.0', self._rest_api_port)
        await self._site.start()

    async def start(self):
        await asyncio.gather(
            self.start_subscription(),
            self.start_rest_api()
        )

async def main():
    subscribe_address = os.environ.get('ZMQ_SUBSCRIBE_ADDRESS')
    publish_address = os.environ.get('ZMQ_PUBLISH_ADDRESS')
    rest_api_port = os.environ.get('REST_API_PORT')

    worker = Worker(publish_address, subscribe_address, rest_api_port)
    signal.signal(signal.SIGINT, worker.signal_handler)
    signal.signal(signal.SIGTERM, worker.signal_handler)

    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())