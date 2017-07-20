"""
Chat Server
===========

This simple application uses WebSockets to run a primitive chat server.
"""

import os
import logging
import redis
import gevent
from flask import Flask, render_template, request
from flask_sockets import Sockets
import json

REDIS_URL = os.environ['REDIS_URL']
REDIS_CHAN = 'chat'

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)
redis = redis.from_url(REDIS_URL)



class ChatBackend(object):
    """Interface for registering and updating WebSocket clients."""

    def __init__(self):
        self.clients = list()
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe(REDIS_CHAN)

    def __iter_data(self):
        for message in self.pubsub.listen():
            data = message.get('data')
            if message['type'] == 'message':
                app.logger.info(u'Sending message: {}'.format(data))
                yield data

    def register(self, client):
        """Register a WebSocket connection for Redis updates."""
        self.clients.append(client)

    def send(self, client, data):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        print('Sending')
        try:
            client.send(data)
        except Exception, e:
            print(e)
            print('Removing Clients')
            self.clients.close()
            self.clients.remove(client)

chats = ChatBackend()

@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/open', methods=['POST'])
def open():
    print('Open')
    box_id=int(request.form['box_id'])
    if not box_id:
        print('No box ID')
        return 'False'
    print(chats.clients)
    if len(chats.clients):
        print('Looking at clientss')
        for client in chats.clients:
            print('A cleint!')
            response_dict = {'box_id' : box_id}
            print(response_dict)
            data_string = json.dumps(response_dict)
            print('Made a response dict', data_string)
            gevent.spawn(chats.send, client, data_string)
        return 'True'
    return 'False'


@sockets.route('/receive')
def outbox(ws):
    print('receive')
    """Sends outgoing chat messages, via `ChatBackend`."""
    chats.register(ws)
    while not ws.closed:
        # Context switch while `ChatBackend.start` is running in the background.
        gevent.sleep(0.1)
    print('Websocket closed')



