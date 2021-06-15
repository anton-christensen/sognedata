import hashlib
from os import path, mkdir

if not path.exists('./data/cache'):
    mkdir('./data')
    mkdir('./data/cache')

def cache(key, func):
    cachedPath = "./data/cache/"+str(hashlib.md5(key.encode('utf-8')).hexdigest())
    if(path.exists(cachedPath)):
        fh = open(cachedPath, "r")
        text = fh.read()
        fh.close()
        return text
    else:
        text = func()
        fh = open(cachedPath, "w")
        fh.write(text)
        fh.close()
        return text
