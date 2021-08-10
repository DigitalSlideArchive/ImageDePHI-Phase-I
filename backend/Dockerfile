FROM python:3 as builder
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY pyproject.toml \
    setup.py \
    setup.cfg \
    /code/
COPY girder_imagedephi /code/girder_imagedephi/
RUN pip wheel --no-deps -w /code/wheels/ .

FROM python:3 as environment
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt
COPY --from=builder /code/wheels/ /tmp/wheels/
RUN pip install /tmp/wheels/* && rm -rf /tmp/wheels

FROM environment AS tests
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY --from=builder /code/ /code/
RUN pip install ".[test]"
COPY tests /code/tests/
CMD pytest tests

FROM environment
ENV PYTHONUNBUFFERED=1
ENV MONGO_DATABASE=mongodb://example.com:27017/girder
EXPOSE 8080
CMD girder serve --host 0.0.0.0 --database $MONGO_DATABASE
