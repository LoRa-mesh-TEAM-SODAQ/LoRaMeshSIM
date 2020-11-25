#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
 LoRaSim 0.2.1: simulate collisions in LoRa - directional base station
 Copyright © 2016-2017 Thiemo Voigt <thiemo@sics.se> and Martin Bor <m.bor@lancaster.ac.uk>

 This work is licensed under the Creative Commons Attribution 4.0
 International License. To view a copy of this license,
 visit http://creativecommons.org/licenses/by/4.0/.

 Do LoRa Low-Power Wide-Area Networks Scale? Martin Bor, Utz Roedig, Thiemo Voigt
 and Juan Alonso, MSWiM '16, http://dx.doi.org/10.1145/2988287.2989163

 Mitigating Inter-Network Interference in LoRa Low-Power Wide-Area Networks,
 Thiemo Voigt, Martin Bor, Utz Roedig, and Juan Alonso, EWSN '17

 $Date: 2017-05-12 19:16:16 +0100 (Fri, 12 May 2017) $
 $Revision: 334 $
"""

"""
 SYNOPSIS:
   ./oneDirectionalLoraIntf.py <nodes> <avgsend> <experiment> <simtime>
                               <collision> <directionality> <networks> <basedist>
 DESCRIPTION:
    nodes
        number of nodes to simulate
    avgsend
        average sending interval in milliseconds
    experiment
        experiment is an integer that determines with what radio settings the
        simulation is run. All nodes are configured with a fixed transmit power
        and a single transmit frequency, unless stated otherwise.
        0   use the settings with the the slowest datarate (SF12, BW125, CR4/8).
        1   similair to experiment 0, but use a random choice of 3 transmit
            frequencies.
        2   use the settings with the fastest data rate (SF6, BW500, CR4/5).
        3   optimise the setting per node based on the distance to the gateway.
        4   use the settings as defined in LoRaWAN (SF12, BW125, CR4/5).
        5   similair to experiment 3, but also optimises the transmit power.
    simtime
        total running time in milliseconds
    collision
        set to 1 to enable the full collision check, 0 to use a simplified check.
        With the simplified check, two messages collide when they arrive at the
        same time, on the same frequency and spreading factor. The full collision
        check considers the 'capture effect', whereby a collision of one or the
    directionality
        set to 1 to enable directional antennae for nodes
    networks
        number of LoRa networks
    basedist
        X-distance between two base stations
 OUTPUT
    The result of every simulation run will be appended to a file named expX.dat,
    whereby X is the experiment number. The file contains a space separated table
    of values for nodes, collisions, transmissions and total energy spent. The
    data file can be easily plotted using e.g. gnuplot.
