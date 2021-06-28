import subprocess


def test_flake8():
    proc = subprocess.run(["flake8", "girder_imagedephi", "tests"], capture_output=True)
    code = proc.returncode
    out = "\n" + str(proc.stdout, "utf-8")
    assert code == 0, out


def test_mypy():
    proc = subprocess.run(["mypy", "-p", "girder_imagedephi"], capture_output=True)
    code = proc.returncode
    out = "\n" + str(proc.stdout, "utf-8")
    assert code == 0, out
