# ID # - 620068361

import sys
import getopt
import time

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.sackMode = sackMode
        self.debug = debug
        self.max_pac_data = 1400
        self.seqno = 0
        self.timeout = 0.5
        self.window = 7
        self.last_ack_pac = None
        self.last_ack_count = 0
        self.unacked_pac = {}
        self.packet_data = []
        self.no_packets = 0
        self.timer = None
        self.fin_seq = None
        

    """Validate ack messages recieved
       Return true if ack is valid, returns false otherwise"""
    def validate_ack(self, response):
        if response:
            temp = self.split_packet(response)
            msg_type, ack_no = temp[0],temp[1]
            if self.sackMode:
                ack_no, _ = ack_no.split(";")
            if msg_type == "ack" or msg_type == "sack":
                try:
                    ack_no = int(ack_no)
                    return Checksum.validate_checksum(response)
                except ValueError:
                    pass                              
        return False
    
    """ Send syn packet and wait for acknowledgement
        Return true if a connection is initiated, returns false otherwise"""
    def handshake(self, start_packet):
        # connection start time
        self.timer = time.time()
        self.send(start_packet)
        self.unacked_pac[self.seqno] = start_packet      
        while self.seqno == 0:            
            response = self.receive(0.5)
            self.handle_ack(response)
            
            if self.validate_ack(response):
                self.seqno += 1
            elif time.time() > self.timer + self.timeout:
                self.retransmit(0)
        return True
        
    """Split data to be sent into chunks
       Returns list whth chunks of data"""
    def make_data_chunks(self):
        data = []
        msg = " "
        while msg != "":
            msg = self.infile.read(self.max_pac_data)
            data.append(msg)
        return data
    
    
    def handle_ack(self, response):
        if self.validate_ack(response):
            msg_type, ack_no, _, _ = self.split_packet(response)
            if self.sackMode:
                ack_no, sack_nos = ack_no.split(";")
                if len(sack_nos):
                    sack_nos = sack_nos.split(",")                    
                    for sn in map(int, sack_nos):
                        if sn in self.unacked_pac.keys():
                            del self.unacked_pac[sn]           
            
            ack_no = int(ack_no)        
            if ack_no == self.last_ack_pac:
                self.last_ack_count += 1
                if self.last_ack_count == 3:
                    if self.sackMode:
                        for seq in self.unacked_pac.keys():
                            if seq not in sack_nos:
                                self.retransmit(seq)
                    else:
                        self.retransmit(ack_no)
                return
            else:
                self.last_ack_pac = ack_no
                self.last_ack_count = 1
                    
            seq_no = ack_no - 1
            for s in self.unacked_pac.keys():
                if s <= seq_no:
                    del self.unacked_pac[s]
                    
            if seq_no == self.fin_seq:
                exit()
        
    """ Resend packets """
    def retransmit(self,seqno):
        packet = self.unacked_pac[seqno]
        self.timer = time.time()
        self.send(packet)
    
    
    # Main sending loop.
    def start(self):
      packet = self.make_packet("syn", self.seqno, "")    
      if self.handshake(packet):          
          self.packet_data = self.make_data_chunks()[:-1]
          self.no_packets = len(self.packet_data)
          self.fin_seq = self.no_packets
          p = 0
          while True:
            if len(self.unacked_pac) < self.window and p < self.fin_seq:
                if p == self.no_packets - 1:
                    packet = self.make_packet("fin", self.seqno, self.packet_data[p])
                else:
                    packet = self.make_packet("dat", self.seqno, self.packet_data[p])
                
                self.timer = time.time()
                self.send(packet)
                self.unacked_pac[self.seqno] = packet
                self.seqno += 1
                p += 1 
            
            response = self.receive(0.5)
            if time.time() > self.timer + self.timeout:
                self.retransmit(self.last_ack_pac)
            else:
                self.handle_ack(response)
                  
                 
        
'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest,port,filename,debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
