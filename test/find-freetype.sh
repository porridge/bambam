#!/bin/bash
# Copyright 2023 Marcin Owsiany <marcin@owsiany.pl>
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
mode="$1"
shift
pygame_file="$(env python3 -c "import pygame; print(pygame.__file__)" | grep -Ev "^(Hello from the |pygame [0-9]+)")"
pygame_dir="$(dirname "${pygame_file}")"
base_dir="$(dirname "${pygame_dir}")"
echo "Looking for freetype shared library under ${base_dir}..." >&2
done=0
for path in $(find "${base_dir}" -iname "libfreetype*.so.6*" -print)
do
    echo "Found ${path}" >&2
    case "${mode}" in
    echo)
        echo "${path}"
        ;;
    rm-and-run)
        echo "Deleting ${path}" >&2
        rm "${path}"
        ;;
    *)
        echo "Unrecognized mode ${mode}" >&2
        exit 1
    esac
    done=1
done
if ! (( done ))
then
    echo "Did not find freetype library under ${base_dir}, exiting..." >&2
    exit 1
fi
if [[ $mode = rm-and-run ]]
then
    exec "$@"
fi
