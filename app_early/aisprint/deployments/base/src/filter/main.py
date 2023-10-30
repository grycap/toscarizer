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

    # Pre-Processing
    # --------------

    # load and preprocess image
    orig_image = cv2.imread(args['input'])
    image = cv2.cvtColor(orig_image, cv2.COLOR_BGR2RGB)
    image = np.expand_dims(image, axis=0)
    image = image.astype(np.float32)
    image = preprocess_input(image) 
    
    ort_session = ort.InferenceSession(args['onnx_file'])
    input_name = ort_session.get_inputs()[0].name
    input_dict = {input_name: image}
    
    # To be forwarded
    input_dict['orig_image'] = orig_image

    # --------------

    # Load and Inference
    # ------------------

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
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input image")
    parser.add_argument("-o", "--output", help="path to output image")
    parser.add_argument("-y", "--onnx_file", default="onnx/filter.onnx", help="complete path to tge ONNX model")
    args = vars(parser.parse_args())

    orig_output = args['output']

    print("SCRIPT: Analyzing file '{}', saving the output images in '{}'".format(args['input'], args['output'])) 

    output_dir = os.path.dirname(orig_output)
    output_prefix = os.path.splitext(os.path.basename(orig_output))[0]
    args['output'] = os.path.join(output_dir, "{}-filtered.jpg".format(output_prefix))

    main(args)
