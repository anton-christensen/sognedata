from typing import Dict
import requests
import xml.etree.ElementTree as ET
import json
from os import path
from functools import reduce

# local libs
import common
import database

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

def _parseLevel(conn, level = 1, parent_id = None):
    url = database.getDataURLByLevel(conn, level)
    if url == None:
        return
    
    xml = _downloadXML(url+ (str(parent_id) if parent_id else "") )
    namespace = {'': xml.tag.split('}')[0][1:]}

    for part in xml.findall('.//Placemark', namespace):
        id = int(part.find('./name', namespace).text)
        name = part.find('./description', namespace).text.split(';')[0]
        
        # convert polygon string to pairs of (lat,lon) floats
        polygons = [
            x for x in 
                [list(map( 
                    lambda p_str: (float(p_str.split(',')[1]), float(p_str.split(',')[0])),
                    [ p for p in ' '.join(polygon.text.splitlines()).split(' ') if len(p) > 1 ]
                    )) 
                for polygon in part.findall('.//coordinates', namespace)] 
            if len(x) ]

        # level 2s tend to have multiple coordinate tags in a single placemark 
        # whereas the others have multiple placemarks with single coordinates in each

        database.updateOrInsertArea(conn, id,level,name,parent_id)
        for polygon in polygons:
            database.insertPolygonByAreaID(conn, id,polygon)
    
    # depth first parsing
    children = database.getChildAreas(conn, parent_id)
    for child in children:
        _parseLevel(conn, level+1, child[0])
    


def buildDataset():
    print("Building dataset: This might take a while")
    conn = database.connect()
    database.reset(conn)
    _parseLevel(conn)
    database.updatePopulation(conn, _makePopulation())
    conn.close()
    print("Dataset complete!")

if __name__ == "__main__":
    buildDataset()
