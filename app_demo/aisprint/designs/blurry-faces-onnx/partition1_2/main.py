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
    with open(args['input'], 'rb') as f:
        input_dict = pickle.load(f)
    return_dict, result = load_and_inference(args['onnx_file'], input_dict)


    # ------------------

    # Post-Processing
    # ---------------
    
    # Result
    confidences, boxes = result

    # Forwarded
    orig_image = return_dict['orig_image']
    threshold = return_dict['threshold']
    classes = return_dict['classes']
    visualize_count = return_dict['visualize_count']

    # post process (NMS)
    boxes, labels, probs = postprocess(
        orig_image.shape[1], orig_image.shape[0], confidences, boxes, threshold)

    total = boxes.shape[0]

    detection_image = orig_image.copy()
    blur_image = orig_image.copy()

    # Visualize detection boxes
    for i in range(boxes.shape[0]):
        box = boxes[i, :]
        label = f"{classes[labels[i]]}: {probs[i]:.2f}"

        cv2.rectangle(detection_image, (box[0], box[1]), (box[2], box[3]), (255, 255, 0), 4)

        cv2.putText(detection_image, label,
                    (box[0] + 20, box[1] + 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,  # font scale
                    (255, 0, 255),
                    2)  # line type

    # Blur detected faces
    blur_image = blur_boxes(blur_image, boxes)

    if visualize_count:
        border_size=100
        border_text_color=[255,255,255]
        #Add top-border to image to display stats
        blur_image = cv2.copyMakeBorder(blur_image, border_size,0,0,0, cv2.BORDER_CONSTANT)
        text = "Number detected faces: {}".format(total)
        cv2.putText(blur_image,text, (0, int(border_size-50)), cv2.FONT_HERSHEY_SIMPLEX,0.8,border_text_color, 2)

    # if image will be saved then save it
    if args['output']:
        cv2.imwrite(args['output'], blur_image)
        print('Image has been saved successfully at', args['output'],
              'path')
    else:
        cv2.imshow('blurred', blur_image)
        # when any key has been pressed then close window and stop the program
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    # ---------------


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='path to input file')
    parser.add_argument('-o', '--output', help='path to output directory')
    parser.add_argument('-y', '--onnx_file', default='onnx/partition1_2.onnx', help='complete path to tge ONNX model')
    args = vars(parser.parse_args())
    main(args)