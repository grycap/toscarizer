import pickle

import os
import sys
import subprocess
import time

import argparse

import onnx
import onnxruntime as ort
import numpy as np

import cv2

from utils import postprocess, blur_boxes

from aisprint.annotations import annotation
from aisprint.onnx_inference import load_and_inference

@annotation({'component_name': {'name': 'blurry-faces-onnx'}, 
             'exec_time': {'local_time_thr': 20}, 
             'partitionable_model': {'onnx_file': 'version-RFB-640.onnx'},
             'expected_throughput': {'rate': 1},
             'device_constraints': {'ram': 1024, 'vram': 2048, 'use_gpu_for': ['dnn']},
             'security': {'trustedExecution': False,
                          'networkShield': False, 'filesystemShield': False}})
def main(args):

    # Pre-Processing
    # --------------

    # load and preprocess image
    orig_image = cv2.imread(args['input'])
    image = cv2.cvtColor(orig_image, cv2.COLOR_BGR2RGB)
    # image = cv2.resize(image, (320, 240))
    image = cv2.resize(image, (640, 480))
    image_mean = np.array([127, 127, 127])
    image = (image - image_mean) / 128
    image = np.transpose(image, [2, 0, 1])
    image = np.expand_dims(image, axis=0)
    image = image.astype(np.float32)
    
    ort_session = ort.InferenceSession(args['onnx_file'])
    input_name = ort_session.get_inputs()[0].name
    input_dict = {input_name: image}

    # To be forwarded
    input_dict['threshold'] = args['threshold']
    input_dict['classes'] = args['classes']
    input_dict['visualize_count'] = args['visualize_count']
    input_dict['orig_image'] = orig_image 
    input_dict['keep'] = False

    # --------------

    # Load and Inference
    # ------------------

    result_dict, _ = load_and_inference(args['onnx_file'], input_dict)

    with open(args['output'], 'wb') as f:
        pickle.dump(result_dict, f)

if __name__ == '__main__':
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input video")
    parser.add_argument("-o", "--output", help="path to output directory")
    parser.add_argument("-y", "--onnx_file", default="/opt/blurry-faces/onnx/version-RFB-640.onnx", help="complete path to tge ONNX model")
    parser.add_argument("-t", "--threshold", type=float, default=0.7, help="threshold when applying non-max suppression")
    parser.add_argument('--visualize_count', default=False, action='store_true', help="whether to visualize the count of the detected faces on the image")
    args = vars(parser.parse_args())

    orig_input = args['input']
    orig_output = args['output']

    args['classes'] = ['BACKGROUND', 'face']

    print("SCRIPT: Analyzing file '{}', saving the outputimages in '{}'".format(args['input'], args['output'])) 

    # subprocess.run(['ffmpeg', '-i', '"$INPUT_FILE_PATH"', '-vf', 'fps=12/60', '"$OUTPUT_SUBFOLDER/img%d.jpg"'])
    subprocess.run(['ffmpeg', '-i', '{}'.format(orig_input), '-vf', 'fps=12/60', '{}/img%d.jpg'.format(orig_output)])

    frames = next(os.walk(os.path.join(orig_output)))[2]
    frames = [frame for frame in frames if '.jpg' in frame]

    for frame in frames:
        args['input'] = os.path.join(orig_output, frame)
        args['output'] = os.path.join(orig_output, frame)

        main(args)
