# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from bottle import route, run, request, static_file, Bottle
import sys, getopt
import os
import requests
import json
from optparse import OptionParser
import time
import socket
import random
from multiprocessing import Process, Queue
from dxf import *

app = Bottle()

def send_requests(registry, wait, requests, startTime, q):
    dxf = []
    for reg in registry:
        dxf.append(DXF(reg, 'test_repo', insecure=True))
    results = []
    fname = str(os.getpid())
    f = open(fname, 'wb')
    f.close()
    for r in requests:
        size = 0
        t = 0
        start = startTime + r['delay']
        onTime = 'no'
        if r['method'] == 'GET':
#            print fname + ' ' + r['blob']
            now = time.time()
            if start > now and wait is True:
                onTime = 'yes'
                time.sleep(start - now)
            t = time.time()
            reg = random.randrange(0, len(registry))
            try:
                for chunk in dxf[reg].pull_blob(r['blob'], chunk_size=1024*1024):
                    size += len(chunk)
            except:
                onTime = 'failed'
            t = time.time() - t
        else:
#            print fname + ' push'
            size = r['size']
            if size > 0:
                with open(fname, 'wb') as f:
                    f.seek(size - 1)
                    f.write('\0')
                now = time.time()
                if start > now and wait is True:
                    time.sleep(start - now)
                now = time.time()
                reg = random.randrange(0, len(registry))
                try:
                    dgst = dxf[reg].push_blob(fname)
                except:
                    onTime = 'failed'

                t = time.time() - now

        reg = (reg + 1) % len(registry)
        results.append({'time': now, 'duration': t, 'onTime': onTime, 'size': size})
    os.remove(fname)
    q.put(results)

def get_messages(q):
    while True:
        msg = q.get()
        masterip = msg[0]

        requests = json.loads(msg[1])

        threads = requests[0]['threads']
        ID = requests[0]['id']
        master = (masterip, requests[0]['port'])
        registry = requests[0]['registry']
        wait = requests[0]['wait']
        print master, ID, threads
        processes = []
        process_requests = []
        delayed = []
        for i in range(threads):
            process_requests.append([])
            delayed.append(0)

        for r in requests[1:]:
            i = 0
            for j in range(len(delayed)):
                if delayed[j] < delayed[i]:
                    i = j
            if delayed[i] < r['delay']:
                delayed[i] = r['delay'] + r['duration']
            else:
                delayed[i] += r['duration']
                
            process_requests[i].append(r)

        requests = [{'id': ID}]

        startTime = time.time()
        rq = Queue()
        for i in range(threads):
            first = registry.pop(0)
            registry.append(first)
            p = Process(target=send_requests, args=(registry, wait, process_requests[i], startTime, rq))
            p.start()
            processes.append(p)

        for i in range(threads):
            requests.extend(rq.get())

        for p in processes:
            p.join()
        print 'processes joined, sending response'
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        err = False
        try:
            sock.connect(master)
            sock.sendall(json.dumps(requests))
        except Exception as inst:
            print inst
            print "Error sending info, writing to file"
            err = True
        if err is True:
            with open('error_output', 'w') as f:
                f.write(json.dumps(requests))
        sock.close()
        print 'finished'
        

@app.route('/up', method="POST")
def sen():
    if 'application/json' in request.headers['Content-Type']:
        app.queue.put((request.environ.get('REMOTE_ADDR'), request.body.read()))
    return 'gotcha :D'

def main(argv):
    ip = ''
    port = 0
    try:
        opts, args = getopt.getopt(argv,"hi:p:",["ip=","port=","registry="])
    except getopt.GetoptError:
        print 'test.py -i <ip> -p <port>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'test.py -i <ip> -p <port>'
            sys.exit()
        elif opt in ("-i", "--ip"):
            ip = arg
        elif opt in ("-p", "--port"):
            port = arg
            

    if ip == '' and port == 0:
        ip = str(args).split(',')[0]
        port = int(str(args).split(',')[1])

    if ip == '' and port == 0:
        print "No ip or port specified..."
    
    global app
    app.queue = Queue()
    backend = Process(target=get_messages, args=[app.queue])
    backend.start()
    run(app, host=ip, port=port, quiet=True, numthreads=1)

if __name__ == "__main__":
    main(sys.argv[1:])

