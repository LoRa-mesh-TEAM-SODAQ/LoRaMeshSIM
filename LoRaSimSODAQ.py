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

width = 2000000
height = 2000000
size = width/250

def onclick(event):
    if event.xdata is not None:
        posx = round(event.xdata)

        if posx >= GW.x - size and posx <= GW.x + size:
            GW.printInfo()
        else:
            for i in range(len(nodes)):
                if posx >= nodes[i].x - size/2 and posx <= nodes[i].x + size/2:
                    nodes[i].printInfo()

# RSSi from node1 to node2
def calcRSSI(sendNode, recNode):
    distToOther = sendNode.calcDistToOther(recNode)
    if distToOther is None:
        print("Something went wrong")
        sendNode.printInfo()
        recNode.printInfo()
        sys.exit(-1)
    else:
        FSL = sendNode.calcFreeSpaceLoss(distToOther)
        RSSI = sendNode.TXpower - FSL
        return [RSSI, distToOther]

def getConnection(self, other):
    point1 = [self.x, self.y]
    point2 = [other.x, other.y]
    xVals = [point1[0], point2[0]]
    yVals = [point1[1], point2[1]]
    return plt.Line2D(xVals, yVals, color='r', linestyle='--', linewidth='.5')

#
# this function creates a node
#
class myNode(object):
    def __init__(self, id, TXp, CF):
        self.id = id
        self.x = random.randint(0, width)
        self.y = random.randint(0, height)
        self.packetList = []
        self.connectionList = []
        self.connectionLines = []
        self.sent = 0
        self.received = 0
        self.TXpower = TXp
        self.energyUsed = 0
        self.carrierFrequency = CF
        self.beacon = None
        self.numberOfHops = 0
        self.sentBeacon = 0
        self.totalTOA = 0
        self.outOfRange = False

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
        print("Out of range:", self.outOfRange)
        print("Distances:")
        print(*self.connectionList, sep="\n")
        print()

    def calcDistToOther(self, other):
        if other is not self:
            xdist = self.x - other.x
            ydist = self.y - other.y
            dist = np.sqrt(xdist * xdist + ydist * ydist)
            return dist
        else:
            print("Cannot calculate distance from self to self")

    def addConnection(self, dict):
        self.connectionList.append(dict)

    def sendPacket(self):
        self.packetList[0].printInfo()
        bitRate = min(DR, key=lambda x: abs(x - self.packetList[0].bitRate))
        Npayload = self.packetList[0].Npayload
        print("Bitrate of packet (bits/s):", bitRate, "DR", DR.index(bitRate))
        print("Nr of symbols packet (bytes):", Npayload)

    def calcFreeSpaceLoss(self, distToOther):
        # FSPL (dB) = 20log10(d) + 20log10(f) + 32.45
        FSL = 20 * math.log(distToOther/1000, 10) + 20 * math.log(self.carrierFrequency, 10) + 32.45
        return FSL

    def addConnectionLine(self, other):
        self.connectionLines.append(getConnection(self, other))

    def sendBeacon(self, env):
        TOA = self.calcTOA(self.beacon)

        yield env.timeout(TOA)

        RXsensi = -174 + 10 * math.log(self.beacon.BW, 10) + SNRvals[self.beacon.SF - 7]

        highestRSSI = [0,-200]

        self.sentBeacon += 1
        self.totalTOA += TOA

        print("Sending beacon at", env.now, "s, from node", self.id, "NoH", self.numberOfHops)
        for i in range(len(self.connectionList)):
            nodeToRec = nodes[self.connectionList[i]['id']]
            RSSIToNodeFromSelf = self.connectionList[i]['RSSI']

            if (nodeToRec.beacon is None) and (RSSIToNodeFromSelf > RXsensi):
                # go through nodes
                # check if RSSI between other node and node to receive beacon is
                # higher than RSSI between this node and node to receive
                print("Looking at node", nodeToRec.id)
                for j in range(len(nodes)):
                    otherNode = nodes[j]
                    if otherNode is not self:
                        for k in range(len(otherNode.connectionList)):
                            if otherNode.connectionList[k]['id'] is nodeToRec.id:
                                RSSIToNodeFromOtherNode = otherNode.connectionList[k]['RSSI']
                                print("\tOther node id:", otherNode.id, ", RSSI:\t", RSSIToNodeFromOtherNode)
                                print("\tOwn RSSI:\t\t\t", RSSIToNodeFromSelf)
                                if RSSIToNodeFromOtherNode > RSSIToNodeFromSelf:
                                    print("\tOther node has setter signal")
                                    if RSSIToNodeFromOtherNode > highestRSSI[1]:
                                        highestRSSI = [otherNode.id, RSSIToNodeFromOtherNode]

                if highestRSSI[1] < RSSIToNodeFromSelf:
                    # self has best signal -> send
                    print("\tNode", nodeToRec.id, "received beacon, RSSI:", RSSIToNodeFromSelf)
                    connections.append(nodeToRec.addConnectionLines(self))

                    nodeToRec.numberOfHops = self.numberOfHops+1
                    nodeToRec.beacon = myBeacon(self.beacon.PL, self.beacon.SF, self.beacon.CR, self.beacon.BW)
                else:
                    print("\tNode", highestRSSI[0], "should send to node", nodeToRec.id)

            elif (nodeToRec.beacon is None) and (RSSIToNodeFromSelf < RXsensi): # RSSI too low
                print("Node", nodeToRec.id, "failed  to receive beacon, RSSI too low")
                print("RX sensitivity:\t", RXsensi)
                print("RSSI:\t\t", RSSIToNodeFromSelf)
            else:
                print("Node", nodeToRec.id, "already received beacon")
        print()

