''' Z-Wave NVM Test Utility

    This Python program provides some test functions for testing the Z-Wave chip external NVM.
    The Z-Wave 500 series chip must be programmed with the SerialAPI.

    This program is a DEMO only and is provided AS-IS and without support. 
    But feel free to copy and improve!

    Usage: python TestNVM.py [COMx]
    COMx is optional and is the COM port or /dev/tty* port of the Z-Wave interface.
    Tested using Python 2.7 - untested on Python 3

   References:
   SerialAPI: https://www.silabs.com/documents/login/user-guides/INS12350-Serial-API-Host-Appl.-Prg.-Guide.pdf (or search "SerialAPI" on the silabs site)
   NVM Interface: INS13954-7 Application Programmers Guide V6.81.xx section 4.8 describes the NVM API


'''

import serial           # serial port control
import sys
import time
import os
from struct            import * # PACK


COMPORT       = "/dev/ttyAMA0" # Serial port default on a Raspberry Pi

VERSION       = "1.0 - 3/18/2019"       # Version of this python program
DEBUG         = 4     # (0-10) higher values print out more debugging info - 0=off

# Handy defines mostly copied from ZW_transport_api.py
FUNC_ID_SERIAL_API_GET_INIT_DATA    = 0x02
FUNC_ID_SERIAL_API_APPL_NODE_INFORMATION = 0x03
FUNC_ID_SERIAL_API_GET_CAPABILITIES = 0x07
FUNC_ID_SERIAL_API_SOFT_RESET       = 0x08
FUNC_ID_ZW_GET_PROTOCOL_VERSION     = 0x09
FUNC_ID_ZW_SEND_DATA                = 0x13
FUNC_ID_ZW_GET_VERSION              = 0x15
FUNC_ID_GET_HOME_ID                 = 0x20
FUNC_ID_NVM_GET_MFG_ID              = 0x29
FUNC_ID_NVM_EXT_READ_BUF            = 0x2A
FUNC_ID_NVM_EXT_WRITE_BUF           = 0x2B
FUNC_ID_NVM_EXT_WRITE_BYTE          = 0x2D
FUNC_ID_ZW_SET_DEFAULT              = 0x42
FUNC_ID_ZW_ADD_NODE_TO_NETWORK      = 0x4A
FUNC_ID_ZW_REMOVE_NODE_FROM_NETWORK = 0x4B
FUNC_ID_ZW_FIRMWARE_UPDATE_NVM      = 0x78

# Firmware Update NVM commands
FIRMWARE_UPDATE_NVM_INIT            = 0
FIRMWARE_UPDATE_NVM_SET_NEW_IMAGE   = 1
FIRMWARE_UPDATE_NVM_GET_NEW_IMAGE   = 2
FIRMWARE_UPDATE_NVM_UPDATE_CRC16    = 3
FIRMWARE_UPDATE_NVM_IS_VALID_CRC16  = 4
FIRMWARE_UPDATE_NVM_WRITE           = 5

# Z-Wave Library Types
ZW_LIB_CONTROLLER_STATIC  = 0x01
ZW_LIB_CONTROLLER         = 0x02
ZW_LIB_SLAVE_ENHANCED     = 0x03
ZW_LIB_SLAVE              = 0x04
ZW_LIB_INSTALLER          = 0x05
ZW_LIB_SLAVE_ROUTING      = 0x06
ZW_LIB_CONTROLLER_BRIDGE  = 0x07
ZW_LIB_DUT                = 0x08
ZW_LIB_AVREMOTE           = 0x0A
ZW_LIB_AVDEVICE           = 0x0B
libType = {
ZW_LIB_CONTROLLER_STATIC  : "Static Controller",
ZW_LIB_CONTROLLER         : "Controller",
ZW_LIB_SLAVE_ENHANCED     : "Slave Enhanced",
ZW_LIB_SLAVE              : "Slave",
ZW_LIB_INSTALLER          : "Installer",
ZW_LIB_SLAVE_ROUTING      : "Slave Routing",
ZW_LIB_CONTROLLER_BRIDGE  : "Bridge Controller",
ZW_LIB_DUT                : "DUT",
ZW_LIB_AVREMOTE           : "AVREMOTE",
ZW_LIB_AVDEVICE           : "AVDEVICE" }

