from os import path
import sys
import json
from functools import reduce
import matplotlib.path as mplpath

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def flatten(listOfLists):
    return [item for sublist in listOfLists for item in sublist]

def combineBBs(bbs):
    return reduce(lambda bb1, bb2: {
        'lon_0': min(bb1['lon_0'], bb2['lon_0']), 
        'lon_1': max(bb1['lon_1'], bb2['lon_1']), 
        'lat_0': min(bb1['lat_0'], bb2['lat_0']), 
        'lat_1': max(bb1['lat_1'], bb2['lat_1'])
        }, bbs, bbs[0])
    

def bbToxywh(bb):
    return {'x': bb['lon_0'], 'y': bb['lat_0'], 'w': bb['lon_1'] - bb['lon_0'], 'h': bb['lat_1'] - bb['lat_0']}

def pointBBintersection(lat, lon, bb):
    return lat >= bb['lat_0'] and lat <= bb['lat_1'] and lon >= bb['lon_0'] and lon <= bb['lon_1']
    
def pointPolygonIntersection(p, polygon):
    path = mplpath.Path(polygon)
    res = path.contains_point(p)
    return res


def findSognByPoint(lat,lon, document):
    stifter = [x for x in document['stifter'].values() if pointBBintersection(lat,lon, x['boundingbox'])]
    provstier = flatten([[x for x in y['provstier'].values() if pointBBintersection(lat,lon, x['boundingbox'])] for y in stifter])
    sogne = flatten([[x for x in y['sogne'].values() if pointBBintersection(lat,lon, x['boundingbox'])] for y in provstier])

    return [s for s in sogne if len([1 for p in s['polygons'] if pointPolygonIntersection((lat,lon), p)]) > 0]


if __name__ == '__main__':
    text_file = open("Stifter.txt", "r")
    document = json.loads(text_file.read())
    text_file.close()

    (lat,lon) = (57.17536551680044, 9.701480184505503)
    def idnamepopulation(o):
        return {'id': o['id'], 'title': o['name'], 'population': o['population']}
    print([idnamepopulation(x) for x in findSognByPoint(lat,lon,document)])