class myGateway(object):
    def __init__(self, id, CF):
        self.id = id
        self.x = width/2
        self.y = height/2
        self.receivedPackets = 0
        self.numberOfHops = 0
        self.connectionList = []
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
        print(*self.connectionList, sep="\n")

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
                self.connectionList.append(dict)
                print(dict)
            return dist

    def addBeacon(self):
        self.beacon = myBeacon(34,
                          7,
                          1,
                          BW[0])
        return 0

    def addConnection(self, dict):
        self.connectionList.append(dict)

class myBeacon(object):
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

        Tsymbol = (2**self.SF) / self.BW
        # Calculate time for preamble and payload
        Tpreamble = (4.25 + self.Npreamble) * Tsymbol
        Tpayload = self.Npayload * Tsymbol
        self.TOA = Tpayload + Tpreamble

        self.RXsensi = -174 + 10 * math.log(self.BW, 10) + SNRvals[self.SF - 7]

class myPacket(object):
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

        # Calculate time to send a single symbol
        Tsymbol = (2**self.SF) / self.BW
        # Calculate time for preamble and payload
        Tpreamble = (4.25 + self.Npreamble) * Tsymbol
        Tpayload = self.Npayload * Tsymbol
        self.TOA = Tpayload + Tpreamble

        self.RXsensi = -174 + 10 * math.log(self.BW, 10) + SNRvals[self.SF - 7]

    def printInfo(self):
        print("PL:", self.PL)
        print("SF:", self.SF)
        print("CR:", self.CR)
        print("BW:", self.BW)

def beaconFromGW():
    if GW.beacon is not None:
        print("Sending beacon from gateway", GW.id)
        for i in range(len(nodes)):
            node = nodes[i]
            # calc RSSI according to distance between GW and node
            RSSID = calcRSSI(GW, node)

            if RSSID[0] > GW.beacon.RXsensi and node.beacon is None: # node received beacon
                GWTN = {'id': node.id, 'RSSI' : RSSID[0], 'dist': RSSID[1]} # gateway to node
                NTGW = {'id': GW.id, 'RSSI' : RSSID[0], 'dist': RSSID[1]} # node to gateway
                print("Node", node.id, " received beacon, RSSI:", RSSID[0])

                # add node to list of connections of GW and other way around
                GW.addConnection(GWTN)
                node.addConnection(NTGW)

                # Set number of hops from GW to node
                node.numberOfHops = GW.numberOfHops + 1
                node.beacon = GW.beacon

                # add graphic lines from node to GW
                node.addConnectionLine(GW)

            else: # node didnt receive beacon
                print("Node", node.id, " failed  to receive beacon, RSSI:", RSSID[0])

        # sort list of connections based on RSSI in ascending order
        GW.connectionList = sorted(GW.connectionList, key=lambda i: i['RSSI'], reverse=True)
        GW.sentBeacon += 1
        return 1
    else:
        print("ERROR: No beacon found in gateway:", GW.id)
        return 0

# checks which node has best signal with receiving node
# returns list with best connection node id and RSSI
def checkSignal(recNode):
    highestRSSI = [0, -200]

    # go through all nodes
    # return higest RSSI value for recNode
    for i in range(len(nodes)):
        otherNode = nodes[i]
        if otherNode is not recNode:
            RSSID = calcRSSI(otherNode, recNode)
            if RSSID[0] > highestRSSI[1] and otherNode.beacon is not None:
                highestRSSI[0] = otherNode.id
                highestRSSI[1] = RSSID[0]
    return highestRSSI

