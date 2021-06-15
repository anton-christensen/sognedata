from flask import Flask, json, request, send_from_directory
import sqlite3

import database
from latlongToSogn import pointPolygonIntersection
from db_dataset import buildDataset
import json_dataset
import markdown

api = Flask(__name__)
api.url_map.strict_slashes = False


def levelToString(level):
  if level == None:
    return "area"
  if level == 1:
    return "stift"
  if level == 2:
    return "provsti"
  if level == 3:
    return "sogn"
  return "{ERROR: AREA}"

def success(data):
  
  return json.dumps({'success': True, 'data': data})
def error(message):
  return json.dumps({'success': False, 'error': message})

def getGeometryByAreaID(conn, id):
  res = database.getpolygonsByArea(conn, id)
  res = [ [(lat, lon) for (lat, lon) in x] for x in res ]
  return res

@api.route('/', methods=["GET"])
def index():
  file = open("README.md", "r")
  md = file.read()
  return markdown.markdown(md, extensions=['extra'])

@api.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@api.route('/data/dataset.json')
def datasetJSON():
  return json_dataset.getDataset()


@api.route('/<int:id>', methods=['GET'])
@api.route('/<int:id>/geometry', methods=['GET'])
def regionByID(id, level=None):
  conn = database.connect()
  conn.row_factory=sqlite3.Row # returns rows as dictionary instead of n-tuples
  
  area = database.getAreaByID(conn, id, level)
  if area:
    res = dict(area)
    if requestsGeometry():
      res['geometry'] = getGeometryByAreaID(conn, res['id'])
    return success(res)
  else:
    return error("No {} with id {}".format(levelToString(level), id))

@api.route('/<float:lat>/<float:lon>', methods=['GET'])
@api.route('/<float:lat>/<float:lon>/geometry', methods=['GET'])
def regionsByCoord(lat,lon,level = None):
  conn = database.connect()
  conn.row_factory=sqlite3.Row # returns rows as dictionary instead of n-tuples
  areas = database.areasByLocation(conn, lat,lon, level)
  areas = [
    (dict(x), getGeometryByAreaID(conn, x['id'])) 
    for x in areas
  ]

  found = []
  for (area, polygons) in areas:
    for polygon in polygons:
      if pointPolygonIntersection((lat,lon), polygon):
        if requestsGeometry():
          area['geometry'] = polygons
        found.append(area)
        break
  
  conn.close()
  return success(found)

@api.route('/l1/<float:lat>/<float:lon>', methods=['GET'])
@api.route('/l1/<float:lat>/<float:lon>/geometry', methods=['GET'])
@api.route('/stift/<float:lat>/<float:lon>', methods=['GET'])
@api.route('/stift/<float:lat>/<float:lon>/geometry', methods=['GET'])
def l1ByCoords(lat,lon):
  return regionsByCoord(lat, lon, 1)

@api.route('/l2/<float:lat>/<float:lon>', methods=['GET'])
@api.route('/l2/<float:lat>/<float:lon>/geometry', methods=['GET'])
@api.route('/provsti/<float:lat>/<float:lon>', methods=['GET'])
@api.route('/provsti/<float:lat>/<float:lon>/geometry', methods=['GET'])
def l2ByCoords(lat,lon):
  return regionsByCoord(lat, lon, 2)

@api.route('/l3/<float:lat>/<float:lon>', methods=['GET'])
@api.route('/l3/<float:lat>/<float:lon>/geometry', methods=['GET'])
@api.route('/sogn/<float:lat>/<float:lon>', methods=['GET'])
@api.route('/sogn/<float:lat>/<float:lon>/geometry', methods=['GET'])
def l3ByCoords(lat,lon):
  return regionsByCoord(lat, lon, 3)

@api.route('/stift', methods=['GET'])
@api.route('/stift/geometry', methods=['GET'])
@api.route('/l1', methods=['GET'])
@api.route('/l1/geometry', methods=['GET'])
def allL1():
  return allLn(1)

