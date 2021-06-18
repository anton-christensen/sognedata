from os import truncate
from flask import Flask, Response, json, request, send_from_directory
from waitress import serve
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
  
  return Response(json.dumps({'success': True, 'data': data}), mimetype='application/json')
def error(message):
  return Response(json.dumps({'success': False, 'error': message}), mimetype='application/json')

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
  return Response(json_dataset.getDataset(), mimetype='application/json')


@api.route('/<int:id>', methods=['GET'])
@api.route('/<int:id>/geometry', methods=['GET'])
def API_regionByID(id, level=None):
  conn = database.connect()
  conn.row_factory=sqlite3.Row # returns rows as dictionary instead of n-tuples
  
  area = regionByID(id, level)
  if area:
    if requestsGeometry():
      area['geometry'] = getGeometryByAreaID(conn, area['id'])
    return success(area)
  else:
    return error("No {} with id {}".format(levelToString(level), id))

def regionByID(id, level=None):
  conn = database.connect()
  conn.row_factory=sqlite3.Row # returns rows as dictionary instead of n-tuples
  
  area = database.getAreaByID(conn, id, level)
  if area:
    return dict(area)
  else:
    None


@api.route('/<float:lat>/<float:lon>', methods=['GET'])
@api.route('/<float:lat>/<float:lon>/geometry', methods=['GET'])
def regionsByCoord(lat,lon,level = None):
  conn = database.connect()
  conn.row_factory=sqlite3.Row # returns rows as dictionary instead of n-tuples
  areas = database.areasByLocation(conn, lat,lon, 3) # find containing l3s, since checking if inside is cheaper than on l2 and l1
  areas = [
    (dict(x), getGeometryByAreaID(conn, x['id'])) 
    for x in areas
  ]

  found = None
  for (area, polygons) in areas:
    for polygon in polygons:
      if pointPolygonIntersection((lat,lon), polygon):
        found = area
        break
    if found != None:
      break
  
  if found == None:
    return error("No {} at location".format(levelToString(level)))

  
  found = [found]
  found.append(regionByID(found[0]['parent_id']))
  found.append(regionByID(found[1]['parent_id']))

  if level == None:
    if requestsGeometry():
      for area in found:
        area['geometry'] = getGeometryByAreaID(conn, area['id'])
  else:
    found = found[3-level]
    if requestsGeometry():
      found['geometry'] = getGeometryByAreaID(conn, found['id'])

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
  return API_regionByID(id, 1)

@api.route('/provsti/<int:id>', methods=['GET'])
@api.route('/provsti/<int:id>/geometry', methods=['GET'])
@api.route('/l2/<int:id>', methods=['GET'])
@api.route('/l2/<int:id>/geometry', methods=['GET'])
def L2ByID(id):
  return API_regionByID(id, 2)

@api.route('/sogn/<int:id>', methods=['GET'])
@api.route('/sogn/<int:id>/geometry', methods=['GET'])
@api.route('/l3/<int:id>', methods=['GET'])
@api.route('/l3/<int:id>/geometry', methods=['GET'])
def L3ByID(id):
  return API_regionByID(id, 3)


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

def init():
  if not database.exists():
    buildDataset()


def serveDevelop():
  init()
  api.run(host='0.0.0.0', port=8000)
  
def serveProduction():
  init()
  print("Serving on port 8000", flush=True)
  serve(api, host='0.0.0.0', port=8000)
  print("quitting")

if __name__ == '__main__':
  serveProduction()
  