def checkOutOfRange(recNode, RXsensi):
    outOfRange = False
    highestRSSI = checkSignal(recNode)

    print("highestRSSI for node", recNode.id, highestRSSI[1], "with node", highestRSSI[0])
    if highestRSSI[1] < RXsensi:
        outOfRange = True

    return outOfRange

def beaconFromNode(sendNode):
    print("Sending beacon from node", sendNode.id, "NoH:", sendNode.numberOfHops)
    # go through all nodes
    for i in range(len(nodes)):
        recNode = nodes[i]
        print("Looking at node", recNode.id)
        # check if node is not same as sending node and node has no beacon yet
        if sendNode.id is not recNode.id and recNode.beacon is None:
            # calc RSSI according to distance between sending and receiving node
            RSSID = calcRSSI(sendNode, recNode)
            RSSIToRecNodeFromSendNode = RSSID[0]

            if RSSIToRecNodeFromSendNode > sendNode.beacon.RXsensi: # recNode is able to receive beacon
                # go through nodes
                # check if RSSI between other node and node to receive beacon is
                # higher than RSSI between this node and node to receive
                highestRSSID = checkSignal(recNode)

                if highestRSSID[0] == sendNode.id:
                    print("\tBest connection with this node")
                    # sendNode has best connection -> send to recNode
                    SNTRN = {'id': recNode.id, 'RSSI': RSSIToRecNodeFromSendNode, 'dist': RSSID[1]} # sending node to receiver node
                    RNTSN = {'id': sendNode.id, 'RSSI': RSSIToRecNodeFromSendNode, 'dist': RSSID[1]} # receiver node to sending node

                    # add connections to connection lists of nodes
                    recNode.addConnection(RNTSN)
                    sendNode.addConnection(SNTRN)

                    # Set number of hops from recNode to sendnode
                    recNode.numberOfHops = sendNode.numberOfHops + 1
                    recNode.beacon = sendNode.beacon

                    # add graphic lines from recNode to sendnode
                    sendNode.addConnectionLine(recNode)
                    print("\tNode", recNode.id, "received beacon, RSSI:", RSSIToRecNodeFromSendNode)
                else:
                    # other node has better connection to recNode
                    print("\tOther node has setter signal, not sending")
                    print("\tNode", highestRSSID[0], "should send to node", recNode.id)
            else: # RSSI too low
                print("\tNode", recNode.id, "failed to receive beacon, RSSI too low")
                print("\tRX sensitivity:\t", sendNode.beacon.RXsensi)
                print("\tRSSI:\t\t", RSSIToRecNodeFromSendNode)

        elif recNode.beacon is not None:
            print("\tNode", recNode.id, "already received beacon")

def beaconFromNodes():
    NoH = 1
    beaconDone = False
    # go through nodes with NoH = 1, aka in connection with GW
    while not beaconDone:
        for i in range(len(nodes)):
            node = nodes[i]
            if node.numberOfHops == NoH and node.beacon is not None:
                # send beacon from the nodes that received a beacon from GW
                beaconFromNode(node)
                print()

        # next hop
        NoH += 1

        nodesDone = 0
        RXsensi = GW.beacon.RXsensi
        # check if beacon is sent to all nodes that were able to receive it
        for i in range(len(nodes)):
            node = nodes[i]
            if node.beacon is not None:
                print("node", node.id, "is done with beacon, received")
                nodesDone += 1
            elif node.numberOfHops == 0:
                node.outOfRange = checkOutOfRange(node, RXsensi)
            if node.outOfRange:
                print("node", node.id, "is out of range of all nodes")
                nodesDone += 1
        if nodesDone == len(nodes):
            print("End of beacon")
            beaconDone = True

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

def setup():
    # add new nodes to nodes list
    for i in range(0, nrNodes):
        node = myNode(i, TXpowerArg, carrierFrequency)
        nodes.append(node)

    # add beacon to the GW and send it to nodes
    GW.addBeacon()
    if beaconFromGW():
        print("Succesfully sent beacon\n")
        beaconFromNodes()
    else:
        sys.exit(-1)



# start with making a new gateway
GW = myGateway("G0", carrierFrequency)
setup()

# prepare show
if (graphics == 1):
    fig, ax = plt.subplots()
    ax.set_xlim((0, width))
    ax.set_ylim((0, height))

    for i in range(len(nodes)):
        for j in range(len(nodes[i].connectionLines)):
            ax.add_line(nodes[i].connectionLines[j])
        ax.add_artist(nodes[i].graphic)
        ax.annotate(nodes[i].id, (nodes[i].x + width/400, nodes[i].y + width/400), size=6)
    ax.add_artist(GW.graphic)

    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()
    print("End program")