@api.route('/provsti', methods=['GET'])
@api.route('/provsti/geometry', methods=['GET'])
@api.route('/l2', methods=['GET'])
@api.route('/l2/geometry', methods=['GET'])
def allL2():
  return allLn(2)

@api.route('/sogn', methods=['GET'])
@api.route('/sogn/geometry', methods=['GET'])
@api.route('/l3', methods=['GET'])
@api.route('/l3/geometry', methods=['GET'])
def allL3():
  return allLn(3)

def allLn(n):
  conn = database.connect()
  conn.row_factory=sqlite3.Row
  areas = database.getAreasByLevel(conn, n)
  areas = [dict(x) for x in areas]

  if requestsGeometry():
    for area in areas:
      area['geometry'] = getGeometryByAreaID(conn, area['id'])

  conn.close()
  
  return success([dict(area) for area in areas])

@api.route('/stift/<int:id>', methods=['GET'])
@api.route('/stift/<int:id>/geometry', methods=['GET'])
@api.route('/l1/<int:id>', methods=['GET'])
@api.route('/l1/<int:id>/geometry', methods=['GET'])
def L1ByID(id):
  return regionByID(id, 1)

@api.route('/provsti/<int:id>', methods=['GET'])
@api.route('/provsti/<int:id>/geometry', methods=['GET'])
@api.route('/l2/<int:id>', methods=['GET'])
@api.route('/l2/<int:id>/geometry', methods=['GET'])
def L2ByID(id):
  return regionByID(id, 2)

@api.route('/sogn/<int:id>', methods=['GET'])
@api.route('/sogn/<int:id>/geometry', methods=['GET'])
@api.route('/l3/<int:id>', methods=['GET'])
@api.route('/l3/<int:id>/geometry', methods=['GET'])
def L3ByID(id):
  return regionByID(id, 3)


@api.route('/stift/<int:id>/provsti', methods=['GET'])
@api.route('/stift/<int:id>/provsti/geometry', methods=['GET'])
@api.route('/l1/<int:id>/l2', methods=['GET'])
@api.route('/l1/<int:id>/l2/geometry', methods=['GET'])
def getProvstiOfStift(id):
  conn = database.connect()
  conn.row_factory=sqlite3.Row
  areas = database.getProvstiOfStift(conn, id)
  areas = [dict(x) for x in areas]
  if requestsGeometry():
    for area in areas:
      area['geometry'] = getGeometryByAreaID(conn, area['id'])
  return success([dict(x) for x in areas])
    
@api.route('/stift/<int:id>/sogn', methods=['GET'])
@api.route('/stift/<int:id>/sogn/geometry', methods=['GET'])
@api.route('/l1/<int:id>/l3', methods=['GET'])
@api.route('/l1/<int:id>/l3/geometry', methods=['GET'])
def getSognOfStift(id):
  conn = database.connect()
  conn.row_factory=sqlite3.Row
  areas = database.getSognOfStift(conn, id)
  areas = [dict(x) for x in areas]
  if requestsGeometry():
    for area in areas:
      area['geometry'] = getGeometryByAreaID(conn, area['id'])
  return success([dict(x) for x in areas])

@api.route('/provsti/<int:id>/sogn', methods=['GET'])
@api.route('/provsti/<int:id>/sogn/geometry', methods=['GET'])
@api.route('/l2/<int:id>/l3', methods=['GET'])
@api.route('/l2/<int:id>/l3/geometry', methods=['GET'])
def getSognOfProvsti(id):
  conn = database.connect()
  conn.row_factory=sqlite3.Row
  areas = database.getSognOfProvsti(conn, id)
  areas = [dict(x) for x in areas]
  if requestsGeometry():
    for area in areas:
      area['geometry'] = getGeometryByAreaID(conn, area['id'])
  return success([dict(x) for x in areas])


def requestsGeometry():
  return request.base_url.split('/')[-1] == "geometry"

if __name__ == '__main__':
  if not database.exists():
    buildDataset()
  api.run(host='0.0.0.0', port=80)

