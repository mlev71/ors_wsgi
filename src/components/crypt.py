##################################
#               AES CRYPTO       #
##################################

from Crypto.Cipher import AES
from Crypto import Random
import base64
import hashlib

block_size = 32
GLOBAL_KEY = hashlib.sha256("hellothisismycipherkey".encode()).digest()
GLOBAL_IV = Random.new().read(AES.block_size)



def encryptUrl(raw, key=GLOBAL_KEY, iv=GLOBAL_IV):
    temp_cipher = AES.new(key, AES.MODE_CBC, iv)
    raw = pad(raw)
    return base64.b64encode(iv + temp_cipher.encrypt(raw)).decode()

def decryptUrl(enc, key=GLOBAL_KEY, iv=GLOBAL_IV):
    temp_cipher = AES.new(key, AES.MODE_CBC, iv)
    enc = base64.b64decode(enc)
    iv = enc[:AES.block_size]
    return unpad(temp_cipher.decrypt(enc[AES.block_size:])).decode('utf-8')


def pad(s):
    return s + (32 - len(s) % 32) * chr(32 - len(s) % 32)

def unpad(s):
    return s[:-ord(s[len(s)-1:])]

