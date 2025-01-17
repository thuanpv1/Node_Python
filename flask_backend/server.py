
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
    isSliceLocation = False
    try:
        slices.sort(key=lambda x: (x.SliceLocation))
        isSliceLocation = True
    except:
        slices.sort(key=lambda x: int(x.InstanceNumber))
    # Fill 3D array with the images from the files
    for i, img2d in enumerate(slices):
        img3d[:, :, i] = img2d.pixel_array

    columns = ['AccessionNumber', 'AcquisitionNumber', 'BitsAllocated', 'BitsStored', 'Columns', 'DeviceSerialNumber', 'EchoNumbers', 'EchoTime',
 'EchoTrainLength', 'FlipAngle', 'FrameOfReferenceUID', 'HeartRate', 'HighBit', 'HighRRValue', 'ImageComments', 'ImagedNucleus', 'ImagingFrequency', 'InPlanePhaseEncodingDirection', 'InstanceCreationDate', 'InstanceCreationTime', 'InstanceCreatorUID', 'InstanceNumber', 
'InstitutionName', 'IntervalsAcquired', 'IntervalsRejected', 'InversionTime', 'LowRRValue', 'MRAcquisitionType', 'MagneticFieldStrength', 'Manufacturer', 'ManufacturerModelName', 
'Modality', 'NumberOfAverages', 'NumberOfPhaseEncodingSteps', 'PatientBirthDate', 'PatientID', 'PatientName', 'PatientPosition', 'PatientSex', 'PatientWeight', 
'PercentPhaseFieldOfView', 'PercentSampling', 'PhotometricInterpretation', 'PixelRepresentation', 'PixelSpacing', 'PositionReferenceIndicator', 
'ProtocolName', 'ReceiveCoilName', 'ReferringPhysicianName', 'RepetitionTime', 'Rows', 'SOPClassUID', 'SOPInstanceUID', 'SamplesPerPixel', 'ScanOptions', 
'ScanningSequence', 'SequenceVariant', 'SeriesDate', 'SeriesDescription', 'SeriesInstanceUID', 'SeriesNumber', 'SeriesTime', 'SliceThickness', 'SoftwareVersions',
 'SpacingBetweenSlices', 'SpecificCharacterSet', 'StudyDate', 'StudyDescription', 'StudyID', 'StudyInstanceUID', 'StudyTime', 'TransmitCoilName', 'WindowCenter', 
 'WindowWidth']
    col_dict = {col: [] for col in columns}
    try:
        for col in columns: 
            col_dict[col].append(str(getattr(files[0], col)))
        
        df = pd.DataFrame(col_dict).T
        df.columns = ['Patient']
    except:
        df = pd.DataFrame([])

    array = None
    if viewOfDicomSliceNumber is None:
        viewOfDicomSliceNumber = 0
    if viewOfDicomThreshold is None:
        viewOfDicomThreshold = 0
    if viewOfDicomName is None:
        viewOfDicomName = 'Axial'
    
    threshold = int(img3d[:, :, viewOfDicomSliceNumber].max())
    
    if (viewOfDicomName == 'Axial'):
        array = normalize_image(filter_image(int(viewOfDicomThreshold), img3d[:, :, int(viewOfDicomSliceNumber)]))
    if (viewOfDicomName == 'Coronal') and isSliceLocation:
        threshold = int(img3d[viewOfDicomSliceNumber, :, :].max())
        array = normalize_image(filter_image(int(viewOfDicomThreshold), resize(ndimage.rotate(img3d[int(viewOfDicomSliceNumber), :, :].T, 180), (img3d.shape[0],img3d.shape[0]))))
    if (viewOfDicomName == 'Sagittal') and isSliceLocation:
        threshold = int(img3d[:, viewOfDicomSliceNumber, :].max())
        array = normalize_image(filter_image(int(viewOfDicomThreshold), resize(ndimage.rotate(img3d[:, int(viewOfDicomSliceNumber), :], 90), (img3d.shape[0],img3d.shape[0]))))

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
    return json.dumps({
            'patientInfo': df.to_dict(),
            'isSliceLocation': isSliceLocation,
            'threshold': threshold,
            'numberOfSlices': len(slices),
            'base64Img': (png_encoded).decode()
        })


@app.route("/", methods = ['GET'])
def read_dicom():
    folderId = request.args.get('folderId')
    viewOfDicomName = request.args.get('viewOfDicomName')
    viewOfDicomSliceNumber = request.args.get('viewOfDicomSliceNumber')
    viewOfDicomThreshold = request.args.get('viewOfDicomThreshold')
    print('folderId===', folderId)
    print('viewOfDicomName===', viewOfDicomName)
    print('viewOfDicomSliceNumber===', viewOfDicomSliceNumber)
    print('viewOfDicomThreshold===', viewOfDicomThreshold)
    if folderId is None:
        folderId = 'test'
    return read_DICOM_slices("./DCOM/" + folderId + "/", viewOfDicomName, viewOfDicomSliceNumber, viewOfDicomThreshold)
@app.route("/getfolder", methods = ['GET'])
def read_folders():
    my_list = os.listdir('./DCOM')
    return json.dumps(my_list)

if __name__=="__main__":
    app.run(debug=True)