ADD_NODE_ANY       = 0x01
ADD_NODE_CONTROLLER= 0x02
ADD_NODE_SLAVE     = 0x03
ADD_NODE_EXISTING  = 0x04
ADD_NODE_STOP      = 0x05
ADD_NODE_SMART_START = 0x09
TRANSMIT_COMPLETE_OK      =0x00
TRANSMIT_COMPLETE_NO_ACK  =0x01 
TRANSMIT_COMPLETE_FAIL    =0x02 
TRANSMIT_ROUTING_NOT_IDLE =0x03
TRANSMIT_OPTION_ACK = 0x01
TRANSMIT_OPTION_AUTO_ROUTE = 0x04
TRANSMIT_OPTION_EXPLORE = 0x20
ADD_NODE_STATUS_LEARN_READY          = 1
ADD_NODE_STATUS_NODE_FOUND           = 2
ADD_NODE_STATUS_ADDING_SLAVE         = 3
ADD_NODE_STATUS_ADDING_CONTROLLER    = 4
ADD_NODE_STATUS_PROTOCOL_DONE        = 5
ADD_NODE_STATUS_DONE                 = 6
ADD_NODE_STATUS_FAILED               = 7
ADD_NODE_STATUS_NOT_PRIMARY          = 0x23

# SerialAPI defines
SOF = 0x01
ACK = 0x06
NAK = 0x15
CAN = 0x18
REQUEST = 0x00
RESPONSE = 0x01
# Most Z-Wave commands want the autoroute option on to be sure it gets thru. Don't use Explorer though as that causes unnecessary delays.
TXOPTS = TRANSMIT_OPTION_AUTO_ROUTE | TRANSMIT_OPTION_ACK

# See INS13954-7 section 7 Application Note: Z-Wave Protocol Versions on page 433
ZWAVE_VER_DECODE = {# Z-Wave version to SDK decoder: https://www.silabs.com/products/development-tools/software/z-wave/embedded-sdk/previous-versions
        "6.01" : "SDK 6.81.00 09/2017",
        "5.03" : "SDK 6.71.03        ",
        "5.02" : "SDK 6.71.02 07/2017",
        "4.61" : "SDK 6.71.01 03/2017",
        "4.60" : "SDK 6.71.00 01/2017",
        "4.62" : "SDK 6.61.01 04/2017",  # This is the INTERMEDIATE version?
        "4.33" : "SDK 6.61.00 04/2016",
        "4.54" : "SDK 6.51.10 02/2017",
        "4.38" : "SDK 6.51.09 07/2016",
        "4.34" : "SDK 6.51.08 05/2016",
        "4.24" : "SDK 6.51.07 02/2016",
        "4.05" : "SDK 6.51.06 06/2015 or SDK 6.51.05 12/2014",
        "4.01" : "SDK 6.51.04 05/2014",
        "3.99" : "SDK 6.51.03 07/2014",
        "3.95" : "SDK 6.51.02 05/2014",
        "3.92" : "SDK 6.51.01 04/2014",
        "3.83" : "SDK 6.51.00 12/2013",
        "3.79" : "SDK 6.50.01        ",
        "3.71" : "SDK 6.50.00        ",
        "3.35" : "SDK 6.10.00        ",
        "3.41" : "SDK 6.02.00        ",
        "3.37" : "SDK 6.01.03        "
        }

