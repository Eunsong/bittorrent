import client
import bencode
import hashlib
import urllib, urllib2
import metainfo

class Tracker(object):
    def __init__(self, client_):
        self.client = client_
        self.uploaded = 0 # currently not implemented
        self.downloaded = 0 # currently not implemented
    def getRequest(self, port=6881):
        base_url = self.client.metainfo.get("announce")
        info = self.client.metainfo.get("info")
        bcoded_info = bencode.Bencode.encodeDict(info)
        info_hash = hashlib.sha1(bcoded_info).digest()
        peer_id = self.client.get_peer_id()
        uploaded = self.uploaded
        downloaded = self.downloaded
        # single file mode
        if "length" in info:
            left = info["length"]
        # multiple files mode
        elif "files" in info:
            files = info["files"]
            left = 0
            for each_file in files:
                left += each_file["length"]
        else:
            raise ValueError("invalid info dictionary")
        event = "started"
        parameters = { 'info_hash': info_hash, 'peer_id': str(peer_id),\
                    'port': str(port), 'uploaded': str(uploaded),\
                    'downloaded': str(downloaded), 'left': str(left),\
                    'event': event}
        request_url = base_url + '?' + urllib.urlencode(parameters)
        response = bencode.Bencode().decode(urllib2.urlopen(request_url).read())
        return response
        """     
        print urllib2.urlopen(request_url).read()
        print "hashed info : "
        print info_hash
        print ("url = " + request_url)
        print peer_id
        print port
        print left
        """