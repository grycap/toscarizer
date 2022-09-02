import pickle

import os

import argparse

import onnx
import onnxruntime as ort
import numpy as np

import cv2


from aisprint.annotations import (component_name, exec_time, 
								  partitionable_model, device_constraints, security)
from aisprint.onnx_inference import load_and_inference

@component_name(name='mask-detector-onnx')
@exec_time(local_time_thr=10, global_time_thr=40, prev_components=['blurry-faces-onnx'])
@partitionable_model(onnx_file='yolov3-tiny.onnx')
@device_constraints(ram=1024, vram=2048, use_gpu_for=['dnn'])
@security(trustedExecution=False, networkShield=False, filesystemShield=False)
def main(args):

	# Pre-Processing
	# --------------

	# load our input image and get it height and width
	image = cv2.imread(args['input'])
	(H, W) = image.shape[:2]

	# construct a blob from the input image and then perform a forward
	# pass of the YOLO object detector, giving us our bounding boxes and
	# associated probabilities
	blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416),swapRB=True, crop=False)

	ort_session = ort.InferenceSession(args['onnx_file'])
	input_name = ort_session.get_inputs()[0].name
	input_dict = {input_name: np.transpose(blob, [0, 2, 3, 1])}

	# To be forwarded
	input_dict['confidence'] = args['confidence']
	input_dict['threshold'] = args['threshold']
	input_dict['classes'] = args['classes']
	input_dict['image'] = image 
	return_dict['COLORS'] = args['COLORS']
	return_dict['LABELS'] = args['LABELS']
	return_dict['keep'] = False

	# --------------

	# Load and Inference
	# ------------------

	result_dict, _ = load_and_inference(args['onnx_file'], input_dict)

	with open(args['output'], 'wb') as f:
	    pickle.dump(result_dict, f)

if __name__ == '__main__':
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--image", required=True, help="path to input image")
    parser.add_argument("-o", "--output",help="path to output image")
    parser.add_argument("-y", "--onnx_file", default="/opt/mask-detector/onnx_model/yolov3-tiny.onnx", help="complete path to tge ONNX model")
    parser.add_argument("-cfg", "--cfg_path", default="/opt/mask-detector/cfg", help="base path to the obj.names specifying classes names")
    parser.add_argument("-c", "--confidence", type=float, default=0.2, help="minimum probability to filter weak detections")
    parser.add_argument("-t", "--threshold", type=float, default=0.1, help="threshold when applying non-max suppression")
    args = vars(parser.parse_args())

    # load the class labels our YOLO model was trained on
    labelsPath = os.path.sep.join([args["cfg_path"], "obj.names"])
    args['LABELS'] = open(labelsPath).read().strip().split("\n")
    # initialize a list of colors to represent each possible class label (red and green)
    args['COLORS'] = [[0,255,0], [0,0,255]]

    main(args)
