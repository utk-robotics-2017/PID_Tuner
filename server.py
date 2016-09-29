# Imports
import sys
import random
import signal
import time
import os
import json

import tornado.ioloop
import tornado.websocket

sys.path.append(('/').join(os.path.abspath(__file__).split('/')[:-2]))
from head.spine.core import get_spine
from head.spine.appendages.pid import Pid

# We're going to store the clients
clients = set()
clientId = 0

# Port for the websocket to be hosted on
port = 9002
pin = random.randint(0, 99999)


def log(wsId, message):
    print("{}\tClient {:2d}\t{}".format(time.strftime("%H:%M:%S", time.localtime()), wsId, message))


class Server(tornado.websocket.WebSocketHandler):
    # Accept cross origin requests
    def check_origin(self, origin):
        return True

    # Client connected
    def open(self):
        global clients, clientId

        self.id = clientId
        clientId += 1
        clients.add(self)

        self.verified = False

        log(self.id, "connected with ip: " + self.request.remote_ip)

    # Client sent a message
    def on_message(self, message):
        if not self.verified:
            # Try to read the message as a pin number
            try:
                clientPin = int(message)
            except ValueError:
                self.write_message("Invalid Pin")
                log(self.id, "entered an invalid pin: " + message)
                return

            # Check pin
            if clientPin == pin:
                self.verified = True
                self.write_message("Verified")
                log(self.id, "entered correct pin")
                self.gs = get_spine()
                self.s = self.gs.__enter__()
            else:
                self.write_message("WrongPin")
                log(self.id, "entered wrong pin")

        else:
            # If message starts with the command, run the code
            cmd = "GetPIDOptions"
            if message[:len(cmd)] == cmd:
                # Additional data will be in "message[len(cmd):]"
                # Messages can be sent to this client using "self.write_message(str)"
                pids = []
                for key, appendage in iter(self.s.get_appendage_dict().items()):
                    if isinstance(appendage, Pid):
                        pids.append(key)
                self.write_message(json.dumps(pids))

            # If message starts with the command, run the code
            cmd = "PostPIDSelection"
            if message[:len(cmd)] == cmd:
                # Additional data will be in "message[len(cmd):]"
                # Messages can be sent to this client using "self.write_message(str)"
                self.pid = self.s.get_appendage(message[len(cmd):])

            # If message starts with the command, run the code
            cmd = "PostPID"
            if message[:len(cmd)] == cmd:
                # Additional data will be in "message[len(cmd):]"
                # Messages can be sent to this client using "self.write_message(str)"
                pid_constants = json.loads(message[len(cmd):])
                self.pid.modify_constants(pid_constants['kp'], pid_constants['ki'],
                                          pid_constants['kd'])

            # If message starts with the command, run the code
            cmd = "PostSetpoint"
            if message[:len(cmd)] == cmd:
                # Additional data will be in "message[len(cmd):]"
                # Messages can be sent to this client using "self.write_message(str)"
                self.pid.set(float(message[len(cmd):]))

            # If message starts with the command, run the code
            cmd = "GetDisplay"
            if message[:len(cmd)] == cmd:
                # Additional data will be in "message[len(cmd):]"
                # Messages can be sent to this client using "self.write_message(str)"

                self.write_message(json.dumps(self.pid.display()))

    # Client disconnected
    def on_close(self):
        clients.remove(self)
        log(self.id, "disconnected")
        self.gs.__exit__()


# Catch ctrl+c
def sigInt_handler(signum, frame):
    print(" Closing Server")

    # Close each client's connection
    while clients:
        client = next(iter(clients))
        client.close(reason="Server Closing")
        client.on_close()

    # Close the websocket port
    tornado.ioloop.IOLoop.current().stop()
    print("Server is closed")
    sys.exit(0)

if __name__ == "__main__":
    app = tornado.web.Application([(r"/", Server)])
    app.listen(port)
    signal.signal(signal.SIGINT, sigInt_handler)
    print("Pin: {:05d}".format(pin))
    tornado.ioloop.IOLoop.current().start()
