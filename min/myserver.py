from os import listdir
from os.path import isfile, join
import traceback
import json
import uuid
import re
import tempfile
from flask import Flask, request
import wand.image
import wand.display
import wand.exceptions
app = Flask(__name__)

#local stuff
from img import persisted_img
im = persisted_img()

def get_ratio_size(w, h, size):
    if w > h:
        w0 = size
        h0 = size * h / w
    else:
        h0 = size
        w0 = size * w / h
    return [w0, h0]

@app.route('/similar_image', methods=['GET', 'POST'])
def similar_image():
    params = request.get_json()
    if 'image' in params:
        image = params['image']
    else:
        return 'error', 201
    try:
        match, total_count = im.match(image, 0, 1)
        return json.dumps(match[0])
    except:
        traceback.print_exc()
    return '', 400

@app.route('/add_image', methods=['GET', 'POST'])
def add_image():
    params = request.get_json()
    if 'image' in params:
        image = params['image']
        im.add_image(image)
    else:
        return 'error', 201
    return 'ok', 200

@app.route('/delete_image', methods=['GET', 'POST'])
def delete_image():
    im.__init__()
    return 'ok', 200

@app.route('/search_image_page', methods=['GET', 'POST'])
def search_image_page():
    params = request.get_json()
    if 'image' in params:
        image = params['image']
    else:
        return 'error', 201
    if 'offset' in params:
        offset = int(params['offset'])
    else:
        offset = 0

    try:
        matches, total_count = im.match(image, offset, offset+10)
        res = dict()
        res['matches'] = matches
        res['total_count'] = total_count
        return json.dumps(res)
    except:
        traceback.print_exc()
    return '', 400

@app.route('/resize_image_api', methods=['GET', 'POST'])
def resize_image_api():
    params = request.get_json()
    if 'source_image' in params:
        source_image = params['source_image']
    else:
        return 'error', 400
    if 'new_image' in params:
        new_image = params['new_image']
    else:
        return 'error', 400
    if 'image_size' in params:
        image_size = params['image_size']
    else:
        return 'error', 400
    try:
        with wand.image.Image(filename=source_image) as img:
            w = img.width
            h = img.height
            [w0, h0] = get_ratio_size(w, h, image_size)
            img.resize(w0, h0)
            img.save(filename=new_image)            
            return 'success', 200
    except:
        return 'error', 400
    return '', 400

if __name__ == "__main__":
    #todo: toggle debug from config
    app.debug = False
    app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    app.run(threaded=True)
    # app.run(host= '0.0.0.0', threaded=True)
