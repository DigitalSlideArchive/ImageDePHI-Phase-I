Launch services:
```bash
$ docker compose up -d
```

Make girder virtual environment:
```bash
$ cd backend
$ poetry install --extras worker --extras bin
$ poetry run girder build --dev
```

Run girder server:
```bash
$ poetry run girder serve --dev
```

Run girder tests:
```bash
poetry run pytest
```
