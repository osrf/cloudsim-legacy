#!/usr/bin/python

from time import gmtime, strftime
from launchers.launch_utils import SshClient
import os

class TrafficShaper:
    
    INITIAL_PACKET_LATENCY_MS = 0    
    MAX_PACKET_LATENCY_MS = 500
    INITIAL_PACKET_LOSS_PERCENTAGE = 0
    MAX_PACKET_LOSS_PERCENTAGE = 40
    OCU_VPN_IP = '11.8.0.2'
    UNKNOWN, KNOWN = range(2)
    REMOTE_USERNAME = 'ubuntu'
    LOG_FILE_NAME = '/tmp/trafficShaper.log'
        
    def __init__(self, _constellationName, _keyDirectory, _keyPairName, _trafficShaperIP, _interface):
        self.constellationName = _constellationName
        self.keyDirectory = _keyDirectory
        self.keyPairName = _keyPairName     
        #ToDo: Remove this atribute when the traffic shaper runs within the router instead of within cloudsim
        self.trafficShaperIP = _trafficShaperIP
        self.interface = _interface
        
        self.targetPacketLatency = TrafficShaper.INITIAL_PACKET_LATENCY_MS
        self.targetPacketLoss = TrafficShaper.INITIAL_PACKET_LOSS_PERCENTAGE
        
        #ToDo: update these values when running as a daemon in the future
        self.ocuStatus = TrafficShaper.UNKNOWN
        self.ocuCurrentPacketLatency = 0
        self.ocuCurrentPacketLoss = 0
        self.ocuIP = TrafficShaper.OCU_VPN_IP
        
        #Handler to manage the remote execution of tc commands. ToDo: Remove this in the future when running as a daemon locally
        self.ssh_handler = SshClient(self.keyDirectory, self.keyPairName, TrafficShaper.REMOTE_USERNAME, self.trafficShaperIP)
        
        tc_cmd = 'init_tc.py ' + self.interface
        self.ssh_handler.cmd(tc_cmd)               
    
    def setTargetPacketLatency(self, _newTargetPacketLatency):
        if _newTargetPacketLatency >= 0 and _newTargetPacketLatency <= TrafficShaper.MAX_PACKET_LATENCY_MS:
            self.targetPacketLatency = _newTargetPacketLatency
            self.log('setTargetPacketLatency() targetPacketLatency changed to ' + str(_newTargetPacketLatency) + ' ms')
        else:
            self.log('setTargetPacketLatency() Illegal <_newTargetPacketLatency> argument: ' + str(_newTargetPacketLatency))
    
    def setTargetPacketLoss(self, _newTargetPacketLoss):
        if _newTargetPacketLoss >= 0 and _newTargetPacketLoss <= TrafficShaper.MAX_PACKET_LOSS_PERCENTAGE:
            self.targetPacketLoss = _newTargetPacketLoss
            self.log('setTargetPacketLoss() targetPacketLoss changed to ' + str(_newTargetPacketLoss) + ' %')
        else:
            self.log('setTargetPacketLoss() Illegal <_newTargetPacketLoss> argument: ' + str(_newTargetPacketLoss))
     
    def setOcuCurrentPacketLatency(self, _newOcuCurrentPacketLatency):    
        if _newOcuCurrentPacketLatency >= 0:
            self.ocuCurrentPacketLatency = _newOcuCurrentPacketLatency
            self.log('setOcuCurrentPacketLatency() ocuCurrentPacketLatency changed to ' + str(_newOcuCurrentPacketLatency) + ' ms')
        else:
            self.log('setOcuCurrentPacketLatency() Illegal <_newOcuCurrentPacketLatency> argument: ' + str(_newOcuCurrentPacketLatency))
            
    def setOcuCurrentPacketLoss(self, _newOcuCurrentPacketLoss):
        if _newOcuCurrentPacketLoss >= 0:
            self.ocuCurrentPacketLoss = _newOcuCurrentPacketLoss
            self.log('setOcuCurrentPacketLoss() ocuCurrentPacketLoss changed to ' + str(_newOcuCurrentPacketLoss) + ' %')
        else:
            self.log('setOcuCurrentPacketLoss() Illegal <_newOcuCurrentPacketLoss> argument: ' + str(_newOcuCurrentPacketLoss))           
    
    def log(self, _msg):
        f = open(os.path.join(TrafficShaper.LOG_FILE_NAME), 'a')
        now = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        f.write('[' + str(now) + '] ' + str(_msg) + '\n')
        f.close() 
    
    def update(self):
        extraPacketLatency = max(self.targetPacketLatency - self.ocuCurrentPacketLatency, 0)
        extraPacketLoss = max(self.targetPacketLoss - self.ocuCurrentPacketLoss, 0)
            
        tc_cmd = 'configure_tc.py ' + str(self.interface) + ' ' + str(extraPacketLatency) + 'ms ' + str(extraPacketLoss) + '%'        
        self.ssh_handler.cmd(tc_cmd)
        self.log('New traffic shaper command sent to ' + str(self.trafficShaperIP) + ', with key ' + str(self.keyPairName) + ' in directory ' + str(self.keyDirectory) + ' (extraPacketLatency= ' + str(self.targetPacketLatency) + ', extraPacketLoss= ' + str(extraPacketLoss) + ')')       
        
