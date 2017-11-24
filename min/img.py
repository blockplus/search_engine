import os
from os import listdir
from os.path import isfile, join
import traceback
import json
import uuid
import re
import tempfile
import wand.image
import wand.display
import wand.exceptions
import cv2
import numpy
import sqlite3
import pickle
from datetime import datetime

#max number of images in each matrix, for parallel processing
DESC_MAX_LEN = 100000
BANK_PATH = '/var/www/web/assets/bank'

'''
note the licensing issues with using SURF/SIFT, alternatives are FREAK, BRISK for
feature detection
'''
def get_surf_des(filename):
    extension  = os.path.splitext(filename)[-1]
    if extension == '.gif':
        tmp_filename = '/var/tmp/giffile.querycustom.jpg'
        try:
            with wand.image.Image(filename=filename) as img:
                img.save(filename=tmp_filename)            
                f = cv2.imread(tmp_filename)
                #hessian threshold 800, 64 not 128
                surf = cv2.SURF(800, extended=False)
                kp, des = surf.detectAndCompute(f, None)
                os.remove(tmp_filename)
        except:
            return None, None
    else:
        f = cv2.imread(filename)
        #hessian threshold 800, 64 not 128
        surf = cv2.SURF(800, extended=False)
        kp, des = surf.detectAndCompute(f, None)
    return kp, des

class _img:
    def __init__(self):
        self.imap = []
        self.r = 0
        self.descs = []
        index_params = dict(algorithm=1,trees=4)
        self.flann = cv2.FlannBasedMatcher(index_params,dict())

    def add_image(self, filename, des=None):
        if des is None:
            kv, des = get_surf_des(filename)
        self.imap.append({
            'index_start' : self.r,
            'index_end' : self.r + des.shape[0] - 1,
            'file_name' : filename
        })
        self.r += des.shape[0]
        #it's really slow to do a vstack every time, so just maintain a list and
        #replicate it as a concatenated numpy ndarray every time. an optimization
        #would be to do a numpy.vstack((self.descs, numpy,array(des))) where self.descs
        #is a numpy.array
        self.descs.append(des)

    def match(self, filename):
        kp, to_match = get_surf_des(filename)
        img_db = numpy.vstack(numpy.array(self.descs))
        #this should be reversed, need to update distance calculation
        matches = self.flann.knnMatch(img_db, to_match, k=4)
        sim = dict()
        for img in self.imap:
            sim[img['file_name']] = 0
        for i in xrange(0, len(matches)):
            match = matches[i]
            if match[0].distance < (.6 * match[1].distance):
                for img in self.imap:
                    if img['index_start'] <= i and img['index_end'] >= i:
                        sim[img['file_name']] += 1
        return sim

    def __len__(self):
        return len(self.descs)

class img:
    def __init__(self):
        self.ims = [_img()]
        self.count = 0

    def get_count(self):
        return self.count

    def add_image(self, filename, des=None):
        self.count += 1
        self.ims[-1].add_image(filename, des=des)
        if len(self.ims[-1]) > DESC_MAX_LEN:
            self.ims.append(_img())

    def match(self, filename, start, end):
        import multiprocessing.dummy
        p = multiprocessing.dummy.Pool(10)
        def f(instance):
            return instance.match(filename)

        res = p.map(f, [i for i in self.ims])
        sim = dict((k,v) for d in res for (k,v) in d.items())
        sorted_sim = sorted(sim.items(), key=lambda x:x[1], reverse=True)
        sorted_sim = [{'image' : x[0], 'similarity' : x[1]} for x in sorted_sim]
        sorted_sim = filter(lambda x:x['similarity'] > 5, sorted_sim)
        total_count = len(sorted_sim)
        sorted_sim = sorted_sim[start: end]
        return sorted_sim, total_count

class persisted_img(img):
    def __init__(self):
        #optimization, should additionally wrap img once more instead, so it works without persistence
        img.__init__(self)

        images = filter(
            lambda x : re.search('\.(jpg|jpeg|png)', x.lower()) != None,
            [join(BANK_PATH, f) for f in listdir(BANK_PATH) if isfile(join(BANK_PATH,f))]
        )
        for f in images:
            self.add_image(f)

    def add_image(self, filename):
        kv, des = get_surf_des(filename)    
        img.add_image(self, filename, des=des)