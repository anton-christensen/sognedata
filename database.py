import sqlite3
from sqlite3.dbapi2 import Connection

def connect():
    conn = sqlite3.connect('./data/dataset.sqlite')
    # conn = sqlite3.connect(':memory:')
    return conn

def exists():
    conn = connect()
    cur = conn.cursor()
    res = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='version';").fetchall()
    if len(res) > 0:
        (version, ) = cur.execute("SELECT version FROM version").fetchone()
        return version == "1.0.0"
    return False

def reset(conn:sqlite3.Connection):
    cur = conn.cursor()
    cur.executescript("""
        DROP TABLE IF EXISTS version;
        CREATE TABLE version ( 
            version VARCHAR(32)
        );
        INSERT INTO version
        VALUES ('1.0.0');


        DROP TABLE IF EXISTS level;
        CREATE TABLE level ( 
            level INTEGER PRIMARY KEY, 
            name_singular VARCHAR(20), 
            name_plural VARCHAR(20), 
            data_url VARCHAR(100) 
        );
        INSERT INTO level
        VALUES
            (1, 'stift'  , 'stifter'  , 'https://sogn.dk/maps/kml/stifter_kml.php'),
            (2, 'provsti', 'provstier', 'https://sogn.dk/maps/kml/provstier_kml.php?stiftId='),
            (3, 'sogn'   , 'sogne'    , 'https://sogn.dk/maps/kml/sogne_kml.php?provstiID=');

        DROP TABLE IF EXISTS area;
        CREATE TABLE area ( 
            id INTEGER PRIMARY KEY, 
            level INTEGER, 
            name VARCHAR(100),
            population INTEGER,
            parent_id Integer);
        
        DROP TABLE IF EXISTS polygon;
        CREATE TABLE polygon ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            min_lat REAL, 
            min_lon REAL, 
            max_lat REAL, 
            max_lon REAL, 
            area_id Integer);
        
        DROP TABLE IF EXISTS polygon_point;
        CREATE TABLE polygon_point ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            point_index INTEGER, 
            lat REAL, 
            lon REAL,
            polygon_id Integer);

        DROP VIEW IF EXISTS boundingbox;
        CREATE VIEW boundingbox AS 
        SELECT
            min(min_lat) AS min_lat,
            min(min_lon) AS min_lon,
            max(max_lat) AS max_lat,
            max(max_lon) AS max_lon,
            area_id
        FROM polygon
        GROUP BY area_id;

        DROP TRIGGER IF EXISTS deletePointsOnDeletePolygon;
        CREATE TRIGGER deletePointsOnDeletePolygon 
        AFTER DELETE ON polygon
        BEGIN
            DELETE FROM polygon_point WHERE polygon_id = old.id;
        END;

        DROP TRIGGER IF EXISTS updatePopulationOnAreaUpdate;
        CREATE TRIGGER updatePopulationOnAreaUpdate 
        AFTER UPDATE ON area
        BEGIN
            UPDATE area SET population = (
                SELECT SUM(population) 
                FROM area 
                WHERE parent_id = new.parent_id 
                GROUP BY parent_id
            ) WHERE id = new.parent_id;
        END;
    """)
    conn.commit()

def updateOrInsertArea(conn:sqlite3.Connection, id:int, level:int, name:str, parent_id:int):
    cur = conn.cursor()
    (count, ) = cur.execute('SELECT COUNT(*) FROM area WHERE id=?;', (id, )).fetchone()
    if count > 0:
        cur.execute(
            'UPDATE area SET level=?, name=?, parent_id=? WHERE id=?;',
            (level,name, parent_id ,id)
        )
    else:
        cur.execute(
            'INSERT INTO area (id,level,name,parent_id) VALUES (?,?,?,?);',
            (id,level,name,parent_id)
        )
        cur.execute(
            'DELETE FROM polygon WHERE area_id=?;',
            (id,)
        )
    conn.commit()

def insertPolygonByAreaID(conn:sqlite3.Connection, area_id:int, polygon):
    cur = conn.cursor()
    polygon_id = cur.execute('INSERT INTO polygon (area_id) VALUES (?)',(area_id,)).lastrowid

    # zip polygon with range(len(polygon))
    lats = [p[0] for p in polygon]
    lons = [p[1] for p in polygon]
    polygon_ids = [polygon_id for p in polygon]
    data = list(zip(range(len(polygon)), lats, lons, polygon_ids))
    cur.executemany('INSERT INTO polygon_point (point_index, lat, lon, polygon_id) VALUES (?,?,?,?);', data)
    
    # update boundingbox
    cur.execute("""
        INSERT OR REPLACE INTO polygon (id, min_lat, max_lat, min_lon, max_lon, area_id)
        SELECT
            ? as id,
            min(pp.lat) AS min_lat,
            max(pp.lat) AS max_lat,
            min(pp.lon) AS min_lon,
            max(pp.lon) AS max_lon,
            ? AS area_id
        FROM polygon_point AS pp
        WHERE pp.polygon_id=?
        GROUP BY polygon_id;
    """, (polygon_id, area_id, polygon_id))
    conn.commit()


