FROM python:3.8
LABEL maintainer="Miguel Caballer <micafer1@upv.es>"
LABEL version="0.2"
LABEL description="Container image to AI-Sprint design & TOSCARIZER tools."

# Install docker
RUN apt-get update && \
    apt-get install -y ca-certificates curl gnupg lsb-release && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt update && apt install  docker-ce-cli -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && rm -rf ~/.cache/


# Install AI-Sprint Design:
RUN git clone https://gitlab.polimi.it/ai-sprint/ai-sprint-design.git && \
    cd ai-sprint-design && \
    pip install --no-cache-dir -r docker/requirements.txt && \
    pip install --no-cache-dir -r docker/requirements-oscarp.txt && \
    pip install --no-cache-dir -r docker/requirements-space4ai.txt && \
    pip install . && \
    cd ..  && \
    rm -rf ai-sprint-design

# Install AI-Sprint Toscarizer:
RUN git clone https://gitlab.polimi.it/ai-sprint/toscarizer.git && \
    cd toscarizer && \
    pip install . && \
    cd ..  && \
    rm -rf toscarizer
