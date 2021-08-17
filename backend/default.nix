with import (fetchTarball https://github.com/NixOS/nixpkgs/archive/nixos-21.05.tar.gz) { };

let
  girderDependencies = rec {
    amqp = py.buildPythonPackage rec {
      pname = "amqp";
      version = "2.6.1";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "70cdb10628468ff14e57ec2f751c7aa9e48e7e3651cfd62d431213c0c4e58f21";
      };
      propagatedBuildInputs = [ vine ];
      disabledTests = [ "test_rmq.py" ];
      doCheck = false;
    };
    vine = py.buildPythonPackage rec {
      pname = "vine";
      version = "1.3.0";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "133ee6d7a9016f177ddeaf191c1f58421a1dcc6ee9a42c58b34bed40e1d2cd87";
      };
      nativeBuildInputs = [ py.case py.pytest ];
      doCheck = false;
    };
    kombu = py.buildPythonPackage rec {
      pname = "kombu";
      version = "4.6.11";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "ca1b45faac8c0b18493d02a8571792f3c40291cf2bcf1f55afed3d8f3aa7ba74";
      };
      postPatch = ''
        substituteInPlace requirements/test.txt \
          --replace "pytest-sugar" ""
        substituteInPlace requirements/default.txt \
          --replace "amqp==2.5.1" "amqp~=2.6"
      '';
      propagatedBuildInputs = [
        amqp
      ];
      doCheck = false;
    };
    celery = py.buildPythonPackage rec {
      pname = "celery";
      version = "4.4.7";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "17vg0921v6d429qb5q5g8hc0fmjkg03c10ngk8a7hz6miqxb286j";
      };
      nativeBuildInputs = [ py.setuptools-scm ];
      propagatedBuildInputs = [
        py.billiard
        kombu
        vine
        py.pytz
      ];
      doCheck = false;
    };
    girder = py.buildPythonPackage rec {
      pname = "girder";
      version = "3.1.5";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "16fh9xgsbrg5xpxa1iaw245ihz13fbla74mfh6aqvry22nka1fx5";
      };
      propagatedBuildInputs = [
        py.setuptools-scm
        py.boto3
        py.botocore
        py.botocore
        py.cherrypy
        py.click
        py.click-plugins
        py.dogpile_cache
        py.filelock
        py.jsonschema
        py.Mako
        py.passlib
        py.psutil
        py.pymongo
        py.pyopenssl
        py.python-dateutil
        py.pytz
        py.pyyaml
        py.requests
      ];
      doCheck = false;
    };
    large-image = py.buildPythonPackage rec {
      pname = "large-image";
      version = "1.7.0";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "1hsd7z98kyfa21xdc0n359l7l4k6szx37nw0brhzamfz80j06p87";
      };
      nativeBuildInputs = [ py.setuptools-scm ];
      propagatedBuildInputs = [
        py.pillow-simd
        py.cachetools
        py.numpy
        py.psutil
        py.pylibmc
        py.pyvips
      ];
      doCheck = false;
    };
    girder-jobs = py.buildPythonPackage rec {
      pname = "girder-jobs";
      version = "3.1.5";
      nativeBuildInputs = [ py.setuptools-scm py.setuptools-git ];
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "1m55a57k5757cp7ql4vmrv3ibqsb4d1c5gg21i6s9bvn75accb2a";
      };
      propagatedBuildInputs = [
        girder
      ];
      doCheck = false;
    };
    girder-client = py.buildPythonPackage rec {
      pname = "girder-client";
      version = "3.1.5";
      nativeBuildInputs = [ py.setuptools-scm ];
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "0hn39l63nw4p9lci02llrksaizw2ybnm3d8lqc8climvjxjzpkn1";
      };
      propagatedBuildInputs = [
        py.click
        py.diskcache
        py.requests
        py.requests_toolbelt
      ];
      doCheck = false;
    };
    girder-worker = py.buildPythonPackage rec {
      pname = "girder-worker";
      version = "0.8.1";
      nativeBuildInputs = [ py.setuptools-scm ];
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "0cahz8wlmlpnx2vvkwmsxy5b1skmkff6x5vaccqkr5c39p9izz9r";
      };
      propagatedBuildInputs = [
        celery
        girder-client
        girder-worker-utils
        py.docker
        py.jinja2
        py.jsonpickle
        py.pymongo
        py.pyopenssl
        py.pyyaml
        py.stevedore
        py.urllib3
      ];
      doCheck = false;
    };
    girder-worker-utils = py.buildPythonPackage rec {
      pname = "girder-worker-utils";
      version = "0.8.6";
      nativeBuildInputs = [ py.setuptools-scm ];
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "1z91xav47bx9xr74vhnfy9dwdxqv500mr17r1i6c0b1wwkknmpri";
      };
      propagatedBuildInputs = [
        girder-client
        py.jsonpickle
        py.requests
        py.six
        py.urllib3
      ];
      doCheck = false;
    };
    girder-large-image = py.buildPythonPackage rec {
      pname = "girder-large-image";
      version = "1.7.0";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "0irnkz7q6llgr8vvgs7gylj3l2swq8zdrcj69g7f4lxp086garkc";
      };
      nativeBuildInputs = [ py.setuptools-scm py.setuptools-git ];
      propagatedBuildInputs = [
        girder
        girder-jobs
        girder-worker
        large-image
        py.enum34
      ];
      doCheck = false;
    };
    girder-large-image-annotation = py.buildPythonPackage rec {
      pname = "girder-large-image-annotation";
      version = "1.7.0";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "1g34n057y1ll5d0rszg2dlf9xrqanf0nanwflbnch6lxypwz7gpr";
      };
      nativeBuildInputs = [ py.setuptools-scm py.setuptools-git ];
      propagatedBuildInputs = [
        girder-large-image
        py.jsonschema
        py.ujson
      ];
      doCheck = false;
    };
    sentinels = py.buildPythonPackage rec {
      pname = "sentinels";
      version = "1.0.0";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "7be0704d7fe1925e397e92d18669ace2f619c92b5d4eb21a89f31e026f9ff4b1";
      };
      propagatedBuildInputs = [
      ];
      doCheck = false;
    };
    mongomock = py.buildPythonPackage rec {
      pname = "mongomock";
      version = "3.23.0";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "1pdh4pj5n6dsaqy98q40wig5y6imfs1p043cgkaaw8f2hxy5x56r";
      };
      nativeBuildInputs = [ py.pbr ];
      propagatedBuildInputs = [
        py.six
        sentinels
      ];
      doCheck = false;
    };
    pytest-girder = py.buildPythonPackage rec {
      pname = "pytest-girder";
      version = "3.1.5";
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "8a3865dea3986bea24cd92c38417401803c6826b55f782b7013c36c7aeb0d5d1";
      };
      propagatedBuildInputs = [
        girder
        mongomock
        py.pytest
        py.pytest-cov
        py.pymongo
      ];
      doCheck = false;
    };
    tifftools = py.buildPythonPackage rec {
      pname = "tifftools";
      version = "1.2.6";
      nativeBuildInputs = [ py.setuptools-scm ];
      src = py.fetchPypi {
        inherit pname version;
        sha256 = "48d28869e85dceacc598c2459d7293fe2ef31f2098fd97c2cf88c76048afec78";
        extension = "zip";
      };
      doCheck = false;
    };
  };
  py = pkgs.python38Packages.override {
    overrides = self: super: girderDependencies;
  };
in
py.buildPythonPackage rec {
  name = "girder-imagedephi";
  version = "0.0.0";
  src = ./.;
  propagatedBuildInputs = [
    py.pkgconfig
    py.girder
    py.girder-large-image
    py.girder-large-image-annotation
    py.large-image
    py.tifftools
    py.pyvips
  ];
  nativeBuildInputs = [ py.setuptools-scm ];
  checkInputs = [
    py.pytestCheckHook
    py.mongomock
    py.black
    py.pytest-girder
    py.flake8
    py.isort
    py.mypy
    py.pytest
    py.pytest-sugar
    py.pep8-naming
  ];
  checkPhase = ''
    pytest tests/
  '';
  doCheck = true;
  editable = pkgs.lib.inNixShell;
}
