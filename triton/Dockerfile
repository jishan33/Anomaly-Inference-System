FROM nvcr.io/nvidia/tritonserver:24.05-py3

RUN pip3 install --no-cache-dir --upgrade \
    scikit-learn==1.7.2 \
    joblib \
    numpy==1.26.4

CMD ["tritonserver", "--model-repository=/models"]