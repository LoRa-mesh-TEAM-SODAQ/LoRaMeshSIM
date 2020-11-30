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

#
# this function creates a node
#


class myNode():
    def __init__(self, nodeid, TXp, CF):
        self.nodeid = nodeid
        self.x = random.randint(0, 500)
        self.y = random.randint(0, 500)
        self.packetList = []
        self.distanceList = []
        self.sent = 0
        self.received = 0
        self.TXpower = TX[TXp]
        self.energyUsed = 0
        self.numberOfHops = 0
        self.carrierFrequency = CF

        # graphics for node
        global graphics
        if (graphics == 1):
            self.graphic = plt.Circle(
                (self.x, self.y), 2, fill=True, color='blue')

        self.packetList.append(myPacket(random.randint(1, 51),
                                        random.randint(7, 12),
                                        1,
                                        random.choice(BW),
                                        0,
                                        0))

    def printInfo(self):
        print("NodeID:", self.nodeid)
        print("node x:", self.x)
        print("node y:", self.y)
        print("Distances:", end="")
        print(*self.distanceList, sep=", ")

    def calcDist(self, nodes):
        for i in range(len(nodes)):
            if nodes[i].nodeid != self.nodeid:
                nodeDist = []
                xdist = self.x - nodes[i].x
                ydist = self.y - nodes[i].y
                nodeDist.append(nodes[i].nodeid)
                nodeDist.append(np.sqrt(xdist * xdist + ydist * ydist))
                self.distanceList.append(nodeDist)

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
        print("Tsymbol:", Tsymbol)
        print("Time on air for packet number",
              self.packetList.index(packet), ":", TOA)
        print()


class myGateway():
    def __init__(self, gateID):
        self.gateID = gateID
        self.x = 250
        self.y = 250
        self.receivedPackets = 0
        self.numberOfHops = 0
        self.distanceList = []

        if (graphics == 1):
            self.graphic = plt.Circle(
                (self.x, self.y), 5, fill=True, color='green')




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


# 1 to show nodes in plot
graphics = 1

# list for all nodes
nodes = []

# list for available bandwidths
BW = [125000, 250000]
# list with datarates from lora specifications EU 868-870 MHz ISM band
DR = [250, 440, 980, 1790, 3125, 5470, 11000]

# compute energy
# Transmit consumption in mA from -2 to +17 dBm
TX = [22, 22, 22, 23,                                      # RFO/PA0: -2..1
      24, 24, 24, 25, 25, 25, 25, 26, 31, 32, 34, 35, 44,  # PA_BOOST/PA1: 2..14
      82, 85, 90,                                          # PA_BOOST/PA1: 15..17
      105, 115, 125]                                       # PA_BOOST/PA1+PA2: 18..20
# mA = 90    # current draw for TX = 17 dBm
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



# Create nodes with avgSendTime and PacketLength
# and add new nodes to nodes list
for i in range(0, nrNodes):
    node = myNode(i, TXpowerArg, carrierFrequency)
    nodes.append(node)

# Calculate distance between nodes and print node info of all nodes
for i in range(len(nodes)):
    nodes[i].calcDist(nodes)
    nodes[i].printInfo()
    nodes[i].sendPacket()
    nodes[i].calcTOA(nodes[i].packetList[0])

GW = myGateway(0)

# prepare show
if (graphics == 1):
    fig, ax = plt.subplots()
    ax.set_xlim((0, 500))
    ax.set_ylim((0, 500))
    for i in range(len(nodes)):
        plt.gcf().gca().add_artist(nodes[i].graphic)
    plt.gcf().gca().add_artist(GW.graphic)
    plt.show()
