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
	with open(args['input'], 'rb') as f:
	    input_dict = pickle.load(f)
	result_dict, result = load_and_inference(args['onnx_file'], input_dict)


	# ------------------

	# Post-Processing
	# ---------------

	# Result
	# output is a list of 2 tensors [1xNx4, 1xNx2]
	pred_boxes = result[0][0]  # remove also batch (eq to 1)
	pred_scores = result[1][0] # remove also batch (eq to 1)

	# Forwarded
	input_confidence = return_dict['confidence']
	input_threshold = return_dict['threshold']
	image = return_dict['image']
	COLORS = return_dict['COLORS']
	LABELS = return_dict['LABELS']
	
	# initialize our lists of detected bounding boxes, confidences, and
	# class IDs, respectively
	boxes = []
	confidences = []
	classIDs = []

	# loop over each of the detections
	for detection_idx, detection in enumerate(pred_boxes):

		# extract the class ID and confidence (i.e., probability) of
		# the current object detection
		scores = pred_scores[detection_idx, :] #last 2 values in vector
		classID = np.argmax(scores)
		confidence = scores[classID]
		# filter out weak predictions by ensuring the detected
		# probability is greater than the minimum probability
		if confidence > input_confidence:
			# scale the bounding box coordinates back relative to the
			# size of the image, keeping in mind that YOLO actually
			# returns the center (x, y)-coordinates of the bounding
			# box followed by the boxes' width and height
			box = detection / 416 * np.array([W, H, W, H])
			(centerX, centerY, width, height) = box.astype("int")
			# use the center (x, y)-coordinates to derive the top and
			# and left corner of the bounding box
			x = int(centerX - (width / 2))
			y = int(centerY - (height / 2))
			# update our list of bounding box coordinates, confidences,
			# and class IDs
			boxes.append([x, y, int(width), int(height)])
			confidences.append(float(confidence))
			classIDs.append(classID)

	# apply NMS to suppress weak, overlapping bounding
	idxs = cv2.dnn.NMSBoxes(boxes, confidences, input_confidence, input_threshold)

	border_size=100
	border_text_color=[255,255,255]
	#Add top-border to image to display stats
	image = cv2.copyMakeBorder(image, border_size,0,0,0, cv2.BORDER_CONSTANT)
	#calculate count values
	filtered_classids=np.take(classIDs,idxs)
	mask_count=(filtered_classids==0).sum()
	nomask_count=(filtered_classids==1).sum()
	#display count
	text = "NoMaskCount: {}  MaskCount: {}".format(nomask_count, mask_count)
	cv2.putText(image,text, (0, int(border_size-50)), cv2.FONT_HERSHEY_SIMPLEX,0.8,border_text_color, 2)
	#display status
	text = "Status:"
	cv2.putText(image,text, (W-300, int(border_size-50)), cv2.FONT_HERSHEY_SIMPLEX,0.8,border_text_color, 2)

	ratio=nomask_count/(mask_count+nomask_count+np.finfo(np.float32).eps)

	if ratio>=0.1 and nomask_count>=3:
		text = "Danger !"
		cv2.putText(image,text, (W-200, int(border_size-50)), cv2.FONT_HERSHEY_SIMPLEX,0.8,[26,13,247], 2)
		
	elif ratio!=0 and np.isnan(ratio)!=True:
		text = "Warning !"
		cv2.putText(image,text, (W-200, int(border_size-50)), cv2.FONT_HERSHEY_SIMPLEX,0.8,[0,255,255], 2)

	else:
		text = "Safe "
		cv2.putText(image,text, (W-200, int(border_size-50)), cv2.FONT_HERSHEY_SIMPLEX,0.8,[0,255,0], 2)

	# ensure at least one detection exists
	if len(idxs) > 0:

		# loop over the indexes we are keeping
		for i in idxs.flatten():
			
			# extract the bounding box coordinates
			(x, y) = (boxes[i][0], boxes[i][1]+border_size)
			(w, h) = (boxes[i][2], boxes[i][3])
			# draw a bounding box rectangle and label on the image
			color = [int(c) for c in COLORS[classIDs[i]]]
			cv2.rectangle(image, (x, y), (x + w, y + h), color, 1)
			text = "{}: {:.4f}".format(LABELS[classIDs[i]], confidences[i])
			cv2.putText(image, text, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX,0.5, color, 1)

	if args["output"]:
		#save the image
		cv2.imwrite(args["output"],image)
	else: 
		# show the output image
		cv2.imshow("Image",image)
		cv2.waitKey(0)

	# ---------------



if __name__ == '__main__':
    parser.argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='path to input file')
    parser.add_argument('-o', '--output', help='path to output directory')
    parser.add_argument('-y', '--onnx_file', help='complete path to tge ONNX model')
    args = vars(parser.parse_args())
    main(args)