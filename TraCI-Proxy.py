#!/usr/bin/python3
import asyncio
import struct
import socket
import argparse

# signal handling
import functools
import signal
import sys

def ask_exit(signame):
    print("got signal %s: exit" % signame)
    loop.stop()

# Command line options
parser = argparse.ArgumentParser(description='TraCI-Proxy - A Proxy to allow multiple TraCI Connections to SUMO')
parser.add_argument('sumoip', metavar='SUMO_IP', help='IP address of the SUMO TraCI Server')
parser.add_argument('sumoport', metavar='SUMO_PORT', type=int, help='Port number of the SUMO TraCI Server')
parser.add_argument('proxyip', metavar='PROXY_IP', help='IP address the TraCI-Proxy should be listening on')
parser.add_argument('proxyport', metavar='PROXY_PORT', help='Port number the TraCI-Proxy should be listening on')

args = parser.parse_args()

# Global socket connection to TraCI Server (SUMO)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((args.sumoip, args.sumoport))

@asyncio.coroutine
def handle_client_connect(reader, writer):
    addr = writer.get_extra_info('peername')
    print('{}:{} connected!'.format(addr[0], addr[1]))

    while True:
        # retrieve packet from client
        data_length = yield from reader.read(4)
        if b'' == data_length:
            break # fail silently
        length, = struct.unpack('!i', data_length)
        #print('Packet length: {}'.format(length))

        data = yield from reader.read(length - 4)
        #print('Packet data: {}'.format(data_length + data))

        # forward packet to TraCI-Server
        s.sendall(data_length + data)

        # receive answer from TraCI-Server
        data_length = s.recv(4)
        length, = struct.unpack('!i', data_length)
        #print('Packet length: {}'.format(length))

        data = s.recv(length - 4)
        #print('Packet data: {}'.format(data_length + data))

        # forward answer to client
        writer.write(data_length + data)
    

loop = asyncio.get_event_loop()
for signame in ('SIGINT', 'SIGTERM'):
    loop.add_signal_handler(getattr(signal,
                                    signame),
                            functools.partial(ask_exit,
                                              signame))
coro = asyncio.start_server(handle_client_connect,
                            args.proxyip,
                            args.proxyport,
                            loop=loop)
server = loop.run_until_complete(coro)
print('TraCI-Proxy awaiting connections on {}:{}...'.format(args.proxyip, args.proxyport))
loop.run_forever()
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