def getDataURLByLevel(conn:sqlite3.Connection, level):
    cur = conn.cursor()
    res = cur.execute('SELECT data_url FROM level WHERE level = ?;', (level, )).fetchall()
    if len(res) > 0:
        (url, ) = res[0]
        return url
    else:
        return None

def updatePopulation(conn:sqlite3.Connection, populationTable):
    data = [(n, id) for (id, n) in populationTable.items()]
    
    cur = conn.cursor()
    cur.execute('PRAGMA recursive_triggers = ON;')
    cur.executemany(
        'UPDATE area SET population=? WHERE id=?',
        data
    )
    cur.execute('PRAGMA recursive_triggers = OFF;')
    conn.commit()

def areasByLocation(conn:sqlite3.Connection, lat,lon, level = None):
    cur = conn.cursor()
    if level:
        return cur.execute('''
            SELECT a.id, a.level, a.name, a.population, a.parent_id FROM area AS a
            INNER JOIN boundingbox AS bb
            ON a.id = bb.area_id
            WHERE bb.min_lat <= ? 
            AND   bb.max_lat >= ?
            AND   bb.min_lon <= ?
            AND   bb.max_lon >= ?
            AND   a.level = ?;
        ''', (lat,lat,lon,lon, level)).fetchall()
    else:
        return cur.execute('''
            SELECT a.id, a.level, a.name, a.population, a.parent_id FROM area AS a
            INNER JOIN boundingbox AS bb
            ON a.id = bb.area_id
            WHERE bb.min_lat <= ? 
            AND   bb.max_lat >= ?
            AND   bb.min_lon <= ?
            AND   bb.max_lon >= ?;
        ''', (lat,lat,lon,lon)).fetchall()
    
def getChildAreas(conn:sqlite3.Connection, parent_id:int):
    cur = conn.cursor()
    if parent_id == None:
        children = cur.execute(
            'SELECT id, level, name, population, parent_id FROM area WHERE parent_id ISNULL'
        ).fetchall()
        return children
    else:
        children = cur.execute(
            'SELECT id, level, name, population, parent_id FROM area WHERE parent_id = ?;',
            (parent_id, )
        ).fetchall()
        return children

def getpolygonsByArea(conn:sqlite3.Connection, area_id):
    cur = conn.cursor()
    polygons = cur.execute('SELECT id FROM polygon where area_id = ?;', (area_id, )).fetchall()
    polygon_ids = [ (p[0], ) for p in polygons ]
    polygons = []
    for polygon_id in polygon_ids:
        polygons.append(cur.execute('SELECT lat, lon FROM polygon_point WHERE polygon_id = ? ORDER BY point_index ASC', polygon_id).fetchall())
    return polygons

def getAreaByID(conn:sqlite3.Connection, area_id, level = None):
    cur = conn.cursor()
    if level:
        return cur.execute('SELECT id, level, name, population, parent_id FROM area WHERE id = ? AND level = ?', (area_id, level)).fetchone()
    else:
        return cur.execute('SELECT id, level, name, population, parent_id FROM area WHERE id = ?', (area_id, )).fetchone()
        

def getAreasByLevel(conn:sqlite3.Connection, level):
    cur = conn.cursor()
    return cur.execute('SELECT id, level, name, population, parent_id FROM area WHERE level = ?', (level, )).fetchall()

def getProvstiOfStift(conn:sqlite3.Connection, id):
    cur = conn.cursor()
    return cur.execute('''
        SELECT c.id, c.level, c.name, c.population, c.parent_id 
        FROM area AS c
        INNER JOIN area AS p ON c.parent_id = p.id WHERE p.id = ? AND p.level = 1
    ''', (id, )).fetchall()
def getSognOfStift(conn:sqlite3.Connection, id):
    cur = conn.cursor()
    return cur.execute('''
        SELECT so.id, so.level, so.name, so.population, so.parent_id 
        FROM area AS so
        INNER JOIN area AS pr ON so.parent_id = pr.id 
        INNER JOIN area AS st ON pr.parent_id = st.id 
        WHERE st.id = ? AND st.level = 1
    ''', (id, )).fetchall()
def getSognOfProvsti(conn:sqlite3.Connection, id):
    cur = conn.cursor()
    return cur.execute('''
        SELECT c.id, c.level, c.name, c.population, c.parent_id 
        FROM area AS c
        INNER JOIN area AS p ON c.parent_id = p.id WHERE p.id = ? AND p.level = 2
    ''', (id, )).fetchall()