
import os
import pydicom
import numpy as np
import sys
from scipy import ndimage
from skimage.transform import resize
import glob
import pandas as pd
import base64
import json
import pickle
import re
import uuid
import shutil
import zipfile
import time
import functools
import random
import string
from google_drive_downloader import GoogleDriveDownloader as gdd
import random
from datetime import datetime
from PIL import Image as im
from flask import Flask
from flask import request

app = Flask(__name__)


def filter_image(threshold_value, img):
    img_ = img.copy()
    img_max = img.max()
    img_min = img.min()
    img_ += threshold_value
    img_[img_ < img_min] = img_min
    img_[img_ > img_max] = img_max
    return img_

def normalize_image(img, axis=None):
    return (img - img.min()) / (img.max() - img.min())


def read_DICOM_slices(path, viewOfDicomName, viewOfDicomSliceNumber, viewOfDicomThreshold):
    # Load the DICOM files
    files = []
    for fname in glob.glob(path + '*', recursive=False):
        if fname[-4:] == '.dcm': # Read only dicom files inside folders.
            files.append(pydicom.dcmread(fname))

    # Skip files with no SliceLocation
    slices = []
    for f in files:
        slices.append(f)

    imgPixelData = slices[0].pixel_array
    img_shape = list(imgPixelData.shape)
    img_shape.append(len(slices))
    img3d = np.zeros(img_shape)
    
    # Fill 3D array with the images from the files
    for i, img2d in enumerate(slices):
        img3d[:, :, i] = img2d.pixel_array

    array = None
    if (viewOfDicomName == 'Axial'):
        array = normalize_image(filter_image(int(viewOfDicomThreshold), img3d[:, :, int(viewOfDicomSliceNumber)]))

    array *= 255
    data = im.fromarray(array)
    now = datetime.now() # current date and time
    date_time = now.strftime("%m.%d.%Y.%H.%M.%S")
    random.seed(10)
    imageName = 'image' + date_time + str(random.random() * 10**10) + '.png'

    data.convert('RGB').save(imageName)

    png_encoded = ''
    with open(imageName, "rb") as f:
        data = f.read()
        png_encoded = base64.b64encode(data)

    os.remove(imageName)
    return png_encoded


@app.route("/")
def read_dicom():
    folderId = request.args.get('folderId')
    viewOfDicomName = request.args.get('viewOfDicomName')
    viewOfDicomSliceNumber = request.args.get('viewOfDicomSliceNumber')
    viewOfDicomThreshold = request.args.get('viewOfDicomThreshold')
    print('folderId===', folderId)
    print('viewOfDicomName===', viewOfDicomName)
    print('viewOfDicomSliceNumber===', viewOfDicomSliceNumber)
    print('viewOfDicomThreshold===', viewOfDicomThreshold)
    return read_DICOM_slices("./DCOM/" + folderId + "/", viewOfDicomName, viewOfDicomSliceNumber, viewOfDicomThreshold)

if __name__=="__main__":
    app.run(debug=True)
