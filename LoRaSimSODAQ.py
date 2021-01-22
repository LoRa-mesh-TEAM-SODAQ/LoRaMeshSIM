# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 14:59:04 2020

@author: secverg
"""

import random
import math
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import Button
import numpy as np
import os

"""Func: onclick(event)
Params:
event             - event object
excecutes a certain function based on where the user clicks inside the plot.
returns:
None"""
def onclick(event):
    if event.xdata is not None:
        posx = round(event.xdata)
        posy = round(event.ydata)

        if posx >= GW.x - size and posx <= GW.x + size and posy >= GW.y - size and posy <= GW.y + size:
            GW.printInfo()
        else:
            for node in nodes:
                if posx >= node.x - size and posx <= node.x + size and\
                   posy >= node.y - size and posy <= node.y + size:
                    node.printInfo()

"""Func: calcRSSI(sendNode, recNode)
Params:
sending node      - myNode object
receiving node    - myNode object
calculates RSSI value between sendNode and recNode
returns:
list [RSSI, distance between recNode and sendNode]"""
def calcRSSI(sendNode, recNode):
    distToOther = sendNode.calcDistToOther(recNode)
    FSL = sendNode.calcFreeSpaceLoss(distToOther)
    atmosphericAttenuation = sendNode.atmosphericAttenuation(distToOther)
    RSSI = sendNode.TXpower - FSL - atmosphericAttenuation
    return [RSSI, distToOther]

"""Func: getConnection(node1, node2)
Params:
node1     - myNode object
node2     - myNode object
Makes a line2D object between the 2 positions of the nodes
returns:
Line2D object"""
def getConnection(node1, node2):
    point1 = [node1.x, node1.y]
    point2 = [node2.x, node2.y]
    xVals = [point1[0], point2[0]]
    yVals = [point1[1], point2[1]]
    return plt.Line2D(xVals, yVals, color='r', linestyle='--', linewidth='.5')

"""Func: def checkSignal(recNode)
Params:
receiving node - myNode object
checks which node has best signal with receiving node
returns:
list [node id, RSSI]"""
def checkSignal(recNode):
    highestRSSI = [0, -200]

    """go through all nodes
       return highest RSSI value for recNode"""
    for otherNode in nodes:
        if otherNode is not recNode:
            RSSID = calcRSSI(otherNode, recNode)
            if RSSID[0] > highestRSSI[1] and otherNode.beacon is not None:
                highestRSSI[0] = otherNode.id
                highestRSSI[1] = RSSID[0]

    return highestRSSI

"""Func: checkOutOfRange(recNode)
Params:
receiving node        - myNode object
checks if the receiving node is in range of any of the nodes that have
received a beacon.
returns:
outOfRange            - boolean"""
def checkOutOfRange(recNode):
    outOfRange = False
    highestRSSI = checkSignal(recNode)
    if highestRSSI[0] == 0 and highestRSSI[1] == -200:
        outOfRange = True
    else:
        bestconNode = nodes[highestRSSI[0]]
        dist = bestconNode.calcDistToOther(recNode)

        #print("highestRSSI for node", recNode.id, highestRSSI[1], "with node", bestconNode.id) ##DEBUG
        if highestRSSI[1] < bestconNode.beacon.RXsensi:
            outOfRange = True
    return outOfRange

class myNode(object):
    def __init__(self, id, TXp, CF):
        self.id = id
        """positional coördinates"""
        self.x = random.randint(0, width)
        self.y = random.randint(0, height)
        """set transmission power & carrierFrequency(gotten from arguments)"""
        self.TXpower = TXp
        self.carrierFrequency = CF
        """lists for different objects the node has"""
        self.packetList = []
        self.connectionList = []
        self.connectionLines = []
        """amount of sent/received packets"""
        self.sent = 0
        self.received = 0
        """energy variables"""
        self.energyUsed = 0
        self.battery = (batteryCapacityArg*V) / 1000
        """mesh setup variables"""
        self.beacon = None
        self.numberOfHops = 0
        """time variables"""
        self.totalTOA = 0
        self.totalTR = 0
        self.totalSleepTime = 0
        self.totalCADTime = 0
        """range/overflow variables"""
        self.outOfRange = False
        self.overflow = False

        """create a matplotlib circle object to use as node graphics"""
        if (graphics == 1):
            self.graphic = plt.Circle(
                (self.x, self.y), size, fill=True, color='blue')

    def printInfo(self):
        days = ((self.totalTOA/3600)/24) + ((self.totalTR/3600)/24) + ((self.totalSleepTime/3600)/24) + ((self.totalCADTime/3600)/24)
        print("id:", self.id)
        print("Node NoH:", self.numberOfHops)
        # print("Out of range:", self.outOfRange)
        # print("Total time on air: {:.2f}".format(self.totalTOA), "s")
        # print("Time spent receiving: {:.2f}".format(self.totalTR), "s")
        # print("Time spent sleeping: {:.2f}".format(self.totalSleepTime), "s")
        # print("Time spent CAD: {:.2f}".format(self.totalCADTime), "s")
        # print("Energy used: {:.2f}".format((1000 * self.energyUsed) / V), "mAh")
        # print("Battery left: {:.2f}".format((1000 * self.battery) / V), "mAh")
        print("{:.2f}".format(days), "days")
        print("Traffic:",self.traffic(), "nodes behind")
        print("Sent packets:",self.sent)
        print("received packets:",self.received)
        print("Connections of node:")
        for i in self.connectionList:
            print("Node:", i.get('Node_Gateway').id, "RSSI: {:.2f}".format(i.get('RSSI')), "dBm,", "distance: {:.2f}".format(i.get('dist')), "m")
        self.possibleConnections()                               ##DEBUG
        print()

    def addPacket(self, packet):
        self.packetList.append(packet)

    def calcDistToOther(self, other):
        if other is not self:
            xdist = self.x - other.x
            ydist = self.y - other.y
            dist = np.sqrt(xdist * xdist + ydist * ydist)
            return dist
        else:
            print("ERROR: Cannot calculate distance from self to self")
            sys.exit(-1)

    def sendPacket(self, recNode, packet):
        """check if packet argument is in packetlist of self"""
        if packet in self.packetList:
            # packet.printInfo()                                         ##DEBUG

            """add time on air to nodes"""
            self.totalTOA += packet.TOA
            recNode.totalTR += packet.TOA

            self.battery -= packet.energyCostTX(self)
            self.energyUsed += packet.energyCostTX(self)
            #print("TX power:", packet.energyCostTX(self))              ##DEBUG
            if isinstance(recNode, myNode):
                recNode.battery -= packet.energyCostRX()
                recNode.energyUsed += packet.energyCostRX()
                #print("RX power:", packet.energyCostRX())              ##DEBUG

            """keep track of how many packets are sent/received"""
            self.sent += 1
            recNode.received += 1

            """add packet to recNode packetlist
               then remove packet from self packetlist
               and finally add sleeping time after sending a packet"""
            recNode.packetList.append(packet)
            self.packetList.remove(packet)
            self.addSleepTime(packet)
        else:
            print("ERROR: Packet is not found at this node")

    def calcFreeSpaceLoss(self, distToOther):
        # FSPL (dB) = 20log10(d) + 20log10(f) + 32.45
        FSL = 20 * math.log(distToOther / 1000, 10) + 20 * math.log(self.carrierFrequency, 10) + 32.45
        return FSL

    def addConnectionLine(self, other):
        self.connectionLines.append(getConnection(self, other))

    def removeConnectionLine(self, other):
        for i in other.connectionLines:
            xdata,ydata = i.get_data()
            # print("self",self.x, self.y)
            # print("other",other.x, other.y)
            if xdata[1] == self.x and ydata[1] == self.y:
                # print("xdat",xdata)
                # print("ydat",ydata)
                other.connectionLines.remove(i)
                #self.connectionLines.remove(i)

    def addConnection(self, Node_Gateway, RSSI, dist):
        dict = {'Node_Gateway': Node_Gateway, 'RSSI': RSSI, 'dist': dist}
        self.connectionList.append(dict)
        self.connectionList = sorted(
            self.connectionList, key=lambda i: i['RSSI'], reverse=True)

    def removeConnection(self, Node_Gateway):
        for i in self.connectionList:
            if i.get('Node_Gateway') is Node_Gateway:
                self.connectionList.remove(i)

    def possibleConnections(self):
        poslist = []
        # print("node", self.id, "can be connected to:")                ##DEBUG
        for i in range(len(nodes)):
            otherNode = nodes[i]
            if otherNode is not self:
                RSSID = calcRSSI(self, otherNode)
                if RSSID[0] > self.beacon.RXsensi:
                    # print("node", otherNode.id, "RSSI:", RSSID[0])    ##DEBUG
                    poslist.append(otherNode)
        return poslist

    def isInConnections(self, node):
        result = False
        for i in self.connectionList:
            nodeInCon = i.get('Node_Gateway')
            if isinstance(nodeInCon, myNode) and nodeInCon == node:
                result = True
        return result

    def traffic(self, amount=0):
        for otherNode in nodes:
            if otherNode is not self:
                if self.isInConnections(otherNode):
                    if self.numberOfHops < otherNode.numberOfHops:
                        if len(otherNode.connectionList) > 1:
                            amount = otherNode.traffic(amount)
                            amount = amount + 1
                        else:
                            amount = amount + 1
        return amount

    def reroute(self):
        for con in self.connectionList:
            node = con.get("Node_Gateway")
            if self.numberOfHops > node.numberOfHops and\
               isinstance(node, myNode) and\
               node.overflow is True:
                # print("othernode is overflowed", node.id)              ##DEBUG
                poscons = self.possibleConnections()
                bestconNode = None
                lastRSSI = -200
                for posconNode in poscons:
                    if posconNode is not self and\
                       posconNode is not node and\
                       self.numberOfHops > posconNode.numberOfHops and\
                       posconNode.traffic() <= self.traffic():
                        temp = calcRSSI(self, posconNode)
                        if lastRSSI < temp[0]:
                            lastRSSI = temp[0]
                            bestconNode = posconNode

                if bestconNode is not None:
                    # print("New connection:", posconNode.id)            ##DEBUG
                    self.removeConnection(node)
                    node.removeConnection(self)

                    self.removeConnectionLine(node)
                    node.removeConnectionLine(self)

                    self.addConnection(bestconNode, temp[0], temp[1])
                    bestconNode.addConnection(self, temp[0], temp[1])
                    self.addConnectionLine(bestconNode)
                    print("Reroute node", self.id, "!!")

    def atmosphericAttenuation(self, distance):
        """
        Atmospheric gases (oxygen and water vapor), fog and rain can add to the
        free space loss attenuation and their effects are worst at 2.4 GHz.
        However the total attenuation is still fairly negligible and rarely
        becomes worst than 0.02 dB/Km.
        For a 50 Km link this translates to an additional attenuation of 1 dB.
        Source: http://afar.net/tutorials/900-mhz-versus-2-4-ghz/

        Attenuation has been set at 0.01 per km, to add some air simulation for
        868MHz. This value is somewhat arbitrary but makes the simulation a
        little more realistic. This attenuation can be changed in the end of
        this code.
        """
        return distance * airAttenuation
        #print("RSSI after atmos atten:", self.RXsensi, "dist", distance) ## DEBUG

    def addSleepTime(self, packet):
        """
        Send every ... minutes. Can make the lifetime
        of the nodes significantly higher.
        """
        # minutes = 15
        # sleepTime = minutes * 60
        """
        send as many times as you can, keeping in mind the 0,01
        duty cycle for lora, but not the maximum uplink time for
        LoRaWAN (30 seconds per day).
        source:
        https://www.thethingsnetwork.org/forum/t/limitations-data-rate-packet-size-30-seconds-uplink-and-10-messages-downlink-per-day-fair-access-policy-guidelines/1300
        """
        sleepTime = (packet.TOA / 0.01) - packet.TOA
        sleepPower = ((sleepModeCurrent * V) * sleepTime) * 0.000278
        self.totalSleepTime += sleepTime
        self.energyUsed += sleepPower
        self.battery -= sleepPower

    def addCADTime(self, packet):
        CADTimeRXMode = (32 / packet.BW + packet.Tsymbol)
        CADTimeProcessingMode = (packet.SF * pow(2, packet.SF)) / (1750000)
        CADPower = (((CADcurrent * V) * CADTimeRXMode) * 0.000278) + ((((CADcurrent/2) * V) * CADTimeProcessingMode) * 0.000278)
        self.totalCADTime += CADTimeRXMode + CADTimeProcessingMode
        self.energyUsed += CADPower
        self.battery -= CADPower

class myGateway(object):
    def __init__(self, id, CF, x, y):
        self.id = id
        self.x = x
        self.y = y
        self.received = 0
        self.numberOfHops = 0
        self.connectionList = []
        self.packetList = []
        self.TXpower = 14
        self.totalTOA = 0
        self.totalTR = 0
        self.carrierFrequency = CF

        if (graphics == 1):
            self.graphic = plt.Circle(
                (self.x, self.y), size * 1.5, fill=True, color='green')

    def printInfo(self):
        print("GWID:", self.id)
        print("GW x:", self.x)
        print("GW y:", self.y)
        print("Distances:", end="")
        print(*self.connectionList, sep="\n")

    def calcFreeSpaceLoss(self, distToOther):
        # FSPL (dB) = 20log10(d) + 20log10(f) + 32.45
        FSL = 20 * math.log(distToOther / 1000, 10) + 20 * math.log(self.carrierFrequency, 10) + 32.45
        return FSL

    def calcDistToOther(self, other):
        if other.id != self.id:
            xdist = self.x - other.x
            ydist = self.y - other.y
            dist = np.sqrt(xdist * xdist + ydist * ydist)
            return dist

    def addBeacon(self):
        self.beacon = myBeacon(34,
                               7,
                               1,
                               BW[0])

    def addConnection(self, Node_Gateway, RSSI, dist):
        dict = {'Node_Gateway': Node_Gateway, 'RSSI': RSSI, 'dist': dist}
        self.connectionList.append(dict)
        self.connectionList = sorted(
            self.connectionList, key=lambda i: i['RSSI'], reverse=True)

    def atmosphericAttenuation(self, distance):
        """
        Atmospheric gases (oxygen and water vapor), fog and rain can add to the
        free space loss attenuation and their effects are worst at 2.4 GHz.
        However the total attenuation is still fairly negligible and rarely
        becomes worst than 0.02 dB/Km.
        For a 50 Km link this translates to an additional attenuation of 1 dB.
        Source: http://afar.net/tutorials/900-mhz-versus-2-4-ghz/

        Attenuation has been set at 0.01 per km, to add some air simulation for
        868MHz. This value is somewhat arbitrary but makes the simulation a
        little more realistic.
        """
        return distance * airAttenuation

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
        self.NF = 7

        thetaPLSF = (8 * self.PL) - (4 * self.SF) + 44
        gammaSF = 4 * self.SF
        self.Npayload = (
            8 + max(math.ceil(thetaPLSF / gammaSF) * (self.CR + 4), 0))

        Tsymbol = (2**self.SF) / self.BW
        # Calculate time for preamble and payload
        Tpreamble = (4.25 + self.Npreamble) * Tsymbol
        Tpayload = self.Npayload * Tsymbol
        self.TOA = Tpayload + Tpreamble

        """
        Rx sensitivity = -174 + 10log10(BW) + NF + SNR (3)
        ...means..:

        BW = bandwidth in Hz,
        NF = noise factor in dB,
        SNR = signal to noise ratio. It indicates how far the signal exceeds
        ...must be the noise.

        According to SX1276-7-8-9 datasheet:
        RX input level (pin)  | NF band 1
        Pin <= AgcThresh1     | 7
        source: https://smartmakers.io/en/lorawan-range-part-1-the-most-important-factors-for-a-good-lorawan-signal-range/
        """
        self.RXsensi = -174 + 10 * math.log(self.BW, 10) + SNRvals[self.SF - 7] + self.NF

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
        self.linkBudget = 0
        self.NF = 7

        # Override SF to 7 when using the 250 kHz bandwith
        if self.BW == 250000:
            self.SF = 7

        self.bitRate = round(min(DR, key=lambda x: abs(
            x - self.SF * (self.BW / (2**self.SF)) * (4 / (4 + self.CR)))))

        thetaPLSF = (8 * self.PL) - (4 * self.SF) + 44 - (20 * self.header)
        gammaSF = 4 * (self.SF - (2 * self.lowDataRateOpt))
        self.Npayload = (
            8 + max(math.ceil(thetaPLSF / gammaSF) * ((4/ (4+self.CR)) + 4), 0))

        # Calculate time to send a single symbol
        self.Tsymbol = (2**self.SF) / self.BW
        # Calculate time for preamble and payload
        Tpreamble = (4.25 + self.Npreamble) * self.Tsymbol
        Tpayload = self.Npayload * self.Tsymbol
        self.TOA = Tpayload + Tpreamble

        self.RXsensi = -174 + 10 * math.log(self.BW, 10) + SNRvals[self.SF - 7] + self.NF

    def printInfo(self):
        print("PL:", self.PL)
        print("SF:", self.SF)
        print("CR:", self.CR)
        print("BW:", self.BW)
        print("TOA", self.TOA)
        print("LinkBudget:", self.linkBudget)
        print("Bitrate of packet (bits/s):",
              self.bitRate, "DR", DR.index(self.bitRate))
        print("Nr of symbols packet (bytes):", self.Npayload)

    def energyCostTX(self, node):
        totalTXpower = (((TX[node.TXpower + 2]/1000) * V) * (self.TOA)) * 0.000278
        return totalTXpower

    def energyCostRX(self):
        totalRXpower = ((receiverModeCurrent * V) * (self.TOA)) * 0.000278
        return totalRXpower

class Index(object):
    """Func: reset()
      Params:
      None
      Is called by the onClick function. Resets all data and makes new plot.
      returns:
      None"""
    def reset(self, event):
        print("Resetting plot...")
        nodes.clear()

        GW = myGateway("G0", 868, width / 4, height / 4)

        setup(True)

    def randomPacketTillBattEmpty(self, event):
        print("Calculating, please wait...")
        batteryEmpty = False

        while not batteryEmpty:
            callback.sendRandomPacket(event)
            for node in nodes:
                if not node.outOfRange:
                    # print(node.battery)                                ##DEBUG
                    if node.battery <= 0:
                        batteryEmpty = True
                        print("Battery of node", node.id, "is empty")
                        node.printInfo()
                        break

    def sendRandomPacket(self, event):
        # print("Sending packet...")
        """get packet to send"""
        packet = getPacket(spreadingFactorArg, 1, BW[0], 0, packetSizeArg)

        """pick random node to send the packet and add the randPacket to its list"""
        randNode = nodes[random.randint(0, len(nodes)) - 1]
        randNode.addPacket(packet)

        """send packet to a node in randNode's connection list
           can only be done if:
           randNode has a connection
           the connection is to a node with less number of hops"""
        if randNode.connectionList:
            # print out randNode's connections                          ## DEBUG
            # print("node", randNode.id, "nodes to send to", )
            # for i in randNode.connectionList:
                # print("Node:", i.get('Node_Gateway').id, "RSSI:",
                      # i.get('RSSI'), "distance:", i.get('dist'))
            sendToGW(randNode, packet)
        else:
            # print("randNode", randNode.id, "has no node to send to")   ##DEBUG
            callback.sendRandomPacket(event)

def getPacket(SF, CR, BW, H, PL):
    """turn lowDataRateOpt for SF is higher or equal to 11
       rule according to EU868 band"""
    if BW == 125000 and SF >= 11:
        lowDataRateOpt = 1
    else:
        lowDataRateOpt = 0
    return myPacket(PL, SF, CR, BW, H, lowDataRateOpt)

def getRandomPacket():
    SF = 7#random.randint(7, 12)
    codingRate = 1
    bandwidth = BW[0]#random.choice(BW)
    header = 0

    """turn lowDataRateOpt for SF is higher or equal to 11
       rule according to EU868 band"""
    if bandwidth == 125000 and SF >= 11:
        lowDataRateOpt = 1
    else:
        lowDataRateOpt = 0

    """Override SF for BW = 250 kHz"""
    if bandwidth == 250000:
        SF = 7

    """packetsize limitations
       rule according to EU868 band"""
    if bandwidth == 125000 and SF == 9:
        packetLength = 100
    elif bandwidth == 125000 and SF <= 8 or bandwidth == 250000 and SF == 7:
        packetLength = 100
    else:
        packetLength = 10

    return myPacket(packetLength, SF, codingRate, bandwidth, header, lowDataRateOpt)

def sendToGW(node, packet):
    atGateway = False

    while not atGateway:
        for i in node.connectionList:
            recNode = i.get('Node_Gateway')

            if recNode.numberOfHops < node.numberOfHops:
                # print("This is the node to send to next:", recNode.id) ##DEBUG
                packet.linkBudget = packet.RXsensi - node.TXpower
                node.sendPacket(recNode, packet)
                #print("Battery of node:", node.battery, " ", node.id)

                if isinstance(recNode, myNode):
                    recNode.addCADTime(packet)
                node = recNode
            if isinstance(recNode, myGateway):
                atGateway = True
                # print("packet received at Gateway")                    ##DEBUG
                break

def beaconFromGW(GW):
    if GW.beacon is not None:
        # print("Sending beacon from gateway", GW.id)                    ##DEBUG
        for i in range(len(nodes)):
            node = nodes[i]
            """calc RSSI according to distance between GW and node"""
            RSSID = calcRSSI(GW, node)

            if RSSID[0] > GW.beacon.RXsensi and node.beacon is None:  # node received beacon
                # print("Node", node.id, " received beacon, RSSI:", RSSID[0])           ##DEBUG

                """add node to list of connections of GW and other way around
                   gateway to node"""
                GW.addConnection(node, RSSID[0], RSSID[1])
                """node to gateway"""
                node.addConnection(GW, RSSID[0], RSSID[1])

                """Set number of hops from GW to node"""
                node.numberOfHops = GW.numberOfHops + 1
                node.beacon = GW.beacon

                """add graphic lines from node to GW"""
                node.addConnectionLine(GW)

            #else:  # node didnt receive beacon
                # print("Node", node.id," failed  to receive beacon, RSSI:", RSSID[0])  ##DEBUG
        return 1
    else:
        # print("ERROR: No beacon found in gateway:", GW.id)                            ##DEBUG
        return 0

def beaconFromNode(sendNode):
    # print("Sending beacon from node", sendNode.id,
    #      "NoH:", sendNode.numberOfHops)  ##DEBUG

    """go through all nodes"""
    for recNode in nodes:
        # print("Looking at node", recNode.id) ##DEBUG

        """check if node is not same as sending node and node has no beacon yet"""
        if sendNode.id is not recNode.id and recNode.beacon is None:
            """calc RSSI according to distance between sending and receiving node"""
            RSSID = calcRSSI(sendNode, recNode)
            RSSIToRecNodeFromSendNode = RSSID[0]

            if RSSIToRecNodeFromSendNode > sendNode.beacon.RXsensi:  # recNode is able to receive beacon
                """ go through nodes
                    check if RSSI between other node and node to receive beacon is
                    higher than RSSI between this node and node to receive"""
                highestRSSID = checkSignal(recNode)
                bestconNode = nodes[highestRSSID[0]]

                if bestconNode.id == sendNode.id or sendNode.isInConnections(bestconNode):
                    """sendNode has best connection or is node with least hops -> send to recNode"""
                    # print("Looking at node", recNode.id) ##DEBUG
                    # if sendNode.isInConnections(bestconNode):
                    #     print("\tNot best connection with this node, but less hops")
                    # else:
                    #     print("\tBest connection with this node")                      ##DEBUG

                    if bestconNode not in sendNode.connectionList:
                        """add connections to connection lists of nodes
                           sending node to receiver node"""
                        sendNode.addConnection(
                            recNode, RSSIToRecNodeFromSendNode, RSSID[1])

                        """add graphic lines from recNode to sendnode"""
                        sendNode.addConnectionLine(recNode)

                    if bestconNode not in recNode.connectionList:
                        """receiver node to sending node"""
                        recNode.addConnection(
                            sendNode, RSSIToRecNodeFromSendNode, RSSID[1])

                        """Set number of hops from recNode to sendnode"""
                        recNode.numberOfHops = sendNode.numberOfHops + 1
                        recNode.beacon = sendNode.beacon

                    #print("\tNode", recNode.id, "received beacon, RSSI:",
                    #      RSSIToRecNodeFromSendNode)                       ##DEBUG
                # else:  # other node has better connection to recNode
                    # print("\tOther node has better signal, not sending")
                    # print("\tNode", highestRSSID[0],
                    #      "should send to node", recNode.id)               ##DEBUG
            #else:  # RSSI too low
                #print("\tNode", recNode.id,
                #      "failed to receive beacon, RSSI too low")
                #print("\tRX sensitivity:\t", sendNode.beacon.RXsensi)
                #print("\tRSSI:\t\t\t", RSSIToRecNodeFromSendNode)          ##DEBUG

def beaconFromNodes():
    NoH = 1
    beaconDone = False

    """go through nodes with NoH = 1, aka in connection with GW"""
    while not beaconDone:
        for node in nodes:
            if node.numberOfHops == NoH and node.beacon is not None:
                """send beacon from the nodes that received a beacon from GW or other Node"""
                beaconFromNode(node)

        """next hop"""
        NoH += 1

        nodesDone = 0
        """check if beacon is sent to all nodes that were able to receive it"""
        for node in nodes:
            if node.beacon is not None:
                """node has a beacon and is done."""
                #print("node", node.id, "is done with beacon, received") #DEBUG
                nodesDone += 1
            elif node.numberOfHops == 0:
                """check if this node can connect to a node with a beacon next hop"""
                node.outOfRange = checkOutOfRange(node)
            if node.outOfRange:
                """node has no possibility to connect to any nodes with a beacon
                   this means this node is done."""
                #print("node", node.id, "is out of range of all nodes") #DEBUG
                nodesDone += 1

        if nodesDone == len(nodes):
            """all nodes either have received a beacon or are out of range."""
            print("End of beacon")
            beaconDone = True

"""Func: showPlot(reset)
Params:
reset - boolean
Prepares plot and makes window in which to show the figure.
If reset = False, the plot will be made for the first time.
If reset = True, the plot will be cleared and filled with new data.
returns:
None"""
def showPlot(reset):
    if reset:
        ax.cla()
    ax.set_xlim((0, width))
    ax.set_ylim((0, height))

    for node in nodes:
        for connection in node.connectionLines:
            ax.add_line(connection)
        ax.add_artist(node.graphic)
        ax.annotate(node.id, (node.x + width /400, node.y + width / 400), size=6)
    ax.add_artist(GW.graphic)

    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    if reset:
        plt.draw()
    else:
        breset = Button(axreset, 'Reset')
        breset.on_clicked(callback.reset)
        brandpacket = Button(axrandpacket, 'Random packet')
        brandpacket.on_clicked(callback.sendRandomPacket)
        bsendtillempty = Button(axsendtillempty, 'Send untill empty')
        bsendtillempty.on_clicked(callback.randomPacketTillBattEmpty)
        plt.show()

"""Func: setup(reset)
Params:
reset - boolean
Main program.
If reset = False, it's first time setup.
If reset = True, all data from nodes and gateway is deleted and is
randomly generated again.
returns:
None"""
def setup(reset):
    """add new nodes to nodes list"""
    for i in range(0, nrNodesArg):
        node = myNode(i, TXpowerArg, 868)
        nodes.append(node)

    """add beacon to the GW and send it to nodes"""
    GW.addBeacon()

    if beaconFromGW(GW):
        print("Succesfully sent beacon")
        beaconFromNodes()

        for node in nodes:
            if node.traffic() > 4:
                node.overflow = True
            else:
                node.overflow = False

            node.reroute()

        for node in nodes:
            if node.traffic() > 4:
                print("Overflow!!")
                node.graphic = plt.Circle((node.x, node.y), size, fill=True, color='red')
            else:
                node.graphic = plt.Circle((node.x, node.y), size, fill=True, color='blue')

        if reset:
            showPlot(True)
        else:
            showPlot(False)
        print("\n")
    else:
        sys.exit(-1)

"""plot axis variables"""
fig, ax = plt.subplots()
axreset = plt.axes([0.58, 0.9, 0.1, 0.075])
axrandpacket = plt.axes([0.7, 0.9, 0.2, 0.075])
axsendtillempty = plt.axes([0.36, 0.9, 0.2, 0.075])

"""parameters for plot and node size
   width and height is in meters."""
width = 30000
height = 30000
size = width / 250

"""1 to show nodes in plot"""
graphics = 1

"""list for all nodes"""
nodes = []
connections = []

"""list for available bandwidths"""
BW = [125000, 250000]
"""list with datarates from lora specifications EU 868-870 MHz ISM band"""
DR = [250, 440, 980, 1790, 3125, 5470, 11000]
"""list with SNR values from SX1276/77/78/79 datasheet in dB"""
SNRvals = [-7.5, -10, -12.5, -15, -17.5, -20]

"""Transmit consumption in mA from -2 to +20 dBm"""
TX = [22, 22, 22, 23,                                       # RFO/PA0:          -2..1
      24, 24, 24, 25, 25, 25, 25, 26, 31, 32, 34, 35, 44,   # PA_BOOST/PA1:     2..14
      82, 85, 90,                                           # PA_BOOST/PA1:     15..17
      105, 115, 125]                                        # PA_BOOST/PA1+PA2: 18..20

"""current draw in A for receiver mode, band 1, BW = 125, SX1276"""
receiverModeCurrent = 0.0103
"""current draw in A for sleep mode SX1276"""
sleepModeCurrent = 0.0000002
CADcurrent = 0.006
V = 3.3                                                     # voltage XXX

"""air attenuation for decreasing signal strength based on distance"""
airAttenuation = 0.003

"""get arguments"""
if len(sys.argv) >= 7:
    nrNodesArg          = int(sys.argv[1])
    TXpowerArg          = int(sys.argv[2])
    spreadingFactorArg  = int(sys.argv[3])
    batteryCapacityArg  = int(sys.argv[4])
    packetSizeArg       = int(sys.argv[5])
    periodArg           = int(sys.argv[6])

    print("Number of nodes: \t",  nrNodesArg)
    print("TX power: \t\t",         TXpowerArg)
    print("Spreading factor: \t", spreadingFactorArg)
    print("Battery capacity: \t", batteryCapacityArg)
    print("Packet size: \t\t",    packetSizeArg)
    print("Period: \t\t",           periodArg)
else:
    print("usage: ./LoRaSimSODAQ.py <numberOfNodes> <TXpower> <spreadingFactor> <batteryCapacity> <packetSize> <period>")
    sys.exit(-1)

"""start with making a new gateway"""
GW = myGateway("G0", 868, width / 2, height / 2)

"""add callback funcionality"""
callback = Index()

"""setup simulation for first time."""
setup(False)
