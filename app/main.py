from __future__ import print_function, division
import flask
import getopt
import numpy as np
import sys
import json
import geojson
import pymongo
import scipy.stats as stats
import os

#   Initialize globals

app = flask.Flask(__name__)
mongo_collection = None

#   Helper functions

def report_memory_usage():
    result = {'peak' : 0, 'rss' : 0}
    with open('/proc/{}/status'.format(os.getpid())) as status:
        for line in status:
            parts = line.split()
            key = parts[0][2:-1].lower()
            if key in result:
                result[key] = int(parts[1]) // 1024
    print(', '.join(["{}: {}MB".format(key, value) for key, value in result.items()]))

def find_near(point, distance, fields=None):
    result = list(mongo_collection.find({'loc' : {'$near' : { '$geometry' : point, '$maxDistance' : distance }}}, fields))
    if result and '_id' in result[0]:
        for r in result:
            r['_id'] = str(r['_id'])
    return result

#   Flask: data

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def send_js(path):
    print('sending {}'.format(path))
    return flask.send_from_directory('.', path)

#   Flask: actions

@app.route("/submit", methods=["POST"])
def submit():
    """
    """
    
    #	Retrieve data

    data = flask.request.json
    print(data)

    #   Get listings
    
    distance = data.get('distance', 500)
    lat, lng = float(data['latitude']), float(data['longitude'])
    fields = data.get('fields', ['id_', 'loc', 'price'])
    listings = find_near(geojson.Point((lng, lat)), distance, fields)
    listings = sorted([l for l in listings if l['price'] < 10000], key=lambda l: l['price'])

    #   Get Probability Distribution

    prices = [l['price'] for l in listings]
    pdf = stats.norm.pdf(prices, np.mean(prices), np.std(prices))
    for i, l in enumerate(listings):
        l['pdf'] = pdf[i]

    #	Package and return result
    
    print('{} results'.format(len(listings)))
    result = flask.jsonify(listings)
    del listings, prices, pdf

    report_memory_usage()
    return result

#   Initialize application

def app_init():
    global mongo_collection
    mongo_client = pymongo.MongoClient('ec2-34-198-246-43.compute-1.amazonaws.com', 27017)
    mongo_collection = mongo_client.renthop.listings
    print('Found {} listings'.format(mongo_collection.count()))

#   Main

def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'dh:', ['debug', 'host='])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    debug = False
    host = '0.0.0.0'

    for opt, arg in opts:
        if opt in ['-d', '--debug']:
            debug = True
        elif opt in ['-h', '--host']:
            host = arg

    app_init()
    app.run(host=host, debug=debug)


if __name__ == '__main__':
    main(sys.argv[1:])