import bencode 

class Metainfo(object):
    def __init__(self, str_):
        self.info_dic = bencode.Bencode(str_).decode()
        assert type(self.info_dic) is dict
    def getDict(self):
        return self.info_dic
    def get(self, key):
        return self.info_dic[key]
