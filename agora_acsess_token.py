import hmac
import hashlib
import base64
import time
from collections import OrderedDict

class AccessToken:
    class Privileges:
        kJoinChannel = 1
        kPublishAudioStream = 2
        kPublishVideoStream = 3
        kPublishDataStream = 4

    def __init__(self, appID, appCertificate, channelName, uid):
        self.appID = appID
        self.appCertificate = appCertificate
        self.channelName = channelName
        self.uid = uid
        self.privileges = OrderedDict()
        self.salt = int(time.time())
        self.expiredTs = 0

    def add_privilege(self, privilege, expireTimestamp):
        self.privileges[privilege] = expireTimestamp
        if expireTimestamp > self.expiredTs:
            self.expiredTs = expireTimestamp

    def build(self):
        sign = self.generate_signature()
        content = self._pack_content()
        return self._pack(sign, content)

    def generate_signature(self):
        key = self._hmac_sha256(self.appCertificate, self._pack_uint32(self.salt))
        message = self._pack_string(self.appID) + \
                 self._pack_string(self.channelName) + \
                 self._pack_string(str(self.uid)) + \
                 self._pack_uint32(self.salt) + \
                 self._pack_uint32(self.expiredTs) + \
                 self._pack_uint16(len(self.privileges))
        
        for key, value in self.privileges.items():
            message += self._pack_uint16(key) + self._pack_uint32(value)
        
        return self._hmac_sha256(key, message)

    def _pack_content(self):
        return self._pack_string(self.appID) + \
               self._pack_string(self.channelName) + \
               self._pack_string(str(self.uid)) + \
               self._pack_uint32(self.salt) + \
               self._pack_uint32(self.expiredTs) + \
               self._pack_uint16(len(self.privileges)) + \
               b''.join([self._pack_uint16(k) + self._pack_uint32(v) for k, v in self.privileges.items()])

    def _pack(self, signature, content):
        return base64.b64encode(
            self._pack_uint16(len(signature)) + 
            signature + 
            content
        ).decode('utf-8')

    def _hmac_sha256(self, key, message):
        return hmac.new(key, message, hashlib.sha256).digest()

    def _pack_string(self, value):
        return self._pack_uint16(len(value)) + value.encode('utf-8')

    def _pack_uint16(self, value):
        return value.to_bytes(2, byteorder='little')

    def _pack_uint32(self, value):
        return value.to_bytes(4, byteorder='little')
