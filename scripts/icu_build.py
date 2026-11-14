"""Pinned ICU source lists and host-side Unicode data generation."""

import hashlib
import json
import os
import re
import subprocess
from darwin_build import ROOT


def source_files(directory):
    names = []
    for name in ("Makefile.in", "Makefile.local"):
        contents = (directory / name).read_text().replace("\\\n", " ")
        for line in contents.splitlines():
            if re.match(r"\s*OBJECTS\s*\+?=", line):
                names.extend(re.findall(r"\b([a-zA-Z0-9_]+)\.o\b", line))
    if not names:
        raise ValueError("ICU source list is empty: " + str(directory))
    sources = []
    for name in dict.fromkeys(names):
        paths = [directory / (name + suffix) for suffix in (".c", ".cpp")]
        paths = [path for path in paths if path.is_file()]
        if len(paths) != 1:
            raise ValueError("ambiguous ICU source: " + str(directory / name))
        sources.extend(paths)
    return sources


def build_host_data(source):
    directory = ROOT / "build/icu-host"
    directory.mkdir(parents=True, exist_ok=True)
    options = [
        "--prefix=" + str(directory / "install"),
        "--disable-tests",
        "--disable-samples",
        "--disable-layout",
        "--disable-layoutex",
        "--disable-icuio",
        "--disable-extras",
        "--with-data-packaging=archive",
    ]
    environment = {
        **os.environ,
        "CFLAGS": "-O2 -fPIC",
        "CXXFLAGS": "-O2 -fPIC -std=gnu++11",
    }
    signature = hashlib.sha256((source / ".commonplace-patches.sha256").read_bytes())
    signature.update(json.dumps(options).encode())
    for name in ("CC", "CXX", "CFLAGS", "CXXFLAGS"):
        signature.update(environment.get(name, "").encode())
    stamp = directory / ".commonplace-data.sha256"
    data = directory / "data/out/icudt55l.dat"
    if not (
        stamp.exists() and stamp.read_text() == signature.hexdigest() and data.is_file()
    ):
        subprocess.run(
            ["bash", str(source / "configure"), *options],
            cwd=directory,
            env=environment,
            check=True,
        )
        subprocess.run(["make", "-j2"], cwd=directory, env=environment, check=True)
        if not data.is_file():
            raise ValueError("ICU did not generate its Unicode data archive")
        stamp.write_text(signature.hexdigest())
    return data
