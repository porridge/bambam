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
"""Checks whether bambam works.

This is intended to be run by autopkgtest, with the environment set up to
connect to an Xvfb server in order to take screenshots from its XWD output
file.

See the main() function for a high-level overview of what the script does.
"""

import argparse
import io
import logging
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time


_COLOR_PATTERN = re.compile(r'(\d+),(\d+),(\d+)')
_EXIT_SECONDS = 5
_BAMBAM_PROGRAM = os.getenv('AUTOPKGTEST_BAMBAM_PROGRAM', '/usr/games/bambam')
_ARTIFACTS_DIR = os.getenv('AUTOPKGTEST_ARTIFACTS', '.')
_TMP_DIR = os.getenv('AUTOPKGTEST_TMP', tempfile.gettempdir())
_AUDIO_FILE = os.path.join(_TMP_DIR, 'sdlaudio.raw')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-audio-output', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--expect-sounds', action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument('--sdl-audio-driver', default='disk')
    parser.add_argument('bambam_args', nargs='*')
    args = parser.parse_args()

    remove_if_exists(_AUDIO_FILE)
    env = os.environ.copy() | dict(SDL_AUDIODRIVER=args.sdl_audio_driver, SDL_DISKAUDIOFILE=_AUDIO_FILE)
    bambam = subprocess.Popen([_BAMBAM_PROGRAM]+args.bambam_args, env=env, stderr=subprocess.PIPE)
    try:
        checker_builder = check_stream(bambam.stderr, sys.stderr)
        if args.expect_audio_output:
            checker_builder.not_contains_line("Warning, sound disabled.")
        else:
            checker_builder.contains_line("Warning, sound disabled.")
        checker = checker_builder.start()
        await_welcome_screen()
        send_keycodes('space')  # any keypress should do
        await_blank_screen()
        test_functionality()
        shut_bambam_down()
        logging.info('Waiting for game to exit cleanly.')
        exit_code = bambam.wait(timeout=_EXIT_SECONDS)
        if exit_code != 0:
            raise Exception('Bambam exited with unexpected code %d.' % exit_code)
        if not checker.check():
            raise Exception('Unexpected standard error output.')
    except:  # noqa: E722
        take_screenshot('exception')
        raise
    check_audio(args.expect_audio_output, args.expect_sounds)
    logging.info('Test successful.')


def remove_if_exists(file_path: str):
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass


def await_welcome_screen():
    logging.info(
        'Polling to observe a light blue screen (which means that bambam '
        'has started AND is displaying a welcome screen where the text '
        'is blue).')
    attempt_count = 40
    sleep_delay = 0.25
    for attempt in range(attempt_count):
        current_average_hsl = get_average_hsl()
        logging.info('On attempt %d the average screen HSV was %s.', attempt, current_average_hsl)
        h, s, l = current_average_hsl  # noqa: E741
        if 50 < h and h < 70 and 20 < s and s < 40 and 80 < l and l < 100:
            logging.info('Found light blue screen, looks like bambam started up OK.')
            take_screenshot('welcome')
            return
        time.sleep(sleep_delay)
    raise Exception(
        'Failed to see bambam start and display light-blue background, '
        'after polling %d times every %f seconds.' % (attempt_count, sleep_delay))


def await_blank_screen():
    logging.info('Polling to observe a mostly-white screen (which means that welcome screen was cleared).')
    attempt_count = 40
    sleep_delay = 0.25
    for attempt in range(attempt_count):
        current_average_color = get_average_color()
        logging.info('On attempt %d the average screen color was %s.', attempt, current_average_color)
        if all(color_component >= 248 for color_component in current_average_color):
            logging.info('Found mostly white screen, looks like bambam cleared the welcome screen OK.')
            take_screenshot('blank')
            return
        time.sleep(sleep_delay)
    raise Exception(
        'Failed to see bambam clear the startup screen and display mostly-white background, '
        'after polling %d times every %f seconds.' % (attempt_count, sleep_delay))


def test_functionality():
    logging.info('Simulating space and letter keypresses and measuring average screen color, to test functionality.')
    attempt_count = 1000
    for attempt in range(attempt_count):
        send_keycodes('space', 'm')  # any letter will do, but em is nice and big
        send_mouse_move()
        time.sleep(0.25)  # let the event propagate and bambam process it (leave some time for sound to play)
        if is_screen_colorful_enough(attempt):
            take_screenshot('success')
            return
    raise Exception('Failed to see a colorful enough screen after %d key presses.' % (attempt_count * 2))


def is_screen_colorful_enough(attempt):
    r, g, b = get_average_color()
    if any(color > 225 for color in (r, g, b)):
        logging.info('On attempt %d the average screen color was too close to white: %d,%d,%d.', attempt, r, g, b)
        return False
    else:
        logging.info('Found colorful enough screen, colors %d, %d, %d.', r, g, b)
        return True


def shut_bambam_down():
    logging.info('Simulating shutdown keypresses.')
    send_keycodes('q', 'u', 'i', 't')


