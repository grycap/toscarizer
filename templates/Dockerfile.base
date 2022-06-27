FROM python:3.8
LABEL maintainer="Miguel Caballer <micafer1@upv.es>"
LABEL version="0.1"
LABEL description="Base container image for the AI-SPRINT use cases."

RUN pip install --upgrade pip
RUN pip install --no-cache-dir \
    numpy==1.23.0 \
    opencv-python==4.4.0.46 \
    onnx==1.11.0 \
    onnxruntime==1.11.1 \
    protobuf==3.20.1
