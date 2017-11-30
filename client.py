import json
import websocket
import threading
import sys
import time
import os
if(os.name == 'nt'):
    import colorama
    colorama.init()
if('--help' in sys.argv):
    i = sys.argv.index('--help')
    if(i == 0 or sys.argv[-1] not in ('--path', '--output')):
        print('''
Usage: python hi.py [options...]
     --help         This help text
     --nolog        Disable logging
     --nossl        Use ws:// instead of wss:// 
 -o, --output <file> Write logs to <file>
     --path <path>  Connect to //hostname/<path> (default: ws)
''')
        exit()
RUNNING = True
t1 = None
def sleep(t):
    while(t > 1):
        t -= 1
        if(not RUNNING):
            sys.exit()
        time.sleep(1)
    time.sleep(t % 1)
def terminate():
    if(t1):
        t1.do_run = False
        t1.join()
    sys.exit()
def timestamp():
    return int(time.time() * 1000)
LOGGING = True
if('--nolog' in sys.argv):
    i = sys.argv.index('--nolog')
    if(i == 0 or sys.argv[-1] not in ('--path', '--output')):
        LOGGING = False
logfn = "rawlog_{0}.log".format(timestamp())
if('--output' in sys.argv):
    i = sys.argv.index('--output')
    if(i == 0 or sys.argv[-1] not in ('--path', '--output') and len(sys.argv) - 1 > i):
        logfn = sys.argv(i + 1)
def rawlog(src, data = ''):
    if(LOGGING):
        f = open(logfn, 'a')
        f.write('{0} [{1}] >>> {2}\n'.format(src, timestamp(), data))
        f.close()
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
        Message = "{0}: {1}".format(From, Message)
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
    closed = False
    path = 'ws'
    def join(self, host, name = None, nossl = False):
        self.host = host
        if(None == name):
            name = self.username
        rawlog('JOIN', json.dumps({'host': host, 'name': name, 'nossl': nossl}))
        p = 'ws' if nossl else 'wss'
        self.ws = websocket.WebSocketApp("{0}://{1}/{3}?username={2}".format(p, host, name, self.path), on_message = self.onMessage, on_error = self.onError, on_close = self.onClose)
        self.ws.run_forever()
    def sendmsg(self, msg):
        if(len(msg) and msg[0] == ':'):
            msg = msg[1:]
            if(len(msg) and msg[0] != ':'):
                msg = msg.split()
                if(msg[0] == 'exit'):
                    self.ws.close()
                    RUNNING = False
                    terminate()
                    return
                if(msg[0] == 'help'):
                    print('''
:help - this message
:exit - exit this app
:name <String name> - change username
:meta <Boolean value> - seems to be useless
:cat <String filename> - send file content to chat (name with spaces not supported)
::msg - pass ":msg" to server
''')
                    return
                if(msg[0] == 'name'):
                    self.username = msg[1]
                    return
                if(msg[0] == 'meta'):
                    if(len(msg) < 2):
                        print('Not enough arguments!')
                        return
                    if(msg[1] in ('1', 'true', 'True', 'TRUE')):
                        self.meta = True
                    elif(msg[1] in ('0', 'false', 'False', 'FALSE')):
                        self.meta = False
                    else:
                        print('"{0}" is not boolean'.format(msg[1]))
                    return
                if(msg[0] == 'cat'):
                    if(len(msg) < 2):
                        print('Not enough arguments!')
                        return
                    try:
                        f = open(msg[1], 'r')
                        self.sendmsg(f.read())
                    except FileNotFoundError:
                        print('File "{0}" does not exist'.format(msg[1]))
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
        rawlog('MESSAGE', msg)
        d = json.loads(msg)
        if(type(d) != dict):
            print(msg)
            return
        print(teletype.proceedText(**d))
    def onClose(self, ws):
        rawlog('CLOSE')
        print('Closed')
        RUNNING = False
        self.closed = True
    def onError(self, ws, err):
        rawlog('ERROR', err)
        print("Error! ", err)
        self.closed = True
h = input("Host (e. g.: b1nary.tk): ")
u = input("Username: ")
a = chatapp()
a.username = u
if('--path' in sys.argv):
    i = sys.argv.index('--path')
    if(i == 0 or sys.argv[-1] not in ('--path', '--output') and len(sys.argv) - 1 > i):
        a.path = sys.argv[i + 1]
t1 = threading.Thread(target = a.join, args = (h, None, '--nossl' in sys.argv))
t1.start()
while(RUNNING):
    s = input()
    if(a.closed or not RUNNING):
        break
    rawlog('INPUT', s)
    a.sendmsg(s)
terminate()
