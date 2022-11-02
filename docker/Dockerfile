FROM python:3.8
LABEL maintainer="Miguel Caballer <micafer1@upv.es>"
LABEL version="0.2"
LABEL description="Container image to AI-Sprint design & TOSCARIZER tools."

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
