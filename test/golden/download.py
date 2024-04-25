#!/usr/bin/python3
# Download golden files from GitHub Actions artifact storage.
#
# Copyright (C) 2024 Marcin Owsiany <marcin@owsiany.pl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import glob
import os
import shutil
import subprocess
import sys
import yaml

os.chdir(os.path.dirname(sys.argv[0]))
subprocess.check_call(["gh", "run", "download"] + sys.argv[1:])

with open("../../.github/workflows/python-app.yml") as workflow_file:
    workflow = yaml.full_load(workflow_file)
    matrix = workflow["jobs"]["e2e"]["strategy"]["matrix"]
    python_versions = matrix["python-version"]
    extensions = matrix["extension"]
    steps = workflow["jobs"]["e2e"]["steps"]
    tests = [s["run"].split(" ")[1] for s in steps if "run" in s and s["run"].startswith("./run_e2e_test.sh")]

for python_version in python_versions:
    for extension in extensions:
        for test in tests:
            src = f"test-golden-{python_version}-{extension}/{python_version}/{extension}/{test}"
            dest = f"{python_version}/{extension}/{test}"
            subprocess.check_call(["pngcrush", "-d", dest] + glob.glob(f"{src}/*.png"))

for d in glob.glob("test-golden-*"):
    shutil.rmtree(d)
