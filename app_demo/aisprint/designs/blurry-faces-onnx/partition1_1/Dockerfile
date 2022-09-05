#FROM registry.gitlab.polimi.it/ai-sprint/apps/base:latest
FROM registry.gitlab.polimi.it/ai-sprint/toscarizer/ai-sprint-base

RUN mkdir /opt/blurry-faces-onnx_partition1_1

WORKDIR /opt/blurry-faces-onnx_partition1_1

COPY *.py requirements.* script.sh onnx /opt/blurry-faces-onnx_partition1_1/

RUN apt update && \
    xargs apt install -y --no-install-recommends < requirements.sys  && \
    apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && rm -rf ~/.cache/

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
