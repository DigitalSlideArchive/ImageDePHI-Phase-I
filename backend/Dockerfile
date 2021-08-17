FROM python:3.8-slim as girder
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    MONGO_DATABASE=mongodb://example.com:27017/girder
WORKDIR /code
RUN apt-get update \
    && apt-get install --no-install-recommends -y nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock /code/
RUN poetry install --no-root --no-dev
RUN poetry run girder build
COPY girder_imagedephi/ /code/girder_imagedephi/
RUN poetry install --no-dev
EXPOSE 8080
CMD poetry run girder serve --host 0.0.0.0 --database $MONGO_DATABASE

FROM girder AS worker
RUN poetry install --no-dev -E worker -E bin
CMD poetry run girder serve --host 0.0.0.0 --database $MONGO_DATABASE

FROM worker AS test
RUN poetry install
COPY .flake8 pyproject.toml /code/
COPY tests/ /code/tests/
CMD poetry run pytest --mongo-uri $MONGO_DATABASE
