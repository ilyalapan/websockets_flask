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
from tinydb import TinyDB
import datetime
import json

REDIS_URL = os.environ['REDIS_URL']
REDIS_CHAN = 'chat'

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)
redis = redis.from_url(REDIS_URL)

db = TinyDB('db.json')

class ChatBackend(object):
    """Interface for registering and updating WebSocket clients."""

    def __init__(self):
        self.clients = {}
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
        connection_id = db.insert({'connection_time':str(datetime.datetime.now())})
        self.clients[connection_id] = client
        return connection_id

    def send(self, client_dict, connection_id, data):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        connection_id = client_dict[]
        print('Sending')
        try:
            client.send(data)
        except Exception, e:
            print(e)
            print('Removing Clients')
            client.close()
            self.clients.remove(client)
            db.remove(eids=[connection_id])

    def run(self):
        """Listens for new messages in Redis, and sends them to clients."""
        print('Running')
        for data in self.__iter_data():
            for connection_id,client_dict in self.clients.iter():
                gevent.spawn(self.send, client_dict, connection_id, data)

    def start(self):
        """Maintains Redis subscription in the background."""
        gevent.spawn(self.run)

chats = ChatBackend()
chats.start()

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
    print(db.all())
    if len(db.all()):
        print('Looking at clientss')
        for client in chats.clients:
            print('A cleint!')
            response_dict = {'box_id' : box_id}
            print(response_dict)
            data_string = json.dumps(response_dict)
            print('Made a response dict', data_string)
            redis.publish(REDIS_CHAN, data_string)
        return 'True'
    return 'False'


@sockets.route('/receive')
def outbox(ws):
    print('receive')
    """Sends outgoing chat messages, via `ChatBackend`."""
    connection_id = chats.register(ws)
    while not ws.closed:
        # Context switch while `ChatBackend.start` is running in the background.
        gevent.sleep(0.1)
    db.remove(eids=[connection_id])


'''
@sockets.route('/submit')
def inbox(ws):
    print('submit')
    """Receives incoming chat messages, inserts them into Redis."""
    while not ws.closed:
        # Sleep to prevent *constant* context-switches.
        gevent.sleep(0.1)
        message = ws.receive()

        if message:
            app.logger.info(u'Insertingg message: {}'.format(message))
            redis.publish(REDIS_CHAN, message)
'''


