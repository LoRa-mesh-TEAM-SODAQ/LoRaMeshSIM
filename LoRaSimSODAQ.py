# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 14:59:04 2020

@author: secve
"""

import simpy
import random
import math
import sys
import matplotlib.pyplot as plt
import numpy as np
import os

#
# this function creates a node
#
class myNode():
    def __init__(self, nodeid, bs, period, packetlen):
        self.nodeid = nodeid
        self.period = period
        self.bs = bs
        self.x = random.randint(0, 500)
        self.y = random.randint(0, 500)
        self.dist = []

        global nodes
        
        #self.packet = myPacket(self.nodeid, packetlen, self.dist)
        self.sent = 0

        # graphics for node
        global graphics
        if (graphics == 1):
            global ax
            ax.add_artist(plt.Circle((self.x, self.y), 2, fill=True, color='blue'))
                
    def printInfo(self):
        print("NodeID", self.nodeid)
        print("node x: ", self.x)
        print("node y: ", self.y)
        print("Distances: ", end= "")
        print(*self.dist, sep= ", ")
        print()
        
    def calcDist(self, nodes):
        for i in range(len(nodes)):
            #print(i)
            if nodes[i].nodeid != self.nodeid:
                nodeDist = []
                xdist = self.x - nodes[i].x
                ydist = self.y - nodes[i].y
                nodeDist.append(nodes[i].nodeid)
                nodeDist.append(np.sqrt(xdist*xdist + ydist*ydist))
                self.dist.append(nodeDist)
        

        
            
#
# # this function creates a packet (associated with a node)
# # it also sets all parameters, currently random
# #
# class myPacket():
#     def __init__(self, nodeid, plen, distance):
#         global experiment
#         global Ptx
#         global gamma
#         global d0
#         global var
#         global Lpld0
#         global GL

#         self.nodeid = nodeid
#         self.txpow = Ptx

#         # randomize configuration values
#         #self.sf = random.choice([12,11,11,10,10,10,10,9,9,9,9,9,9,9,9,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8])
#         #self.sf = random.choice([8,9,10,11,12])
#         #self.sf = random.choice([8,8,8,9,9,9,10,10,11,12])
#         #self.sf = random.choice([12,11,11,10,10,10,9,9,9,9,8,8,8,8,8])
#         #self.sf  = random.choice([8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,9,9,9,9,9,9,9,9,9,10,10,10,10,10,11,11,11,12])
# #        self.sf  = random.choice([8,8,8,8,8,8,8,8,8,8,8,8,9,9,9,9,9,9,10,10,10,10,11,11,12])
#         self.cr = random.randint(1,4)
#         #self.bw = random.choice([125, 250, 500])
        

#         # for certain experiments override these
#         if experiment==1 or experiment == 0:
#             self.sf = 12
#             self.cr = 4
#             self.bw = 125

#         # for certain experiments override these
#         if experiment==2:
#             self.sf = 6
#             self.cr = 1
#             self.bw = 500
#         # lorawan
#         if experiment == 4:
#             self.sf = 12
#             self.cr = 1
#             self.bw = 125


#         # for experiment 3 find the best setting
#         # OBS, some hardcoded values
#         Prx = self.txpow  ## zero path loss by default

#         # log-shadow
#         Lpl = Lpld0 + 10*gamma*math.log(distance/d0)
#         print(("Lpl:", Lpl))
#         Prx = self.txpow - GL - Lpl

#         if (experiment == 3) or (experiment == 5):
#             minairtime = 9999
#             minsf = 0
#             minbw = 0

#             print(("Prx:", Prx))
#             self.cr = 1
#             self.bw = 125
#             self.sf  = random.choice([7,7,7,7,7,7,7,7,7,7,7,8,8,8,8,8,8,9,9,9,9,10,10,11,12])        
#             #self.sf = random.choice([12,11,11,10,10,10,10,9,9,9,9,9,9,9,9,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8])
#             #self.sf = random.choice([8,9,10,11,12])
#             #self.sf = random.choice([8,8,8,9,9,9,10,10,11,12])
#             #self.sf = random.choice([12,11,11,10,10,10,9,9,9,9,8,8,8,8,8])
#             #self.sf  = random.choice([8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,9,9,9,9,9,9,9,9,9,10,10,10,10,10,11,11,11,12])
#             #self.sf  = random.choice([8,8,8,8,8,8,8,8,8,8,8,8,9,9,9,9,9,9,10,10,10,10,11,11,12])

#             at = airtime(self.sf, self.cr, plen, self.bw)
#             if at < minairtime:
#                 minairtime = at
#                 minsf = self.sf
#                 minbw = self.bw
#                 minsensi = -88
#             if (minairtime == 9999):
#                 print("does not reach base station")
#                 sys.exit(-1)
#             print(("best sf:", minsf, " best bw: ", minbw, "best airtime:", minairtime))
#             self.rectime = minairtime
#             self.bw = minbw
#             self.cr = 1

#             if experiment == 5:
#                 # reduce the txpower if there's room left
#                 self.txpow = max(2, self.txpow - math.floor(Prx - minsensi))
#                 Prx = self.txpow - GL - Lpl
#                 print(('minsesi {} best txpow {}'.format(minsensi, self.txpow)))

#         # transmission range, needs update XXX
#         self.transRange = 150
#         self.pl = plen
#         self.symTime = (2.0**self.sf)/self.bw
#         self.arriveTime = 0
#         self.rssi = Prx
#         # frequencies: lower bound + number of 61 Hz steps
#         #self.freq = 860000000 + random.randint(0,2622950)

#         # for certain experiments override these and
#         # choose some random frequences
        
#         self.freq = random.choice([868100000, 868300000, 868500000,868700000,868900000,869100000,869300000,869500000])
#         #self.freq = random.choice([866500000,866700000,866900000,867100000,867300000,867500000,867700000,867900000,868100000, 868300000, 868500000,868700000,868900000,869100000,869300000,869500000])

#         print(("frequency" ,self.freq, "symTime ", self.symTime))
#         print(("bw", self.bw, "sf", self.sf, "cr", self.cr, "rssi", self.rssi))
#         self.rectime = airtime(self.sf,self.cr,self.pl,self.bw)
#         print(("rectime node ", self.nodeid, "  ", self.rectime))
#         # denote if packet is collided
#         self.collided = 0
#         self.processed = 0

# 1 to show nodes in plot
graphics = 1

# 868 MHz EU Carrier frequency
freq = 0.868

# list for all nodes
nodes = []

# get arguments
if len(sys.argv) >= 3:
    nrNodes = int(sys.argv[1])
    avgSendTime = int(sys.argv[2])
    PL = int(sys.argv[3])
    
    print("Nodes: ", nrNodes)
    print("AvgSendTime (exp. distributed): ",avgSendTime)
    print("PacketLength: ",PL)
else:
    print("usage: ./loraDir <nodes> <avgsend> <PacketLength>")
    sys.exit(-1)

#prepare show
if (graphics == 1):
    plt.ion()
    plt.figure()
    ax = plt.gcf().gca()
    
# Create nodes with avgSendTime and PacketLength 
# and add new nodes to nodes list
for i in range(0,nrNodes):
    node = myNode(i, 0, avgSendTime, PL)
    nodes.append(node)
    
# Calculate distance between nodes and print node info of all nodes
for i in range(len(nodes)):
    nodes[i].calcDist(nodes)
    nodes[i].printInfo()

# Show plot
if (graphics == 1):
    plt.xlim([0, 500])
    plt.ylim([0, 500])
    plt.draw()
    plt.show()
    