"""

import simpy
import random
import numpy as np
import math
import sys
import matplotlib.pyplot as plt
import os
from matplotlib.patches import Rectangle

# turn on/off graphics
graphics = 0

# do the full collision check
full_collision = False

# experiments:
# 0: packet with longest airtime, aloha-style experiment
# 1: one with 3 frequencies, 1 with 1 frequency
# 2: with shortest packets, still aloha-style
# 3: with shortest possible packets depending on distance


# RSSI global values for antenna
dir_30 = 4
dir_90 = 2
dir_150 = -4
dir_180 = -3
#dir_30 = 8
#dir_90 = 4
#dir_150 = -8
#dir_180 = -6


# this is an array with measured values for sensitivity
# see paper, Table 3
sf7 = np.array([7,-126.5,-124.25,-120.75])
sf8 = np.array([8,-127.25,-126.75,-124.0])
sf9 = np.array([9,-131.25,-128.25,-127.5])
sf10 = np.array([10,-132.75,-130.25,-128.75])
sf11 = np.array([11,-134.5,-132.75,-128.75])
sf12 = np.array([12,-133.25,-132.25,-132.25])

#
# check for collisions at base station
# Note: called before a packet (or rather node) is inserted into the list
def checkcollision(packet):
    col = 0 # flag needed since there might be several collisions for packet
    # lost packets don't collide
    if packet.lost:
       return 0
    if packetsAtBS[packet.bs]:
        for other in packetsAtBS[packet.bs]:
            if other.id != packet.nodeid:
                   # simple collision
               if frequencyCollision(packet, other.packet[packet.bs]) \
                   and sfCollision(packet, other.packet[packet.bs]):
                   if full_collision:
                       if timingCollision(packet, other.packet[packet.bs]):
                           # check who collides in the power domain
                           c = powerCollision(packet, other.packet[packet.bs])
                           # mark all the collided packets
                           # either this one, the other one, or both
                           for p in c:
                               p.collided = 1
                               if p == packet:
                                   col = 1
                       else:
                           # no timing collision, all fine
                           pass
                   else:
                       packet.collided = 1
                       other.packet[packet.bs].collided = 1  # other also got lost, if it wasn't lost already
                       col = 1
        return col
    return 0

#
# frequencyCollision, conditions
#
#        |f1-f2| <= 120 kHz if f1 or f2 has bw 500
#        |f1-f2| <= 60 kHz if f1 or f2 has bw 250
#        |f1-f2| <= 30 kHz if f1 or f2 has bw 125
def frequencyCollision(p1,p2):
    if (abs(p1.freq-p2.freq)<=120 and (p1.bw==500 or p2.freq==500)):
        return True
    elif (abs(p1.freq-p2.freq)<=60 and (p1.bw==250 or p2.freq==250)):
        return True
    else:
        if (abs(p1.freq-p2.freq)<=30):
            return True
    return False

def sfCollision(p1, p2):
    if p1.sf == p2.sf:
        # p2 may have been lost too, will be marked by other checks
        return True
    return False

def powerCollision(p1, p2):
    powerThreshold = 6 # dB
    if abs(p1.rssi - p2.rssi) < powerThreshold:
        # packets are too close to each other, both collide
        # return both packets as casualties
        return (p1, p2)
    elif p1.rssi - p2.rssi < powerThreshold:
        # p2 overpowered p1, return p1 as casualty
        return (p1,)
    # p2 was the weaker packet, return it as a casualty
    return (p2,)

def timingCollision(p1, p2):
    # assuming p1 is the freshly arrived packet and this is the last check
    # we've already determined that p1 is a weak packet, so the only
    # way we can win is by being late enough (only the first n - 5 preamble symbols overlap)

    # assuming 8 preamble symbols
    Npream = 8

    # we can lose at most (Npream - 5) * Tsym of our preamble
    Tpreamb = 2**p1.sf/(1.0*p1.bw) * (Npream - 5)

    # check whether p2 ends in p1's critical section
    p2_end = p2.addTime + p2.rectime
    p1_cs = env.now + Tpreamb
    if p1_cs < p2_end:
        # p1 collided with p2 and lost
        return True
    return False

# this function computes the airtime of a packet
# according to LoraDesignGuide_STD.pdf
#
def airtime(sf,cr,pl,bw):
    H = 0        # implicit header disabled (H=0) or not (H=1)
    DE = 0       # low data rate optimization enabled (=1) or not (=0)
    Npream = 8   # number of preamble symbol (12.25  from Utz paper)

    if bw == 125 and sf in [11, 12]:
        # low data rate optimization mandated for BW125 with SF11 and SF12
        DE = 1
    if sf == 6:
        # can only have implicit header with SF6
        H = 1

    Tsym = (2.0**sf)/bw
    Tpream = (Npream + 4.25)*Tsym
    payloadSymbNB = 8 + max(math.ceil((8.0*pl-4.0*sf+28+16-20*H)/(4.0*(sf-2*DE)))*(cr+4),0)
    Tpayload = payloadSymbNB * Tsym
    return Tpream + Tpayload



#
# this function creates a BS
#
class myBS():
    def __init__(self, id):
        self.id = id
        self.x = 0
        self.y = 0

        # This is a hack for now
        global nrBS
        global maxDist
        global maxX
        global maxY
        global baseDist

        if (nrBS == 1 and self.id == 0):
            self.x = maxDist
            self.y = maxY

        if (nrBS == 2 and self.id == 0):
            self.x = maxDist
            self.y = maxY

        if (nrBS == 2 and self.id == 1):
            self.x = maxDist + baseDist
            self.y = maxY

        if (nrBS == 3 and self.id == 0):
            self.x = maxDist + baseDist
            self.y = maxY

        if (nrBS == 3 and self.id == 1):
            self.x = maxDist
            self.y = maxY

        if (nrBS == 3 and self.id == 2):
            self.x = maxDist + 2*baseDist
            self.y = maxY

        if (nrBS == 4 and self.id == 0):
            self.x = maxDist + baseDist
            self.y = maxY

        if (nrBS == 4 and self.id == 1):
            self.x = maxDist
            self.y = maxY

        if (nrBS == 4 and self.id == 2):
            self.x = maxDist + 2*baseDist
            self.y = maxY

        if (nrBS == 4 and self.id == 3):
            self.x = maxDist + baseDist
            self.y = maxY + baseDist

        if (nrBS == 5 and self.id == 0):
            self.x = maxDist + baseDist
            self.y = maxY + baseDist

        if (nrBS == 5 and self.id == 1):
            self.x = maxDist
            self.y = maxY + baseDist

        if (nrBS == 5 and self.id == 2):
            self.x = maxDist + 2*baseDist
            self.y = maxY + baseDist

        if (nrBS == 5 and self.id == 3):
            self.x = maxDist + baseDist
            self.y = maxY

        if (nrBS == 5 and self.id == 4):
            self.x = maxDist + baseDist
            self.y = maxY + 2*baseDist


        if (nrBS == 6):
            if (self.id < 3):
                self.x = (self.id+1)*maxX/4.0
                self.y = maxY/3.0
            else:
                self.x = (self.id+1-3)*maxX/4.0
                self.y = 2*maxY/3.0

        if (nrBS == 8):
            if (self.id < 4):
                self.x = (self.id+1)*maxX/5.0
                self.y = maxY/3.0
            else:
                self.x = (self.id+1-4)*maxX/5.0
                self.y = 2*maxY/3.0

        if (nrBS == 24):
            if (self.id < 8):
                self.x = (self.id+1)*maxX/9.0
                self.y = maxY/4.0
            elif (self.id < 16):
                self.x = (self.id+1-8)*maxX/9.0
                self.y = 2*maxY/4.0
            else:
                self.x = (self.id+1-16)*maxX/9.0
                self.y = 3*maxY/4.0

        if (nrBS == 96):
            if (self.id < 24):
                self.x = (self.id+1)*maxX/25.0
                self.y = maxY/5.0
            elif (self.id < 48):
                self.x = (self.id+1-24)*maxX/25.0
                self.y = 2*maxY/5.0
            elif (self.id < 72):
                self.x = (self.id+1-48)*maxX/25.0
                self.y = 3*maxY/5.0
            else:
                self.x = (self.id+1-72)*maxX/25.0
                self.y = 4*maxY/5.0


        print "BSx:", self.x, "BSy:", self.y

        global graphics
        if (graphics):
            global ax
            # XXX should be base station position
            if (self.id == 0):
                ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='blue'))
                ax.add_artist(plt.Circle((self.x, self.y), maxDist, fill=False, color='green'))
            if (self.id == 1):
                ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='red'))
                ax.add_artist(plt.Circle((self.x, self.y), maxDist, fill=False, color='green'))
            if (self.id == 2):
                ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='green'))
                ax.add_artist(plt.Circle((self.x, self.y), maxDist, fill=False, color='green'))
            if (self.id == 3):
                ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='brown'))
                ax.add_artist(plt.Circle((self.x, self.y), maxDist, fill=False, color='green'))
            if (self.id == 4):
                ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='yellow'))
                ax.add_artist(plt.Circle((self.x, self.y), maxDist, fill=False, color='green'))

#
# this function creates a node
#
class myNode():
    def __init__(self, id, period, packetlen, myBS):
        global bs

        self.bs = myBS
        self.id = id
        self.period = period
        self.x = 0
        self.y = 0
        self.packet = []
        self.dist = []
        # this is very complex prodecure for placing nodes
        # and ensure minimum distance between each pair of nodes
        found = 0
        rounds = 0
        global nodes
        while (found == 0 and rounds < 100):
            global maxX
            global maxY
            a = random.random()
            b = random.random()
            if b<a:
                a,b = b,a
            posx = b*maxDist*math.cos(2*math.pi*a/b)+self.bs.x
            posy = b*maxDist*math.sin(2*math.pi*a/b)+self.bs.y
            if len(nodes) > 0:
                for index, n in enumerate(nodes):
                    dist = np.sqrt(((abs(n.x-posx))**2)+((abs(n.y-posy))**2))
                    # we set this so nodes can be placed everywhere
                    # otherwise there is a risk that little nodes are placed
                    # between the base stations where it would be more crowded
                    if dist >= 0:
                        found = 1
                        self.x = posx
                        self.y = posy
                    else:
                        rounds = rounds + 1
                        if rounds == 100:
                            print "could not place new node, giving up"
                            exit(-2)
            else:
                print "first node"
                self.x = posx
                self.y = posy
                found = 1


        # create "virtual" packet for each BS
        global nrBS
        for i in range(0,nrBS):
            d = np.sqrt((self.x-bs[i].x)*(self.x-bs[i].x)+(self.y-bs[i].y)*(self.y-bs[i].y))
            self.dist.append(d)
            self.packet.append(myPacket(self.id, packetlen, self.dist[i], i))
        print('node %d' %id, "x", self.x, "y", self.y, "dist: ", self.dist, "my BS:", self.bs.id)

        self.sent = 0

        # graphics for node
        global graphics
        if (graphics == 1):
            global ax
            if (self.bs.id == 0):
                    ax.add_artist(plt.Circle((self.x, self.y), 2, fill=True, color='blue'))
            if (self.bs.id == 1):
                    ax.add_artist(plt.Circle((self.x, self.y), 2, fill=True, color='red'))
            if (self.bs.id == 2):
                    ax.add_artist(plt.Circle((self.x, self.y), 2, fill=True, color='green'))
            if (self.bs.id == 3):
                    ax.add_artist(plt.Circle((self.x, self.y), 2, fill=True, color='brown'))


#
#   update RSSI depending on direction
#
    def updateRSSI(self):
        global bs

        if (self.bs.id == 0):
            print "+++++++++uR node", self.id, " and bs ", self.bs.id
        else:
            print "+++++NO+NO+++uR node", self.id, " and bs ", self.bs.id
            return
        print "node x,y", self.x, self.y
        print "main-bs x,y", bs[self.bs.id].x, bs[self.bs.id].y
        for i in range(0,len(self.packet)):
            print "rssi before", self.packet[i].rssi
            print "packet bs", self.packet[i].bs
            print "packet bs x, y:", bs[self.packet[i].bs].x, bs[self.packet[i].bs].y
            if (self.bs.id == self.packet[i].bs):
                print "packet to main bs, increase rssi "
                self.packet[i].rssi = self.packet[i].rssi + dir_30
            else:
                b1 = np.array([bs[self.bs.id].x, bs[self.bs.id].y])
                p = np.array([self.x, self.y])
                b2 = np.array([bs[self.packet[i].bs].x, bs[self.packet[i].bs].y])

                ba = b1 - p
                bc = b2 - p
                print ba
                print bc

                cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
                angle = np.degrees(np.arccos(cosine_angle))

                print "angle: ", angle

                if (angle <= 30):
                    print "rssi increase to other BS: 4"
                    self.packet[i].rssi = self.packet[i].rssi + dir_30
                elif angle <= 90:
                    print "rssi increase to other BS: 2"
                    self.packet[i].rssi = self.packet[i].rssi + dir_90
                elif angle <= 150:
                    print "rssi increase to other BS: -4"
                    self.packet[i].rssi = self.packet[i].rssi + dir_150
                else:
                    print "rssi increase to other BS: -3"
                    self.packet[i].rssi = self.packet[i].rssi + dir_180
            print "packet rssi after", self.packet[i].rssi


#
# this function creates a packet (associated with a node)
# it also sets all parameters, currently random
#
class myPacket():
    def __init__(self, nodeid, plen, distance, bs):
        global experiment
        global Ptx
        global gamma
        global d0
        global var
        global Lpld0
        global GL
        global nodes

        # new: base station ID
        self.bs = bs
        self.nodeid = nodeid


        # randomize configuration values
        self.sf = random.randint(6,12)
        self.cr = random.randint(1,4)
        self.bw = random.choice([125, 250, 500])

        # for certain experiments override these
        if experiment==1 or experiment == 0:
            self.sf = 12
            self.cr = 4
            self.bw = 125

        # for certain experiments override these
        if experiment==2:
            self.sf = 6
            self.cr = 1
            self.bw = 500


        # for experiment 3 find the best setting
        # OBS, some hardcoded values
        Prx = Ptx  ## zero path loss by default

        # log-shadow
        Lpl = Lpld0 + 10*gamma*math.log10(distance/d0)
        print Lpl
        Prx = Ptx - GL - Lpl

        if (experiment == 3):
            minairtime = 9999
            minsf = 0
            minbw = 0

            #print "Prx:", Prx

            for i in range(0,6):
                for j in range(1,4):
                    if (sensi[i,j] < Prx):
                        self.sf = sensi[i,0]
                        if j==1:
                            self.bw = 125
                        elif j==2:
                            self.bw = 250
                        else:
                            self.bw=500
                        at = airtime(self.sf,4,20,self.bw)
                        if at < minairtime:
                            minairtime = at
                            minsf = self.sf
                            minbw = self.bw

            self.rectime = minairtime
            self.sf = minsf
            self.bw = minbw
            if (minairtime == 9999):
                print "does not reach base station"
                exit(-1)

        # transmission range, needs update XXX
        self.transRange = 150
        self.pl = plen
        self.symTime = (2.0**self.sf)/self.bw
        self.arriveTime = 0
        self.rssi = Prx
        # frequencies: lower bound + number of 61 Hz steps
        self.freq = 860000000 + random.randint(0,2622950)

        # for certain experiments override these and
        # choose some random frequences
        if experiment == 1:
            self.freq = random.choice([860000000, 864000000, 868000000])
        else:
            self.freq = 860000000

        self.rectime = airtime(self.sf,self.cr,self.pl,self.bw)
        # denote if packet is collided
        self.collided = 0
        self.processed = 0
        # mark the packet as lost when it's rssi is below the sensitivity
        # don't do this for experiment 3, as it requires a bit more work
        if experiment != 3:
            global minsensi
            self.lost = self.rssi < minsensi
            print "node {} bs {} lost {}".format(self.nodeid, self.bs, self.lost)


#
# main discrete event loop, runs for each node
# a global list of packet being processed at the gateway
# is maintained
#
def transmit(env,node):
    while True:
        # time before sending anything (include prop delay)
        # send up to 2 seconds earlier or later
        yield env.timeout(random.expovariate(1.0/float(node.period)))

        # time sending and receiving
        # packet arrives -> add to base station

        node.sent = node.sent + 1

        global packetSeq
        packetSeq = packetSeq + 1

        global nrBS
        for bs in range(0, nrBS):
           if (node in packetsAtBS[bs]):
                print "ERROR: packet already in"
           else:
                # adding packet if no collision
                if (checkcollision(node.packet[bs])==1):
                    node.packet[bs].collided = 1
                else:
                    node.packet[bs].collided = 0
                packetsAtBS[bs].append(node)
                node.packet[bs].addTime = env.now
                node.packet[bs].seqNr = packetSeq

        # take first packet rectime
        yield env.timeout(node.packet[0].rectime)

        # if packet did not collide, add it in list of received packets
        # unless it is already in
        for bs in range(0, nrBS):
            if node.packet[bs].lost:
                lostPackets.append(node.packet[bs].seqNr)
            else:
                if node.packet[bs].collided == 0:
                    if (nrNetworks == 1):
                        packetsRecBS[bs].append(node.packet[bs].seqNr)
                    else:
                        # now need to check for right BS
                        if (node.bs.id == bs):
                            packetsRecBS[bs].append(node.packet[bs].seqNr)
                    # recPackets is a global list of received packets
                    # not updated for multiple networks
                    if (recPackets):
                        if (recPackets[-1] != node.packet[bs].seqNr):
                            recPackets.append(node.packet[bs].seqNr)
                    else:
                        recPackets.append(node.packet[bs].seqNr)
                else:
                    # XXX only for debugging
                    collidedPackets.append(node.packet[bs].seqNr)

        for bs in range(0, nrBS):
            if (node in packetsAtBS[bs]):
                packetsAtBS[bs].remove(node)
                # reset the packet
                node.packet[bs].collided = 0
                node.packet[bs].processed = 0

#
# "main" program
#

# get arguments
if len(sys.argv) == 10:
    nrNodes = int(sys.argv[1])
    avgSendTime = int(sys.argv[2])
    experiment = int(sys.argv[3])
    simtime = int(sys.argv[4])
    nrBS = int(sys.argv[5])
    if len(sys.argv) > 6:
        full_collision = bool(int(sys.argv[6]))
    directionality = int(sys.argv[7])
    nrNetworks = int(sys.argv[8])
    baseDist = float(sys.argv[9])
    print "Nodes per base station:", nrNodes
    print "AvgSendTime (exp. distributed):",avgSendTime
    print "Experiment: ", experiment
    print "Simtime: ", simtime
    print "nrBS: ", nrBS
    print "Full Collision: ", full_collision
    print "with directionality: ", directionality
    print "nrNetworks: ", nrNetworks
    print "baseDist: ", baseDist   # x-distance between the two base stations

else:
    print "usage: ./oneDirectionalLoraIntf.py <nodes> <avgsend> <experiment> <simtime> <collision> <directionality> <networks> <basedist>"
    print "experiment 0 and 1 use 1 frequency only"
    exit(-1)


# global stuff
nodes = []
packetsAtBS = []
env = simpy.Environment()


# max distance: 300m in city, 3000 m outside (5 km Utz experiment)
# also more unit-disc like according to Utz
nrCollisions = 0
nrReceived = 0
nrProcessed = 0

# global value of packet sequence numbers
packetSeq = 0

# list of received packets
recPackets=[]
collidedPackets=[]
lostPackets = []

Ptx = 14
gamma = 2.08
d0 = 40.0
var = 0           # variance ignored for now
Lpld0 = 127.41
GL = 0

sensi = np.array([sf7,sf8,sf9,sf10,sf11,sf12])

## figure out the minimal sensitivity for the given experiment
minsensi = -200.0
if experiment in [0,1,4]:
    minsensi = sensi[5,2]  # 5th row is SF12, 2nd column is BW125
elif experiment == 2:
    minsensi = -112.0   # no experiments, so value from datasheet
elif experiment == 3:
    minsensi = np.amin(sensi) ## Experiment 3 can use any setting, so take minimum

Lpl = Ptx - minsensi
print "amin", minsensi, "Lpl", Lpl
maxDist = d0*(math.e**((Lpl-Lpld0)/(10.0*gamma)))
print "maxDist:", maxDist

# size of area
xmax = maxDist*(nrBS+2) + 20
ymax = maxDist*(nrBS+1) + 20

# maximum number of packets the BS can receive at the same time
maxBSReceives = 8

maxX = maxDist + baseDist*(nrBS)
print "maxX ", maxX
maxY = 2 * maxDist * math.sin(30*(math.pi/180)) # == maxdist
print "maxY", maxY


# prepare graphics and add sink
if (graphics == 1):
    plt.ion()
    plt.figure()
    ax = plt.gcf().gca()

# list of base stations
bs = []

# list of packets at each base station, init with 0 packets
packetsAtBS = []
packetsRecBS = []
for i in range(0,nrBS):
    b = myBS(i)
    bs.append(b)
    packetsAtBS.append([])
    packetsRecBS.append([])


for i in range(0,nrNodes):
    # myNode takes period (in ms), base station id packetlen (in Bytes)
    # 1000000 = 16 min
    for j in range(0,nrBS):
        # create nrNodes for each base station
        node = myNode(i*nrBS+j, avgSendTime,20,bs[j])
        nodes.append(node)

        # when we add directionality, we update the RSSI here
        if (directionality == 1):
            node.updateRSSI()
        env.process(transmit(env,node))

#prepare show
if (graphics == 1):
    plt.xlim([0, maxX+50])
    plt.ylim([0, maxX+50])
    plt.draw()
    plt.show()

# store nodes and basestation locations
with open('nodes.txt', 'w') as nfile:
    for node in nodes:
        nfile.write('{x} {y} {id}\n'.format(**vars(node)))

with open('basestation.txt', 'w') as bfile:
    for basestation in bs:
        bfile.write('{x} {y} {id}\n'.format(**vars(basestation)))

# start simulation
env.run(until=simtime)

print "nr received packets (independent of right base station)", len(recPackets)
print "nr collided packets", len(collidedPackets)
print "nr lost packets (not correct)", len(lostPackets)

sum = 0
for i in range(0,nrBS):
    print "packets at BS",i, ":", len(packetsRecBS[i])
    sum = sum + len(packetsRecBS[i])
print "sent packets: ", packetSeq
print "overall received at right BS: ", sum

sumSent = 0
sent = []
for i in range(0, nrBS):
    sent.append(0)
for i in range(0,nrNodes*nrBS):
    sumSent = sumSent + nodes[i].sent
    print "id for node ", nodes[i].id, "BS:", nodes[i].bs.id, " sent: ", nodes[i].sent
    sent[nodes[i].bs.id] = sent[nodes[i].bs.id] + nodes[i].sent
for i in range(0, nrBS):
    print "send to BS[",i,"]:", sent[i]

print "sumSent: ", sumSent

der = []
# data extraction rate
derALL = len(recPackets)/float(sumSent)
sumder = 0
for i in range(0, nrBS):
    der.append(len(packetsRecBS[i])/float(sent[i]))
    print "DER BS[",i,"]:", der[i]
    sumder = sumder + der[i]
avgDER = (sumder)/nrBS
print "avg DER: ", avgDER
print "DER with 1 network:", derALL

# this can be done to keep graphics visible
if (graphics == 1):
    raw_input('Press Enter to continue ...')

# save experiment data into a dat file that can be read by e.g. gnuplot
# name of file would be:  exp0.dat for experiment 0
fname = "exp" + str(experiment) + "intfDIR5BS.dat"
print fname
if os.path.isfile(fname):
    res = "\n" + str(nrNodes) + " " + str(der[0]) + " " + str(avgDER)
else:
    res = "# nrNodes DER0 AVG-DER\n" + str(nrNodes) + " " + str(der[0]) + " " + str(avgDER)
with open(fname, "a") as myfile:
    myfile.write(res)
myfile.close()
