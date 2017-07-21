"""
Chat Server
===========

This simple application uses WebSockets to run a primitive chat server.
"""

import os
import logging
import redis
import gevent
from flask import Flask, render_template, request, Response
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
        print('Registered a connection!')
        connection_id = db.insert({'connection_time':str(datetime.datetime.now())})
        self.clients[connection_id] = client
        return connection_id

    def send(self, client, connection_id, data):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        print('Sending')
        try:
            client.send(data)
        except Exception, e:
            print(e)
            print('Removing Clients')
            self.clients[connection_id] = None
            db.remove(eids=[connection_id])

    def run(self):
        """Listens for new messages in Redis, and sends them to clients."""
        print('Running')
        for data in self.__iter_data():
            for connection_id,client in self.clients.items():
                gevent.spawn(self.send, client, connection_id, data)

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
    print(request.get_json())
    box_id = None
    #box_id= request.values['box_id']
    if not box_id:
        r = Response(response = json.dumps({'status':False, 'comment':'No Box ID'}),status=200, mimetype="application/json")
        return r
    print(db.all())
    if len(db.all()):
        print('Looking at clientss')
        response_dict = {'box_id' : box_id}
        print(response_dict)
        data_string = json.dumps(response_dict)
        print('Made a response dict', data_string)
        redis.publish(REDIS_CHAN, data_string)
        return Response(response = json.dumps({'status':True}),status=200, mimetype="application/json")
    r = Response(response = json.dumps({'status':False}),status=200, mimetype="application/json")
    return r


@sockets.route('/receive')
def outbox(ws):
    print('Receiving a connection!')
    """Sends outgoing chat messages, via `ChatBackend`."""
    connection_id = chats.register(ws)
    while not ws.closed:
        # Context switch while `ChatBackend.start` is running in the background.
        gevent.sleep(0.1)
    print('Connection closed!')
    print(db.all())
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


