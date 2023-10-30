import pickle

import os

# import the necessary libs
import numpy as np
import argparse
import time
import os

import onnx
import onnxruntime as ort
import numpy as np
from scipy.stats import entropy

import cv2
import matplotlib.pyplot as plt

from utils import preprocess_input 

from aisprint.annotations import component_name, early_exits_model, exec_time
from aisprint.onnx_inference import load_and_inference


def early_exit_condition(output, threshold=1):
    # Compute entropy
    H = entropy(output[0][0]) 
    return H < threshold

@component_name(name='classifier')
@exec_time(local_time_thr=10)
@early_exits_model(onnx_file='ee_classifier.onnx', condition_function='early_exit_condition', transition_probabilities=[0.75])
def main(args):
    
    # Pre-Processing
    # --------------

    # load and preprocess image
    orig_image = cv2.imread(args['input'])
    cv2_image = cv2.cvtColor(orig_image, cv2.COLOR_BGR2RGB)
    image = np.expand_dims(cv2_image, axis=0)
    image = image.astype(np.float32)
    image = preprocess_input(image) 
    
    ort_session = ort.InferenceSession(args['onnx_file'])
    input_name = ort_session.get_inputs()[0].name
    input_dict = {input_name: image}
    
    # To be forwarded
    input_dict['cv2_image'] = cv2_image 

    # --------------

    # Load and Inference
    # ------------------

    return_dict, result = load_and_inference(args['onnx_file'], input_dict)

    # Evaluate Early-Exit Condition
    if not early_exit_condition(result):
        intermediate_output = args['output'] + '_INTERMEDIATE_PICKLE'
        with open(intermediate_output, 'wb') as f:
            pickle.dump(return_dict, f)
    else: 
    
        # ------------------
    
        # Post-Processing
        # ---------------
    
    	# Forwared
        cv2_image = return_dict['cv2_image']
        
        # Result
        pred_prob = result[0][0]
        all_classes = np.arange(pred_prob.shape[0])
        sorted_arg = pred_prob.argsort()[-5:][::-1]  # top5 predicted labels
        pred_class = pred_prob[sorted_arg]
        sorted_classes = all_classes[sorted_arg]
    
        pred_tmp = ['{}.  {} | {:.0f} %'.format(str(sorted_classes[i]), p, p*100) for i, p in enumerate(pred_class)]
        text = r''
        text += 'Predicted labels: \n\n    ' + '\n    '.join(pred_tmp)
        arr = np.asarray(cv2_image)
        fig = plt.figure(figsize=(20, 12))
        ax1 = fig.add_axes((.1, .1, .5, 0.9))
        ax1.imshow(arr)
        ax1.set_xticks([]), ax1.set_yticks([])
        ax1.set_xticklabels([]), ax1.set_yticklabels([])
        t = fig.text(.7, .5, text, fontsize=20)
        t.set_bbox(dict(color='white', alpha=0.5, edgecolor='black'))
        plt.savefig(args['output'])
        
        # ---------------
    
if __name__ == '__main__':

	# construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input image")
    parser.add_argument("-o", "--output", help="path to output image")
    parser.add_argument("-y", "--onnx_file", default="onnx/partition1_1.onnx", help="complete path to the ONNX model")
    args = vars(parser.parse_args())

    orig_output = args['output']

    print("SCRIPT: Analyzing file '{}', saving the output images in '{}'".format(args['input'], args['output'])) 

    output_ext = os.path.splitext(args['output'])[1]
    if not output_ext:
        args['output'] = "%s.jpg" % args['output'] 

    main(args) 
