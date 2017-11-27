import json
import websocket
import threading
import sys
class teletype:
    fg256prefix = (38, 5)
    bg256prefix = (48, 5)
    bg16 = 10
    colors256 = {'coral': 209, 'darkblue': 4}
    colors16 = dict()
    defaultUser = (True, 'darkblue')
    defaultChannel = (True, 'coral')
    users = dict()
    def color(c, bg = False):
        if(type(c[0]) == bool):
            if(c[0]):
                p = teletype.fg256prefix
                if(bg):
                    p = teletype.bg256prefix
                return p + (teletype.colors256.get(c[1], 15),)
            else:
                p = 0
                if(bg):
                    p = teletype.bg16
                return (teletype.colors16.get(c[1], 97) + p,)
        else:
            return tuple(map(int, c))
    def strColor(c, bg = False):
        return '\033[{0}m'.format(';'.join(tuple(map(str, teletype.color(c, bg)))))
    def styleFor(From = '', Meta = False, **kwargs):
        if(Meta):
            return teletype.strColor(teletype.defaultChannel)
        return teletype.strColor(teletype.users.get(From, teletype.defaultUser))
    def proceedText(Message = '', From = '', Meta = False, Room = '', **kwargs):
        b = []
        eb = []
        estate = False
        e = teletype.styleFor(From, Meta)
        b.append(e)
        Message = "{0}: {1}".format(('#' + Room) if Meta else From, Message)
        for c in Message:
            if(estate):
                if(c in '[0123456789;'):
                    eb.append(c)
                else:
                    estate = False
                    if(c == 'm'):
                        v = ''.join(eb[2:])
                        if('[' in v):
                            continue
                        v = tuple(map(int, v.split(';')))
                        s = ''
                        if 0 in v:
                            s = e
                        b.append(''.join(eb) + c + s)
            else:
                if(c == '\033'):
                    eb = ['\033']
                    estate = True
                    continue
                if(c == '\n'):
                    c = '\n\t'
                b.append(c)
        return ''.join(b) + '\033[48;5;0;38;5;15;0m\n'
class chatapp:
    username = 'anon'
    room = 'general'
    ws = None
    meta = False
    def join(self, host, name = None, nossl = False):
        self.host = host
        if(None == name):
            name = self.username
        p = 'ws' if nossl else 'wss'
        self.ws = websocket.WebSocketApp("{0}://{1}/chat?username={2}".format(p, host, name), on_message = self.onMessage, on_error = self.onError, on_close = self.onClose)
        self.ws.run_forever()
    def sendmsg(self, msg):
        if(len(msg) and msg[0] == ':'):
            msg = msg[1:]
            if(len(msg) and msg[0] != ':'):
                msg = msg.split()
                if(msg[0] == 'exit'):
                    self.ws.close()
                    exit()
                if(msg[0] == 'help'):
                    print('''
                    :help - this message
                    :exit - exit this app
                    :name <String name> - change username
                    :meta <Boolean value> - seems to be useless
                    ::msg - pass ":msg" to server
                    ''')
                    return
                if(msg[0] == 'name'):
                    self.username = msg[1]
                    return
                if(msg[0] == 'meta'):
                    if(msg[1] in ('1', 'true', 'True', 'TRUE')):
                        self.meta = True
                    elif(msg[1] in ('0', 'false', 'False', 'FALSE')):
                        self.meta = False
                    else:
                        print('"{0}" is not boolean'.format(msg[1]))
                    return
                print("Command not found!")
                return
        d = json.dumps({
                                    'From': self.username,
                                    'Message': msg,
                                    'Room': self.room,
                                    'Meta': self.meta})
        self.ws.send(d)
    def onMessage(self, ws, msg):
        d = json.loads(msg)
        if(type(d) != dict):
            print(msg)
            return
        print(teletype.proceedText(**d))
    def onClose(self, ws):
        print('Closed')
        sys.exit()
    def onError(self, ws, err):
        print("Error! ", err)
h = input("Host (e. g.: b1nary.tk): ")
u = input("Username: ")
a = chatapp()
a.username = u
t = threading.Thread(target = a.join, args = (h,))
t.start()
while(True):
    a.sendmsg(input())
