## Setup

Install Vips

``` bash
$ sudo apt installed libtiff-dev
$ sudo apt install libvips libvips-dev libvips-tools
```

Virtual environment

```bash
$ python -m venv venv
$ source venv/bin/activate
```

Install packages

```bash
(venv) $ pip install --upgrade pip
(venv) $ pip install wheel
(venv) $ pip install tifftools pyvips
```

Copy Vips header to environment

```bash
(venv) $ cp /usr/include/x86_64-linux-gnu/tiff.h venv/include/
```