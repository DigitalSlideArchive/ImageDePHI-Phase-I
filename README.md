Launch mongo:
```bash
docker run \
    --name imagedephi-mongo \
    --env MONGO_INITDB_DATABASE=girder \
    -p 27017:27017 \
    -d \
    mongo:3.4
```

Make girder virtual environment:
```bash
$ cd backend
$ python3 -m venv .venv
$ source .venv/bin/activate
```

Install girder requirements:
```bash
$ cd backend
$ pip install -e '.[test]' --find-links https://girder.github.io/large_image_wheels
```

Build girder files:
```bash
$ cd backend
$ girder build --dev
```

Run girder server:
```bash
$ girder serve --dev
```

Run girder tests:
```bash
pytest
```
