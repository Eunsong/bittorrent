import metainfo
import tracker

class Client(object):
    def __init__(self, metainfo_):
        self.peer_id = self._gen_peer_id()
        self.metainfo = metainfo_
        self.tracker = tracker.Tracker(self)
        self.trackerResponse = self.request_tracker()
        # list of {'ip': ip, 'port': port} peer dictionaries
        self.peers = self.get_peers()
    def update_peers(self):
        self.peers = self.get_peers()
    def get_peers(self):
        peers = []
        arg = self.trackerResponse['peers']
        if ( type(arg) is str): # if binary model
            assert (len(arg) % 6 == 0)
            num_peers = len(arg)/6
            for n in range(num_peers):
                ip = '.'.join([str(ord(c)) for c in arg[n*6: n*6 + 4]])
                port = str(ord(arg[n*6 + 4])) + str(ord(arg[n*6 + 5]))
                peers.append({'ip': ip, 'port': port})
        else: # dictionary model is not implemented yet
            raise ValueError("unsupported tracker response format")
        return peers
    def request_tracker(self):
        return self.tracker.getRequest()
    def _gen_peer_id(self):
        import struct
        import time
        myid = "-" + "MY" + "0001" + str(time.time())
        return struct.pack("20s", myid) 
    def get_peer_id(self):
        return self.peer_id
        