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
    with open(args['input'], 'rb') as f:
        input_dict = pickle.load(f)
    return_dict, result = load_and_inference(args['onnx_file'], input_dict)

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
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='path to input file')
    parser.add_argument('-o', '--output', help='path to output directory')
    parser.add_argument('-y', '--onnx_file', default='onnx/partition1_2.onnx', help='complete path to tge ONNX model')
    args = vars(parser.parse_args())
    input_filename = args['input'].split('/')[-1].rsplit('_INTERMEDIATE_PICKLE', 1)[0]
    args['output'] = os.path.join(os.path.dirname(args['output']), input_filename)
    main(args)