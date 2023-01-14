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

import logging
import os
import random
import re
import subprocess
import time


_COLOR_PATTERN = re.compile(r'(\d+),(\d+),(\d+)')
_EXIT_SECONDS = 5
_BAMBAM_PROGRAM = os.getenv('AUTOPKGTEST_BAMBAM_PROGRAM', '/usr/games/bambam')


def main():
    bambam = subprocess.Popen([_BAMBAM_PROGRAM])
    try:
        await_welcome_screen()
        send_keycodes('space')  # any keypress should do
        await_blank_screen()
        test_functionality()
        shut_bambam_down()
        logging.info('Waiting for game to exit cleanly.')
        exit_code = bambam.wait(timeout=_EXIT_SECONDS)
        if exit_code != 0:
            raise Exception('Bambam exited with unexpected code %d.' % exit_code)
        logging.info('Test successful.')
    except:  # noqa: E722
        take_screenshot('exception')
        raise


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
        time.sleep(0.005)  # let the event propagate and bambam process it
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


def take_screenshot(title):
    file_name = os.path.join(os.environ['AUTOPKGTEST_ARTIFACTS'], '%s.png' % title)
    subprocess.call([
        'convert',
        'xwd:' + os.path.join(os.environ['AUTOPKGTEST_TMP'], 'Xvfb_screen0'),
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
        'xwd:' + os.path.join(os.environ['AUTOPKGTEST_TMP'], 'Xvfb_screen0'),
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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    main()
