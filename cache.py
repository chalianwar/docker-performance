# The MIT License (MIT)
#
# Copyright (c) 2018 IBM
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time

class complex_cache:
    def __init__(self, size=1., restrict=100, fssize=10):
        self.lmu = []
        self.mem = {}
        self.capacity = int(size * (2**30))
        self.size = 0
        self.hits = 0
        self.misses = 0
        self.restrict = restrict*(2**20)
        self.firstmemhits = 0
        self.firstfsmemhits = 0
        self.firstfshits = 0
        if self.restrict > self.capacity:
            self.restrict = self.capacity
        self.evictions = 0
        self.first = True
        self.firstMiss = 0
        self.fslmu = []
        self.fs = {}
        self.fscap = self.capacity*fssize
        self.fssize = 0
        self.fsmiss = 0
        self.fsfirstMiss = 0
        self.fsfirst = True
        self.fshits = 0
        self.fsevicts = 0

    def fsCheck(self, request):
        if request[-1] in self.fs:
            self.fssize -= self.fs[request[-1]][0]
            self.fs.pop(request[-1], None)
            self.fshits += 1
            if self.fsfirst == True:
                self.firstfshits += 1
        else:
            self.fsmiss += 1
            if self.fsfirst == True:
                self.fsfirstMiss += 1

    def fsPlace(self, layer, layerSize, ejected=False):
        if layer in self.fs:
            self.fslmu.append(layer)
            self.fshits += 1
            self.fs[layer][1] += 1
            if self.fsfirst == True:
                self.firstfshits += 1
        else:
            if ejected is False:
                self.fsmiss += 1
                if self.fsfirst == True:
                    self.fsfirstMiss += 1

            if layerSize + self.fssize <= self.fscap:
                self.fs[layer] = [layerSize, 1]
                self.fssize += layerSize
                self.fslmu.append(layer)
            else:
                if self.fscap < layerSize:
                    return
                self.fsfirst = False
                while layerSize + self.fssize > self.fscap:
                    eject = self.fslmu.pop(0)
                    if eject not in self.fs:
                        continue
                    self.fs[eject][1] -= 1
                    if self.fs[eject][1] > 0:
                        continue
                    self.fssize -= self.fs[eject][0]
                    self.fs.pop(eject, None)
                    self.fsevicts += 1
                self.fs[layer] = [layerSize, 1]
                self.fslmu.append(layer)
                self.fssize += layerSize

    def place(self, request):
        if request[-1] in self.mem:
            self.lmu.append(request[-1])
            self.mem[request[-1]][1] += 1
            self.hits += 1
            if self.first == True:
                self.firstmemhits += 1
            if self.fsfirst == True:
                self.firstfsmemhits += 1
            
        else:
            self.misses += 1
            if self.first == True:
                self.firstMiss += 1

            if request[1] >= self.restrict:
                self.fsPlace(request[-1], request[1])
                return

            self.fsCheck(request)

            if request[1] + self.size <= self.capacity:
                self.mem[request[-1]] = [request[1], 1]
                self.lmu.append(request[-1])
                self.size += request[1]
            else:
                self.first = False
                while request[1] + self.size > self.capacity:
                    eject = self.lmu.pop(0)
                    self.mem[eject][1] -= 1
                    if self.mem[eject][1] > 0:
                        continue
                    self.fsPlace(eject, self.mem[eject][0], ejected=True)
                    self.size -= self.mem[eject][0]
                    self.mem.pop(eject, None)
                    self.evictions += 1

                self.mem[request[-1]] = [request[1], 1]
                self.lmu.append(request[-1])
                self.size += request[1]

    def get_lmu_hits(self):
        return self.hits - self.firstmemhits

    def get_h_hits(self):
        return self.hits + self.fshits - self.firstfsmemhits - self.firstfshits

    def get_lmu_misses(self):
        return self.misses - self.firstMiss

    def get_h_misses(self):
        return self.fsmiss - self.fsfirstMiss

    def get_all(self):
        info = {
            'memory hits': self.hits,
            'memory misses': self.misses,
            'initial memory misses': self.firstMiss,
            'memory evictions': self.evictions,
            'file system hits': self.fshits,
            'file system misses': self.fsmiss,
            'initial file system misses': self.fsfirstMiss,
            'file system evictions': self.fsevicts,
            'initial memory hits': self.firstmemhits,
            'initial memory-file-system hits': self.firstfsmemhits,
            'initial file system hits': self.firstfshits}
        return info


def reformat(indata):
    ret = []
    for item in indata:
        if 'manifest' in item['uri']:
            continue

        layer = item['uri'].split('/')[-1]
        ret.append((item['delay'], item['size'], layer))

    return ret

def run_sim(requests, size):
    t = time.time()
    caches = []
    caches.append(complex_cache(size=size, fssize = 10))
    caches.append(complex_cache(size=size, fssize = 15))
    caches.append(complex_cache(size=size, fssize = 20))
    i = 0
    count = 10
    for request in requests:
        if 1.*i / len(requests) > 0.1:
            i = 0
            print str(count) + '% done'
            count += 10
        for c in caches:
            c.place(request)
        i += 1
    hit_ratios = {}
    i = 0
    hit_ratios[str(i) + ' 10 lmu hits'] = caches[i].get_lmu_hits()
    hit_ratios[str(i) + ' 10 lmu misses'] = caches[i].get_lmu_misses()
    hit_ratios[str(i) + ' 10 h hits'] = caches[i].get_h_hits()
    hit_ratios[str(i) + ' 10 h misses'] = caches[i].get_h_misses()
    hit_ratios[str(i) + ' 15 lmu hits'] = caches[i + 1].get_lmu_hits()
    hit_ratios[str(i) + ' 15 lmu misses'] = caches[i + 1].get_lmu_misses()
    hit_ratios[str(i) + ' 15 h hits'] = caches[i + 1].get_h_hits()
    hit_ratios[str(i) + ' 15 h misses'] = caches[i + 1].get_h_misses()
    hit_ratios[str(i) + ' 20 lmu hits'] = caches[i + 2].get_lmu_hits()
    hit_ratios[str(i) + ' 20 lmu misses'] = caches[i + 2].get_lmu_misses()
    hit_ratios[str(i) + ' 20 h hits'] = caches[i + 2].get_h_hits()
    hit_ratios[str(i) + ' 20 h misses'] = caches[i + 2].get_h_misses()

    return hit_ratios

def init(data, args):
    cache_size = args['cache_size']

    print 'running cache simulation'

    parsed_data = reformat(data)

    info = run_sim(parsed_data, cache_size)

    for thing in info:
        print thing + ': ' + str(info[thing])

