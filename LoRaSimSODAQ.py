# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 14:59:04 2020

@author: secverg
"""

import simpy
import random
import math
import sys
import matplotlib.pyplot as plt
import numpy as np
import os

global ax
global nodes
global connections
global highestRSSI

width = 1000000
height = 1000000
size = width/250

def onclick(event):
    posx = round(event.xdata)

    if posx >= GW.x - size and posx <= GW.x + size:
        GW.printInfo()
    else:
        for i in range(len(nodes)):
            if posx >= nodes[i].x - size/2 and posx <= nodes[i].x + size/2:
                nodes[i].printInfo()

# RSSi from node1 to node2
def calcRSSI(node1, node2):
    distToOther = node1.calcDistToOther(node2)
    if distToOther is None:
        print("Something went wrong")
        node1.printInfo()
        node2.printInfo()
        sys.exit()
    else:
        FSL = node1.calcFreeSpaceLoss(distToOther)
        RSSI = node1.TXpower - FSL
        return [RSSI, distToOther]

#
# this function creates a node
#
class myNode():
    def __init__(self, id, TXp, CF):
        self.id = id
        self.x = random.randint(0, width)
        self.y = random.randint(0, height)
        self.packetList = []
        self.distanceList = []
        self.sent = 0
        self.received = 0
        self.TXpower = TXp
        self.energyUsed = 0
        self.carrierFrequency = CF
        self.beacon = None
        self.numberOfHops = 0
        self.sentBeacon = 0
        self.totalTOA = 0

        # graphics for node
        global graphics
        if (graphics == 1):
            self.graphic = plt.Circle(
                (self.x, self.y), size, fill=True, color='blue')

        self.packetList.append(myPacket(random.randint(1, 51),
                                        random.randint(7, 12),
                                        1,
                                        random.choice(BW),
                                        0,
                                        0))

    def printInfo(self):
        print("id:", self.id)
        print("node x:", self.x)
        print("node y:", self.y)
        print("node NoH:", self.numberOfHops)
        print("Distances:", end="")
        print(*self.distanceList, sep="\n")
        print()

    def calcDistToOther(self, other):
        if other.id != self.id:

            xdist = self.x - other.x
            ydist = self.y - other.y
            dist = np.sqrt(xdist * xdist + ydist * ydist)
            if dist < 5000:
                dict = {'id': other.id,  'dist': dist,
                        'x':  other.x, 'y': other.y}
                self.distanceList.append(dict)
                print(dict)
            return dist

    def sendPacket(self):
        self.packetList[0].printInfo()
        bitRate = min(DR, key=lambda x: abs(x - self.packetList[0].bitRate))
        Npayload = self.packetList[0].Npayload
        print("Bitrate of packet (bits/s):", bitRate, "DR", DR.index(bitRate))
        print("Nr of symbols packet (bytes):", Npayload)

    def calcTOA(self, packet):
        # Calculate time to send a single symbol
        Tsymbol = (2**packet.SF) / packet.BW
        # Calculate time for preamble and payload
        Tpreamble = (4.25 + packet.Npreamble) * Tsymbol
        Tpayload = packet.Npayload * Tsymbol
        TOA = Tpayload + Tpreamble
        return TOA

    def calcFreeSpaceLoss(self, distToOther):
        # FSPL (dB) = 20log10(d) + 20log10(f) + 32.45
        FSL = 20 * math.log(distToOther/1000, 10) + 20 * math.log(self.carrierFrequency, 10) + 32.45
        return FSL

    def addConnectionLines(self, other):
        point1 = [self.x, self.y]
        point2 = [other.x, other.y]
        xVals = [point1[0], point2[0]]
        yVals = [point1[1], point2[1]]
        return plt.Line2D(xVals, yVals, color='r', linestyle='--', linewidth='.5')

    def sendBeacon(self):
        TOA = self.calcTOA(self.beacon)

        yield env.timeout(TOA)

        RXsensi = -174 + 10 * math.log(self.beacon.BW, 10) + SNRvals[self.beacon.SF - 7]

        self.beacon.numberOfHops += 1
        self.sentBeacon += 1
        self.totalTOA += TOA
        highestRSSI = [0,-200]

        print("Sending beacon at", env.now, "s, from node", self.id)
        for i in range(len(self.distanceList)):
            nodeToRec = nodes[self.distanceList[i]['id']]
            RSSIToNodeFromSelf = self.distanceList[i]['RSSI']

            if (nodeToRec.beacon is None) and (RSSIToNodeFromSelf > RXsensi):
                # go through nodes
                # check if RSSI between other node and node to receive beacon is
                # higher than RSSI between this node and node to receive
                print("Looking at node", nodeToRec.id)
                for j in range(len(nodes)):
                    otherNode = nodes[j]
                    if otherNode is not self:
                        for k in range(len(otherNode.distanceList)):
                            if otherNode.distanceList[k]['id'] is nodeToRec.id:
                                RSSIToNodeFromOtherNode = otherNode.distanceList[k]['RSSI']
                                print("Other node id:", otherNode.id, ",RSSI:", RSSIToNodeFromOtherNode)
                                print("Own RSSI:", RSSIToNodeFromSelf)
                                if RSSIToNodeFromOtherNode > RSSIToNodeFromSelf:
                                    print("Other node has setter signal")
                                    if RSSIToNodeFromOtherNode > highestRSSI[1]:
                                        highestRSSI = [otherNode.id, RSSIToNodeFromOtherNode]
                print(highestRSSI)
                if highestRSSI[1] < RSSIToNodeFromSelf:
                    # self has best signal -> send
                    print("Node", nodeToRec.id, "received beacon, RSSI:", RSSIToNodeFromSelf)
                    connections.append(nodeToRec.addConnectionLines(self))

                    nodeToRec.numberOfHops = self.beacon.numberOfHops
                    nodeToRec.beacon = self.beacon
                else:
                    print("Node", highestRSSI[0], "should send to node", nodeToRec.id)

            elif (nodeToRec.beacon is None) and (RSSIToNodeFromSelf < RXsensi): # RSSI too low
                print("Node", nodeToRec.id, "failed  to receive beacon, RSSI too low")
                print("RX sensitivity:\t", RXsensi)
                print("RSSI:\t\t", RSSIToNodeFromSelf)
            else:
                print("Node", nodeToRec.id, "already received beacon")
        print()

        # for i in range(len(nodes)):
        #      if nodes[i].beacon is None:
        #          self.sendBeacon()


class myGateway():
    def __init__(self, id, CF):
        self.id = id
        self.x = width/2
        self.y = height/2
        self.receivedPackets = 0
        self.numberOfHops = 0
        self.distanceList = []
        self.TXpower = 14
        self.sentBeacon = 0
        self.totalTOA = 0
        self.carrierFrequency = CF

        if (graphics == 1):
            self.graphic = plt.Circle(
                (self.x, self.y), size*1.5, fill=True, color='green')

    def printInfo(self):
        print("GWID:", self.id)
        print("GW x:", self.x)
        print("GW y:", self.y)
        print("Distances:", end="")
        print(*self.distanceList, sep="\n")

    def calcFreeSpaceLoss(self, distToOther):
        # FSPL (dB) = 20log10(d) + 20log10(f) + 32.45
        FSL = 20 * math.log(distToOther/1000, 10) + 20 * math.log(self.carrierFrequency, 10) + 32.45
        return FSL

    def calcDistToOther(self, other):
        if other.id != self.id:

            xdist = self.x - other.x
            ydist = self.y - other.y
            dist = np.sqrt(xdist * xdist + ydist * ydist)
            if dist < 5000:
                dict = {'id': other.id,  'dist': dist,
                        'x':  other.x, 'y': other.y}
                self.distanceList.append(dict)
                print(dict)
            return dist

    def sendBeacon(self, env):
        # Beacon SF, CR, BW need to be determined according to lora specifications
        beacon = myBeacon(34,
                          7,
                          1,
                          BW[0])
        TOA = self.calcTOA(beacon)

        yield env.timeout(TOA)

        RXsensi = -174 + 10 * math.log(beacon.BW, 10) + SNRvals[beacon.SF - 7]
        beacon.numberOfHops += 1
        self.sentBeacon += 1
        self.totalTOA += TOA

        print("Sending beacon at", env.now, "s, from gateway", self.id)
        for i in range(len(nodes)):
            # calc freespaceloss according to distance
            node = nodes[i]
            RSSID = calcRSSI(self, node)

            if RSSID[0] > RXsensi + 3 and node.beacon is None: # node received beacon
                dict = {'id': node.id,  'dist': RSSID[1],
                        'x':  node.x, 'y': node.y, 'RSSI' : RSSID[0]}

                print("Node", node.id, " received beacon, RSSI:", RSSID[0])
                self.distanceList.append(dict)
            else: # node didnt receive beacon
                print("Node", node.id, " failed  to receive beacon, RSSI:", RSSID[0])
        print()

        self.distanceList = sorted(self.distanceList, key=lambda i: i['RSSI'], reverse=True)

        for i in range(len(self.distanceList)):
            node = nodes[self.distanceList[i]['id']]
            connections.append(node.addConnectionLines(self))

            node.numberOfHops = beacon.numberOfHops
            node.beacon = beacon
            highestRSSI = -200

            for j in range(len(nodes)):
                if node.id is not nodes[j].id and nodes[j].beacon is None:
                    #print(nodes[j].beacon)
                    RSSID = calcRSSI(node, nodes[j])

                    if RSSID[0] > RXsensi:
                        dict = {'id': nodes[j].id,  'dist': RSSID[1],
                                'x':  nodes[j].x, 'y': nodes[j].y, 'RSSI': RSSID[0]}
                        node.distanceList.append(dict)
                    # print(node.id)
                    #print(dict)

                node.distanceList = sorted(node.distanceList, key=lambda i: i['RSSI'], reverse=True)
            # print("DL node", node.id)
            # print(*node.distanceList, sep="\n")

            env.process(node.sendBeacon())


    def calcTOA(self, beacon):
        # Calculate time to send a single symbol
        Tsymbol = (2**beacon.SF) / beacon.BW
        # Calculate time for preamble and payload
        Tpreamble = (4.25 + beacon.Npreamble) * Tsymbol
        Tpayload = beacon.Npayload * Tsymbol
        TOA = Tpayload + Tpreamble
        print("Tsymbol:", Tsymbol)
        print("Time on air for beacon:", TOA)
        print()
        return TOA

class myBeacon():
    def __init__(self, packetLength, spreadingFactor, codingRate, bandwidth):
        self.PL = packetLength
        self.SF = spreadingFactor
        self.CR = codingRate
        self.BW = bandwidth
        # Standard preamble for EU 863-870 MHz ISM Band
        # (source https://lora-alliance.org/sites/default/files/2018-05/2015_-_lorawan_specification_1r0_611_1.pdf#page=34)
        self.Npreamble = 10
        self.numberOfHops = 0

        thetaPLSF = (8 * self.PL) - (4 * self.SF) + 44
        gammaSF = 4 * self.SF
        self.Npayload = (
            8 + max(math.ceil(thetaPLSF / gammaSF) * (self.CR + 4), 0))

class myPacket():
    def __init__(self, packetLength, spreadingFactor, codingRate, bandwidth, header, lowDataRateOpt):
        self.PL = packetLength
        self.SF = spreadingFactor
        self.CR = codingRate
        self.BW = bandwidth
        # Standard preamble for EU 863-870 MHz ISM Band
        # (source https://lora-alliance.org/sites/default/files/2018-05/2015_-_lorawan_specification_1r0_611_1.pdf#page=34)
        self.Npreamble = 8
        self.header = header
        self.lowDataRateOpt = lowDataRateOpt

        # Override SF to 7 when using the 250 kHz bandwith
        if self.BW == 250000:
            self.SF = 7

        self.bitRate = round(min(DR, key=lambda x: abs(
            x - self.SF * (self.BW / (2**self.SF)) * (4 / (4 + self.CR)))))

        if DR.index(self.bitRate) == 0 or\
                DR.index(self.bitRate) == 1 or\
                DR.index(self.bitRate) == 2:
            self.PL = random.randint(1, 59)
        elif DR.index(self.bitRate) == 4 or\
                DR.index(self.bitRate) == 5 or\
                DR.index(self.bitRate) == 6 or\
                DR.index(self.bitRate) == 7:
            self.PL = random.randint(1, 115)
        else:
            self.PL = random.randint(1, 222)

        thetaPLSF = (8 * self.PL) - (4 * self.SF) + 44 - (20 * self.header)
        gammaSF = 4 * (self.SF - (2 * self.lowDataRateOpt))
        self.Npayload = (
            8 + max(math.ceil(thetaPLSF / gammaSF) * (self.CR + 4), 0))

    def printInfo(self):
        print("PL:", self.PL)
        print("SF:", self.SF)
        print("CR:", self.CR)
        print("BW:", self.BW)

env = simpy.Environment()

# 1 to show nodes in plot
graphics = 1

# list for all nodes
nodes = []
connections = []

# list for available bandwidths
BW = [125000, 250000]
# list with datarates from lora specifications EU 868-870 MHz ISM band
DR = [250, 440, 980, 1790, 3125, 5470, 11000]
# list with SNR values from SX1276/77/78/79 datasheet in dB
SNRvals = [-7.5, -10, -12.5, -15, -17.5, -20]

# Transmit consumption in mA from -2 to +17 dBm
TX = [22, 22, 22, 23,                                      # RFO/PA0: -2..1
      24, 24, 24, 25, 25, 25, 25, 26, 31, 32, 34, 35, 44,  # PA_BOOST/PA1: 2..14
      82, 85, 90,                                          # PA_BOOST/PA1: 15..17
      105, 115, 125]                                       # PA_BOOST/PA1+PA2: 18..20
receiverModeCurrent = 0.0103    # current draw in A for receiver mode, band 1, BW = 125, SX1276
V = 3.0     # voltage XXX

# get arguments
if len(sys.argv) >= 3:
    nrNodes = int(sys.argv[1])
    TXpowerArg = int(sys.argv[2])
    carrierFrequency = int(sys.argv[3])

    print("Number of nodes: ", nrNodes)
    print("TXpower: ", TXpowerArg)
    print("CarrierFrequency: ", carrierFrequency)
else:
    print("usage: ./loraDir <amount of nodes> <TXpower> <carrierFrequency>")
    sys.exit(-1)

GW = myGateway("G0", carrierFrequency)

# Create nodes with avgSendTime and PacketLength
# and add new nodes to nodes list
for i in range(0, nrNodes):
    node = myNode(i, TXpowerArg, carrierFrequency)
    nodes.append(node)

# Calculate distance between nodes and print node info of all nodes
for i in range(len(nodes)):
    nodes[i].printInfo()

env.process(GW.sendBeacon(env))
env.run(until=10)

# prepare show
if (graphics == 1):
    fig, ax = plt.subplots()
    ax.set_xlim((0, width))
    ax.set_ylim((0, height))

    for i in range(len(connections)):
        ax.add_line(connections[i])
    for i in range(len(nodes)):
        ax.add_artist(nodes[i].graphic)
        ax.annotate(nodes[i].id, (nodes[i].x + width/400, nodes[i].y + width/400), size=6)
    ax.add_artist(GW.graphic)

    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()