class TestNVM():
    ''' Open the serial port to the Z-Wave SerialAPI controller '''
    def __init__(self):         # parse the command line arguments and open the serial port
        self.COMPORT=COMPORT
        self.filename=""
        if len(sys.argv)==1:     # No arguments then try the default serial port
            pass
        elif len(sys.argv)==2: 
            self.COMPORT=sys.argv[1]
        else:
            self.usage()
            sys.exit()
        if DEBUG>3: print "COM Port set to {}".format(self.COMPORT)
        try:
            self.UZB= serial.Serial(self.COMPORT,'115200',timeout=2)
        except serial.SerialException:
            print "Unable to open serial port {}".format(self.COMPORT)
            exit()

    def checksum(self,pkt):
        ''' compute the Z-Wave SerialAPI checksum at the end of each frame'''
        s=0xff
        for c in pkt:
            s ^= ord(c)
        return s

    def GetRxChar( self, timeout=100):
        ''' Get a character from the UART or timeout in 100ms'''
        while timeout >0 and not self.UZB.inWaiting():
            time.sleep(0.001)
            timeout -=1
        if timeout>0:
            retval= self.UZB.read()
        else:
            retval= None
        return retval

    def GetZWave( self, timeout=5000):
        ''' Receive a frame from the UART and return the binary string or timeout in TIMEOUT ms and return None'''
        pkt=""
        c=self.GetRxChar(timeout)
        if c == None:
            if DEBUG>1: print "GetZWave Timeout!"
            return None
        while ord(c)!=SOF:   # get synced on the SOF
            if DEBUG>5: print "SerialAPI Not SYNCed {:02X}".format(ord(c))
            c=self.GetRxChar(timeout)
        if ord(c)!=SOF:
            return None
        length=ord(self.GetRxChar())
        for i in range(length):
            c=self.GetRxChar()
            pkt += c
        checksum= self.checksum(pkt)
        checksum ^= length  # checksum includes the length
        if checksum!=0:
            if DEBUG>1: print "GetZWave checksum failed {:02x}".format(checksum)
        self.UZB.write(pack("B",ACK))  # ACK the returned frame - we don't send anything else even if the checksum is wrong
        return pkt[1:-1] # strip off the type and checksum
 
 
    def Send2ZWave( self, SerialAPIcmd, returnStringFlag=False):
        ''' Send the command via the SerialAPI to the Z-Wave chip and optionally wait for a response.
            If ReturnStringFlag=True then returns a binary string of the SerialAPI frame response
            else returns None
            Waits for the ACK/NAK/CAN for the SerialAPI and strips that off. 
            Removes all SerialAPI data from the UART before sending and ACKs to clear any retries.
        '''
        if self.UZB.inWaiting(): 
            self.UZB.write(pack("B",ACK))  # ACK just to clear out any retries
            if DEBUG>5: print "Dumping ",
        while self.UZB.inWaiting(): # purge UART RX to remove any old frames we don't want
            c=self.UZB.read()
            if DEBUG>5: print "{:02X}".format(ord(c)),
        frame = pack("2B", len(SerialAPIcmd)+2, REQUEST) + SerialAPIcmd # add LEN and REQ bytes which are part of the checksum
        chksum= self.checksum(frame)
        pkt = (pack("B",SOF) + frame + pack("B",chksum)) # add SOF to front and CHECKSUM to end
        if DEBUG>9: print "Sending ", 
        for c in pkt:
            if DEBUG>9: print "{:02X},".format(ord(c)),
            self.UZB.write(c)  # send the command
        if DEBUG>9: print " "
        # should always get an ACK/NAK/CAN so wait for it here
        c=self.GetRxChar(500) # wait up to half second for the ACK
        if c==None:
            if DEBUG>1: print "Error - no ACK or NAK"
            # try resending one time
            self.UZB.write(pack("B",ACK))  # ACK just to clear out any retries
            for c in pkt:
                self.UZB.write(c)  # resend the command
            c=self.GetRxChar(1500) # wait for the ACK
            if c==None:
                if DEBUG>1: print "Error - No Ack/Nak on 2nd try"
        elif ord(c)!=ACK:
            if DEBUG>1: print "Error - not ACKed = 0x{:02X}".format(ord(c))
            self.UZB.write(pack("B",ACK))   # send an ACK to stop any retries
            time.sleep(1)
            while self.UZB.inWaiting(): # purge UART RX to remove any old frames we don't want
                c=self.UZB.read()
            for c in pkt:
                self.UZB.write(c) # resend the command
            c=self.GetRxChar(500)
            if c==None:
                if DEBUG>1: print "ERROR - No Ack/Nak on 2nd try"
        response=None
        if returnStringFlag:    # wait for the returning frame for up to 5 seconds
            response=self.GetZWave()    
        return response
            

    def RemoveLifeline( self, NodeID):
        ''' Remove the Lifeline Association from the NodeID (integer). 
            Helps eliminate interfering traffic being sent to the controller during the middle of range testing.
        '''
        pkt=self.Send2ZWave(pack("!9B",FUNC_ID_ZW_SEND_DATA, NodeID, 4, 0x85, 0x04, 0x01, 0x01, TXOPTS, 78),True)
        pkt=self.GetZWave(10*1000)
        if pkt==None or ord(pkt[2])!=0:
            if DEBUG>1: print "Failed to remove Lifeline"
        else:
            print "Lifeline removed"
        if DEBUG>10: 
            for i in range(len(pkt)): 
                print "{:02X}".format(ord(pkt[i])),

    def PrintVersion(self):
        pkt=self.Send2ZWave(pack("B",FUNC_ID_SERIAL_API_GET_CAPABILITIES),True)
        if pkt==None: 
            print "Failed to communicate with Z-Wave Chip"
            return
        (ver, rev, man_id, man_prod_type, man_prod_type_id, supported) = unpack("!2B3H32s", pkt[1:])
        print "SerialAPI Ver={0}.{1}".format(ver,rev)   # SerialAPI version is different than the SDK version
        print "Mfg={:04X}".format(man_id)
        print "ProdID/TypeID={0:02X}:{1:02X}".format(man_prod_type,man_prod_type_id)
        pkt=self.Send2ZWave(pack("B",FUNC_ID_ZW_GET_VERSION),True)  # SDK version
        (VerStr, lib) = unpack("!12sB", pkt[1:])
        print "{} {}".format(VerStr,ZWAVE_VER_DECODE[VerStr[-5:-1]])
        print "Library={} {}".format(lib,libType[lib])
        pkt=self.Send2ZWave(pack("B",FUNC_ID_SERIAL_API_GET_INIT_DATA),True)
        if pkt!=None and len(pkt)>33:
            print "NodeIDs=",
            for k in [4,28+4]:
                j=ord(pkt[k]) # this is the first 8 nodes
                for i in range(0,8):
                    if (1<<i)&j:
                        print "{},".format(i+1+ 8*(k-4)),
            print " "
        pkt=self.Send2ZWave(pack("BB",FUNC_ID_ZW_FIRMWARE_UPDATE_NVM,FIRMWARE_UPDATE_NVM_INIT),True)
        (cmd, FirmwareUpdateSupported) = unpack("!BB", pkt[1:])

    def usage(self):
        print ""
        print "Usage: python TestNVM.py [COMxx]"
        print " COMxx is the Z-Wave UART interface - typically COMxx for windows and /dev/ttyXXXX for Linux"
        print "Version {}".format(VERSION)
        print "Commands:"
        print "p=Probe the NVM and report MFG and size"
        print "h=Print the HomeID and NodeID"
        print "d=dump the NVM contents to the file NVM.hex"
        print "f [dd] = Fill the entire NVM with the value dd (0 by default)"
        print "s=Soft Reset the Z-Wave chip (reboot)"
        print "S=Factory Reset the Z-Wave chip - NVM is initialized, Z-Wave network deleted, ZW_SetDefault()"
        print "r [aaaaaa]=Read 256 bytes starting at address aaaaaa in hex"
        print "v=Print SDK Version of the controller and other info"
        print "+=Include a node"
        print "-=Exclude a node"
        print "x=Exit program"
        print ""

