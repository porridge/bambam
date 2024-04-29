#!/usr/bin/env python3
# Copyright (C) 2018-2023 Marcin Owsiany <marcin@owsiany.pl>
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
"""Tests for test_e2e.py"""

import subprocess
import tempfile
import unittest


import test_e2e


class TestStreamChecker(unittest.TestCase):

    def test_string_emitted_true(self):
        with subprocess.Popen("echo peekaboo", stdout=subprocess.PIPE, shell=True) as p, \
                tempfile.TemporaryFile(mode="w+") as t:
            checker = test_e2e.check_stream(p.stdout, t).contains_line("peekaboo").start()
            self.assertEqual(p.wait(), 0)
            self.assertTrue(checker.check())
            t.seek(0, 0)
            self.assertEqual(t.read(), "peekaboo\n")

    def test_string_emitted_false(self):
        with subprocess.Popen("sleep 0.01; echo boom", stdout=subprocess.PIPE, shell=True) as p, \
                tempfile.TemporaryFile(mode="w+") as t:
            checker = test_e2e.check_stream(p.stdout, t).contains_line("peekaboo").start()
            self.assertEqual(p.wait(), 0)
            self.assertFalse(checker.check())
            t.seek(0, 0)
            self.assertEqual(t.read(), "boom\n")

    def test_string_not_emitted_true(self):
        with subprocess.Popen("echo peekaboo", stdout=subprocess.PIPE, shell=True) as p, \
                tempfile.TemporaryFile(mode="w+") as t:
            checker = test_e2e.check_stream(p.stdout, t).not_contains_line("boom").start()
            self.assertEqual(p.wait(), 0)
            self.assertTrue(checker.check())
            t.seek(0, 0)
            self.assertEqual(t.read(), "peekaboo\n")

    def test_string_not_emitted_false(self):
        with subprocess.Popen("sleep 0.01; echo boom", stdout=subprocess.PIPE, shell=True) as p, \
                tempfile.TemporaryFile(mode="w+") as t:
            checker = test_e2e.check_stream(p.stdout, t).not_contains_line("boom").start()
            self.assertEqual(p.wait(), 0)
            self.assertFalse(checker.check())
            t.seek(0, 0)
            self.assertEqual(t.read(), "boom\n")


if __name__ == "__main__":
    unittest.main()
