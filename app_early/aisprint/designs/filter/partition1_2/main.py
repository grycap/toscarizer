import pickle

import os

import os

import argparse

import onnx
import onnxruntime as ort
import numpy as np

import cv2

from utils import preprocess_input

from aisprint.annotations import annotation
from aisprint.onnx_inference import load_and_inference

@annotation({'component_name': {'name': 'filter'}, 
             'exec_time': {'local_time_thr': 20}, 
             'partitionable_model': {'onnx_file': 'filter.onnx'},
             'expected_throughput': {'rate': 1}})
def main(args):
    with open(args['input'], 'rb') as f:
        input_dict = pickle.load(f)
    return_dict, result = load_and_inference(args['onnx_file'], input_dict)

    # ------------------

    # Post-Processing
    # ---------------
    orig_image = return_dict['orig_image']
    
    # Get predicted class 
    softmax = result[0]
    pred_class = np.argmax(softmax)
    if pred_class == 1:
        cv2.imwrite(args['output'], orig_image)
        print('An animal has been detected in the image.',
              'Image has been saved succesfully at', args['output'], 'path')
    
    # ---------------


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='path to input file')
    parser.add_argument('-o', '--output', help='path to output directory')
    parser.add_argument('-y', '--onnx_file', default='onnx/partition1_2.onnx', help='complete path to tge ONNX model')
    args = vars(parser.parse_args())
    input_filename = args['input'].split('/')[-1]
    args['output'] = os.path.join(os.path.dirname(args['output']), input_filename)
    main(args)