if __name__ == "__main__":
    ''' Start the app if this file is executed'''
    try:
        self=TestNVM()
    except:
        print 'error - unable to start program'
        self.usage()
        exit()

    # fetch and display various attributes of the Controller
    self.PrintVersion()

    while True:
        line = raw_input('>')
        if len(line)<1: 
            line=' '
        if line[0] == 'X' or line[0] == 'x' or line[0] == 'q':  ############## exit
            break
        elif line[0] == 'p':                          ############## probe - print out the NVM MFG and size
            pkt=self.Send2ZWave(pack("B",FUNC_ID_NVM_GET_MFG_ID),True) 
            print "{:02X} {:02X} {:02X} {:02X} {:02X}".format(ord(pkt[0]),ord(pkt[1]),ord(pkt[2]),ord(pkt[3]),ord(pkt[4])),
            print " Mfg=",
            if ord(pkt[2])==0x20: 
                print "Micron",
                size=ord(pkt[4])
                if 0x0e<size<0x18:
                    size2=16<<(size-0x0e) 
                    print "Size={}KB".format(size2)
            elif ord(pkt[2])==0x1f: 
                print "Adesto",
                size=ord(pkt[3])
                if (size&0x1F)==0x03:   # TODO decode some of the other sizes
                    print "Size=2MBit (256KB)"
                else:
                    print "Size={:02X}".format(ord(pkt3))
            else: print "{:02X}".format(ord(pkt[3]))

        elif line[0] == 'h':                          ############## Get the HomeID NodeID
            pkt=self.Send2ZWave(pack("B",FUNC_ID_GET_HOME_ID),True) 
            HomeID = int(ord(pkt[1]))
            HomeID=HomeID<<8
            HomeID += ord(pkt[2])
            HomeID = HomeID<<8 
            HomeID += ord(pkt[3])
            HomeID = HomeID<<8
            HomeID += ord(pkt[4])
            NodeID=ord(pkt[5])
            print "HomeID={:X} NodeID={}".format(HomeID, NodeID)

        elif line[0] == 's':                          ############## soft reset
            pkt=self.Send2ZWave(pack("B", FUNC_ID_SERIAL_API_SOFT_RESET),False) 
            time.sleep(1.5)         # wait for reset to complete
            pkt=self.GetZWave()          # clear the Start command
            print "Reset Complete"

        elif line[0] == 'S':                          ############## SET_DEFAULT - factory reset
            pkt=self.Send2ZWave(pack("B", FUNC_ID_ZW_SET_DEFAULT),False) 
            time.sleep(1.5)         # wait for reset to complete
            pkt=self.Send2ZWave(pack("B", FUNC_ID_SERIAL_API_SOFT_RESET),False) 
            pkt=self.GetZWave()          # clear the Start command
            print "Factory Reset Complete"

        elif line[0] == 'r':                          ############## Read 256 bytes at page xxx
            linesplit=line.split()
            if len(linesplit)>1:
                addr=int(linesplit[1],16)
            else:
                addr=0
            for i in range(0,16):
                pkt=self.Send2ZWave(pack("BBBBBB",FUNC_ID_NVM_EXT_READ_BUF,(addr>>16)&0xFF,(addr>>8)&0xFF,(addr>>0)&0xFF ,0,16),True) 
                print "\r\n0x{:06X}=".format(addr),
                addr+=16
                for j in range(1,17):
                    print "{:02X}".format(ord(pkt[j])),
            print " "

        elif line[0] == 'w':                          ############## Write a single byte to address aaaaaa
            linesplit=line.split()
            if len(linesplit)>2:
                addr=int(linesplit[1],16)
                data=int(linesplit[2],16)
            else:
                print "w aaaaaa dd - write dd to address aaaaaa. Values are in hex"
            pkt=self.Send2ZWave(pack("B3BB",FUNC_ID_NVM_EXT_WRITE_BYTE,(addr>>16)&0xFF,(addr>>8)&0xFF,(addr>>0)&0xFF ,data),True) 
            if pkt[1] != 0:
                print "Write of {:X} to {:X} complete".format(data,addr)
            else:
                print "Write failed"

        elif line[0] == 'f':                          ############## fill the entire NVM with the value included 
            linesplit=line.split()
            if len(linesplit)>1:
                val=int(linesplit[1],16)
            else:
                val=0xFF
            print "Writing {:02X} to entire NVM - Please wait...".format(val)
            addr=0x0
            for i in range(0,256*1024/16):
                pkt=self.Send2ZWave(pack("B3B2B16B",FUNC_ID_NVM_EXT_WRITE_BUF,(addr>>16)&0xFF,(addr>>8)&0xFF,(addr>>0)&0xFF,0, 16,
                    val,val,val,val,val,val,val,val,
                    val,val,val,val,val,val,val,val),True) 
                addr+=16
                if DEBUG>9: print "{:X}={:x}".format(addr,ord(pkt[1]))

        elif line[0] == 'd':                          ############## dump the entire NVM to a filed called NVM.hex (assumes a 2mbit NVM)
            # TODO could try to figure out the size here and then just dump the actual size
            try:
                f=open("NVM.hex","w")
            except:
                print "unable to open NVM.hex"
                continue
            print "Please wait..."
            addr=0
            for i in range(0,256*1024/16):
                pkt=self.Send2ZWave(pack("BBBBBB",FUNC_ID_NVM_EXT_READ_BUF,(addr>>16)&0xFF,(addr>>8)&0xFF,(addr>>0)&0xFF ,0,16),True) 
                f.write("\r\n0x{:06X}=".format(addr))
                addr+=16
                for j in range(1,17):
                    f.write("{:02X}".format(ord(pkt[j])))
            f.close()
            print "Dump completed"

        elif line[0]=='v':                          ########################## Print the version of the controller
            self.PrintVersion()

        elif line[0]=='+':                          ########################## Inclusion mode
            pkt=self.Send2ZWave(pack("3B",FUNC_ID_ZW_ADD_NODE_TO_NETWORK, ADD_NODE_ANY, 0xaa),True)
            (cmd,FuncID,bStatus)= unpack("BBB",pkt[:3]) # first status should be 01=learn_ready
            if (bStatus==ADD_NODE_STATUS_LEARN_READY):
                print "Press Button on Device"
            while not (bStatus==ADD_NODE_STATUS_FAILED or bStatus==ADD_NODE_STATUS_DONE): # will get several callbacks until DONE with info along the way
                pkt=self.GetZWave(50*1000)      # wait for up to 50seconds for a response
                (cmd,FuncID,bStatus)= unpack("BBB",pkt[:3])
                #print "Adding Status={}".format(bStatus)
                if bStatus==ADD_NODE_STATUS_PROTOCOL_DONE: # required to send it again to get to DONE
                    pkt=self.Send2ZWave(pack("3B",FUNC_ID_ZW_ADD_NODE_TO_NETWORK, ADD_NODE_STOP, 0xaa),False)
                if (bStatus==ADD_NODE_STATUS_ADDING_SLAVE or bStatus==ADD_NODE_STATUS_ADDING_CONTROLLER):
                    stuff,=unpack("B",pkt[3])
                    print "Added Node {}".format(stuff)
            if bStatus==ADD_NODE_STATUS_FAILED:
                print "Add node failed"
            self.Send2ZWave(pack("BB",FUNC_ID_ZW_ADD_NODE_TO_NETWORK, ADD_NODE_STOP),False) # cleanup

        elif line[0]=='-':                          ############################### Exclusion mode
            pkt=self.Send2ZWave(pack("3B",FUNC_ID_ZW_REMOVE_NODE_FROM_NETWORK, REMOVE_NODE_ANY, 0xdd),True) # go into exclude mode but wait up to 60 seconds for a response
            (cmd,FuncID,bStatus)= unpack("BBB",pkt[:3]) # first status should be 01=learn_ready
            if (bStatus==REMOVE_NODE_STATUS_LEARN_READY):
                print "Press Button on Device"
            while not (bStatus==REMOVE_NODE_STATUS_FAILED or bStatus==REMOVE_NODE_STATUS_DONE): # will get several callbacks until DONE with info along the way
                pkt=self.GetZWave(50*1000)      # wait for up to 50seconds for a response
                (cmd,FuncID,bStatus)= unpack("BBB",pkt[:3])
                if (bStatus==REMOVE_NODE_STATUS_REMOVING_SLAVE or bStatus==REMOVE_NODE_STATUS_REMOVING_CONTROLLER):
                    stuff,=unpack("B",pkt[3])
                    print "Excluded Node {}".format(stuff)
            self.Send2ZWave(pack("BB",FUNC_ID_ZW_REMOVE_NODE_FROM_NETWORK, REMOVE_NODE_STOP),False) # cleanup
        else:
            self.usage()
    exit()
