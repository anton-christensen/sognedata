from typing import Dict
import requests
import xml.etree.ElementTree as ET
import json
from os import path
from functools import reduce

# local libs
import common

def _makePopulation():
    def work():
        reqData = {
            "table": "km5",
            "format": "CSV",
            "variables": [
                {
                    "code": "sogn",
                    "values": [
                        "*"
                    ]
                }
            ]
        }
        text = requests.post("https://api.statbank.dk/v1/data", json = reqData).text
        return text

    population_csv = common.cache("api.statbank.dk - km5 data 2021", work) # todo: invalidate cache each year

    lines = population_csv.splitlines()[1:]
    population = dict(map(lambda l: (int(l[0:4]), int(l.split(';')[2])), lines))
    return population


def _downloadXML(url):
    text = common.cache(url, lambda: requests.get(url, allow_redirects=True).text)
    return ET.fromstring(text)

def _parseLevel(url, childKey = None):
    xml = _downloadXML(url)
    namespace = {'': xml.tag.split('}')[0][1:]}
    doc = dict()

    for part in xml.findall('.//Placemark', namespace):
        id = part.find('./name', namespace).text
        description = part.find('./description', namespace).text.split(';')[0]
        
        # convert polygon string to pairs of (lat,lon) floats
        polygons = [x for x in [list(map(
            lambda p_str: (float(p_str.split(',')[1]), float(p_str.split(',')[0])),
            # lambda p_str: p_str.split(','),
            [ p for p in ' '.join(polygon.text.splitlines()).split(' ') if len(p) > 1 ]
        )) for polygon in part.findall('.//coordinates', namespace)] if len(x)]

        # level 2s tend to have multiple coordinate tags in a single placemark 
        # whereas the others have multiple placemarks with single coordinates in each

        if(id not in doc.keys()):
            doc[id] = {'id': id, 'name': description, 'polygons': polygons}
            if childKey:
                doc[id][childKey] = dict()
        else:
            # print(id, description, len(polygons))

            doc[id]['polygons'] = doc[id]['polygons'] + polygons
    
    # calculate boundingbox of polygons
    for part in doc.values():
        points = [item for sublist in part['polygons'] for item in sublist]
        (lat_0,lon_0) = reduce(lambda p1, p2: (min(p1[0],p2[0]), min(p1[1],p2[1])), points, points[0])
        (lat_1,lon_1) = reduce(lambda p1, p2: (max(p1[0],p2[0]), max(p1[1],p2[1])), points, points[0])
        bb = {'lon_0': lon_0, 'lon_1': lon_1, 'lat_0': lat_0, 'lat_1': lat_1}
        doc[part['id']]['boundingbox'] = bb

    return doc


def buildDataset():
    population = _makePopulation()

    document = dict()
    # Download stifter
    document['stifter'] = _parseLevel(
        'https://sogn.dk/maps/kml/stifter_kml.php',
        'provstier'
        )

    # for each stift
    for stift in document['stifter'].values():
        # Download provstier
        document['stifter'][stift['id']]['provstier'] = _parseLevel(
            'https://sogn.dk/maps/kml/provstier_kml.php?stiftId='+stift['id'], 
            'sogne'
            )

    for stift in document['stifter'].values():
        stiftPopulation = 0
        # for hvert provsti
        for provsti in stift['provstier'].values():
            # Download sogne
            document['stifter'][stift['id']]['provstier'][provsti['id']]['sogne'] = _parseLevel(
                'https://sogn.dk/maps/kml/sogne_kml.php?provstiID='+provsti['id'] )


    # calculate population
    totalPopulation = 0
    for stift in document['stifter'].values():
        stiftPopulation = 0
        for provsti in stift['provstier'].values():
            provstiPopulation = 0
            for sogn in provsti['sogne'].values():
                document['stifter'][stift['id']]['provstier'][provsti['id']]['sogne'][sogn['id']]['population'] = population[int(sogn['id'])]
                provstiPopulation += population[int(sogn['id'])]
            document['stifter'][stift['id']]['provstier'][provsti['id']]['population'] = provstiPopulation
            stiftPopulation += provstiPopulation
        document['stifter'][stift['id']]['population'] = stiftPopulation
        totalPopulation += stiftPopulation
    document['population'] = totalPopulation

    text_file = open("./data/dataset.json", "w")
    text_file.write(json.dumps(document))
    text_file.close()
    return document

def getDataset():
    document = None
    if path.isfile("./data/dataset.json"):
        file = open("./data/dataset.json")
        document = file.read()
        file.close()
    else:
        document = json.dumps(buildDataset())
    return document

if __name__ == "__main__":
    buildDataset()