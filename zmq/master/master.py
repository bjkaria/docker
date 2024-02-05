# this is the master node that publishes instructions over a zeromq publish socket
# it is the main entry point for the system

from aiohttp import web
import asyncio
import json
import os
import random
import signal
import socket
import zmq
import zmq.asyncio

class Master:
    def __init__(self, zmq_publish_address, zmq_subscribe_address, rest_api_port):
        self._zmq_publish_address = zmq_publish_address
        self._zmq_subscribe_address = zmq_subscribe_address
        self._shutdown = False
        self._zmq_context = zmq.asyncio.Context()
        self._zmq_pub_socket = None
        self._num_workers = 0
        self._num_published_instructions = 0
        self._rest_api_port = rest_api_port
        self._workers = []
        self._setup_pub_socket()

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        self._shutdown = True
        print("shutting down")

    def _setup_pub_socket(self):
        self._zmq_pub_socket = self._zmq_context.socket(zmq.PUB)
        self._zmq_pub_socket.bind(self._zmq_publish_address)

    def register_workers(self):
        worker_addresses = socket.getaddrinfo(f'worker', port=None, family=socket.AF_INET, type=socket.SOCK_STREAM)

        for i, worker_address in enumerate(worker_addresses):
            worker = {
                'address': worker_address,
                'id': i
            }
            self._workers.append(worker)
            self._num_workers += 1

        print(f"registered {self._num_workers} workers")

    def get_status(self):
        status = {
            'num_workers': self._num_workers,
            'num_published_instructions': self._num_published_instructions
        }

        return status

    async def publish_instructions(self):
        while not self._shutdown:
            random_string = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=10))
            random_number = random.randint(1, 100)
            random_number_2 = random.randint(1, 100)
            random_number_3 = random.randint(1, 100)

            message = {
                'random_string': random_string,
                'random_number': random_number,
                'random_number_2': random_number_2,
                'random_number_3': random_number_3
            }

            message_json = json.dumps(message)

            print(f"publishing message: {message_json}")
            await self._zmq_pub_socket.send_string(message_json)
            self._num_published_instructions += 1
            await asyncio.sleep(1)

        self._zmq_pub_socket.close()

    async def startRESTAPI(self):
        async def status(request):
            return web.json_response(self.get_status())

        self._webapp = web.Application()
        self._webapp.router.add_get('/status', status)
        self._runner = web.AppRunner(self._webapp)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, '0.0.0.0', self._rest_api_port)
        await self._site.start()

    async def start(self):
        self.register_workers()
        task1 = asyncio.create_task(self.publish_instructions())
        task2 = asyncio.create_task(self.startRESTAPI())

        await asyncio.gather(task1, task2)


async def main():
    publish_address = os.environ.get('ZMQ_PUBLISH_ADDRESS')
    subscribe_address = os.environ.get('ZMQ_SUBSCRIBE_ADDRESS')
    rest_api_port = os.environ.get('REST_API_PORT')

    master = Master(publish_address, subscribe_address, rest_api_port)
    master.setup_signal_handlers()
    await master.start()

if __name__ == "__main__":
    asyncio.run(main())