import client
import bencode
import hashlib
import urllib
from urllib.request import urlopen
import logging

class Tracker(object):
    def __init__(self, client_):
        self.client = client_
        self.uploaded = 0 # currently not implemented
        self.downloaded = 0 # currently not implemented
    def getRequest(self, port=6881):
        logging.info('sending tracker request')    
        base_url = self.client.metainfo.get(b'announce')
        info = self.client.metainfo.get(b'info')
        bcoded_info = bencode.Bencode.encodeDict(info)
        info_hash = hashlib.sha1(bcoded_info).digest()
        peer_id = self.client.get_peer_id()
        uploaded = self.uploaded
        downloaded = self.downloaded
        # single file mode
        if b"length" in info:
            left = info[b"length"]
        # multiple files mode
        elif b"files" in info:
            files = info[b"files"]
            left = 0
            for each_file in files:
                left += each_file[b"length"]
        else:
            raise ValueError("invalid info dictionary")
        event = "started"
        parameters = { 'info_hash': info_hash, 'peer_id': peer_id,\
                    'port': str(port), 'uploaded': str(uploaded),\
                    'downloaded': str(downloaded), 'left': str(left),\
                    'event': event, 'compact': 1}
        request_url = base_url.decode('utf8') + '?' + urllib.parse.urlencode(parameters)
        response = bencode.Bencode().decode(urlopen(request_url).read())
        logging.info('received response from tracker')    
        return response
        