def check_audio(assert_audio_output_exists=True, assert_contains_sounds=True):
    if assert_audio_output_exists:
        logging.info('Checking that audio output was created.')
        if not os.path.exists(_AUDIO_FILE):
            raise Exception('Output audio file %s not found.' % _AUDIO_FILE)
    else:
        logging.info('Checking that audio output was NOT created.')
        if os.path.exists(_AUDIO_FILE):
            raise Exception('Output audio file %s was unexpectedly found.' % _AUDIO_FILE)
        return

    logging.info('Checking that emitted audio %s sounds.' % (
        'contains' if assert_contains_sounds else 'does NOT contain'))
    # Create WAV file as an artifact, as it is easier to handle thanks to embedded metadata.
    audio_artifact = os.path.join(_ARTIFACTS_DIR, 'audio.wav')
    remove_if_exists(audio_artifact)
    # Audio parameters based on pygame.mixer.init() defaults:
    # https://www.pygame.org/docs/ref/mixer.html#pygame.mixer.init
    subprocess.check_call([
        'sox', '-r', '44.1k', '-e', 'signed', '-b', '16', '-c', '2',
        _AUDIO_FILE, audio_artifact
    ])
    # Remove silence anywhere in the file:
    trimmed_audio = os.path.join(_TMP_DIR, 'trimmed.raw')
    remove_if_exists(trimmed_audio)
    subprocess.check_call([
        'sox', audio_artifact, trimmed_audio,
        'silence', '1', '0', '0%', '-1', '0', '0%',
    ])
    size = os.stat(trimmed_audio).st_size
    if assert_contains_sounds and size < 100000:
        raise Exception('Audio file unexpectedly small after trimming silence: %d bytes' % size)
    elif not assert_contains_sounds and size > 0:
        raise Exception('Audio file is not empty after trimming silence: %d bytes' % size)


def take_screenshot(title):
    file_name = os.path.join(_ARTIFACTS_DIR, '%s.png' % title)
    subprocess.call([
        'convert',
        'xwd:' + os.path.join(_TMP_DIR, 'Xvfb_screen0'),
        file_name])
    logging.info('Took a screenshot to: %s', file_name)


def get_average_color():
    return summarize_screen('r*255', 'g*255', 'b*255')


def get_average_hsl():
    return summarize_screen('hue*100', 'saturation*100', 'lightness*100')


def summarize_screen(*fx_expressions):
    if len(fx_expressions) != 3:
        raise Exception('Expected three FX expressions, got %s' % fx_expressions)
    format_arg = ','.join(('%%[fx:int(%s)]' % e) for e in fx_expressions)
    color_str = subprocess.check_output([
        'convert',
        'xwd:' + os.path.join(_TMP_DIR, 'Xvfb_screen0'),
        '-resize', '1x1!',
        '-format', format_arg,
        'info:-']).decode()
    m = _COLOR_PATTERN.match(color_str)
    if not m:
        raise Exception('Failed to parse color ' + color_str)
    return [int(i) for i in m.group(1, 2, 3)]


def xdotool(*args):
    subprocess.check_call(['xdotool', 'search', '--class', 'bambam'] + list(args))


def send_keycodes(*keycodes):
    xdotool('key', *keycodes)


def random_move():
    return random.choice(['+', '-']) + str(random.choice(range(1, 50)))


def send_mouse_move():
    x, y = random_move(), random_move()
    xdotool('mousedown', '1', 'mousemove_relative', '--', x, y, 'mouseup', '1')


class StreamChecker:
    def __init__(self, input_stream: io.IOBase, output_stream: io.IOBase, checks, negative_checks) -> None:
        self._input_stream = input_stream
        self._output_stream = output_stream
        self._checks = list(checks)
        self._negative_checks = list(negative_checks)
        self._result = False if self._checks else True
        self._thread = threading.Thread(target=self._ingest, name='StreamChecker for %s' % input_stream)
        self._thread.start()

    def _ingest(self):
        while True:
            line = self._input_stream.readline()
            if not line:
                return
            print(line.decode(), end='', flush=True, file=self._output_stream)
            line = line.rstrip()
            for check in self._checks:
                if line == check:
                    self._result = True

            for check in self._negative_checks:
                if line == check:
                    self._result = False

    def check(self):
        self._thread.join()
        return self._result


class _StreamCheckerBuilder:
    def __init__(self, input_stream: io.IOBase, output_stream: io.IOBase) -> None:
        self._input_stream = input_stream
        self._output_stream = output_stream
        self._checks = []
        self._negative_checks = []

    def contains_line(self, line: str):
        if self._negative_checks:
            raise ValueError('contains_line() must not be used together with not_contains_line()')
        self._checks.append(bytes(line, 'utf-8'))
        return self

    def not_contains_line(self, line: str):
        if self._checks:
            raise ValueError('contains_line() must not be used together with not_contains_line()')
        self._negative_checks.append(bytes(line, 'utf-8'))
        return self

    def start(self) -> StreamChecker:
        checker = StreamChecker(self._input_stream, self._output_stream, self._checks, self._negative_checks)
        return checker


def check_stream(input: io.IOBase, output: io.IOBase) -> _StreamCheckerBuilder:
    return _StreamCheckerBuilder(input, output)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    main()
