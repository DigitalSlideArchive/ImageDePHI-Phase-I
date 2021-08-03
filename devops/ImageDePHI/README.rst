=============================
ImageDePHI via Docker Compose
=============================

This directory contains a docker-compose set up for the ImageDePHI project.

Database files and local assetstore files are stored in local directories.

Prerequsities:
--------------

Before using this, you need both Docker and docker-compose.  See the `official installation instructions <https://docs.docker.com/compose/install>`_.

Start
-----

To start the program::

    docker-compose up

This adds some sample files, creates custom directories for redaction, and otherwise has the defaults for the Digital Slide Archive.  By default, it creates an ``admin`` user with a password of ``password``.


