#!/bin/bash
# Copyright (C) 2023 Marcin Owsiany <marcin@owsiany.pl>
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
set -euo pipefail
subdir="$1"
shift
export AUTOPKGTEST_ARTIFACTS="$(pwd)/artifacts/${subdir}"
mkdir -p "${AUTOPKGTEST_ARTIFACTS}"
exec xvfb-run \
    -e "${AUTOPKGTEST_ARTIFACTS}/xvfb-run.stderr" \
    -s "-screen 0 1024x768x24 -fbdir ${AUTOPKGTEST_TMP}" \
    ./test_e2e.py "$@"
