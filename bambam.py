#!/usr/bin/env python
# Copyright (C)
#    2007-2008 Don Brown,
#    2010 Spike Burch <spikeb@gmail.com>,
#    2015-2016 Vasya Novikov
#    2018 Olivier Mehani <shtrom+bambam@ssji.net>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import pygame
import sys
import os
import random
import string
import glob
import argparse
import fnmatch
from pygame.locals import Color, RLEACCEL, QUIT, KEYDOWN, MOUSEMOTION, MOUSEBUTTONDOWN, MOUSEBUTTONUP


class Bambam:
    IMAGE_MAX_WIDTH = 700

    args = None
    progInstallBase = None

    colors = None
    images = None
    sounds = None

    background = None
    screen = None
    sheight = None
    swidth = None

    mouse_down = None
    sequence = None
    sound_muted = None

    @classmethod
    def get_color(cls):
        """
        Return bright color varying over time.
        """
        col = Color('white')

        hue = pygame.time.get_ticks() / 50 % 360
        col.hsva = (hue, 100, 100, 50)

        return Color(col.r, col.g, col.b)

    @classmethod
    def load_image(cls, fullname, colorkey=None):
        """
        Load image/, handling setting of the transparency color key.
        """
        try:
            image = pygame.image.load(fullname)

            sz_x, sz_y = image.get_rect().size
            if (sz_x > cls.IMAGE_MAX_WIDTH or sz_y > cls.IMAGE_MAX_WIDTH):
                new_size = (cls.IMAGE_MAX_WIDTH, int(cls.IMAGE_MAX_WIDTH * (float(sz_y)/sz_x)))
                if new_size[1] < 1:
                    print("Image has 0 size:", fullname)
                    raise SystemExit(message)

                image = pygame.transform.scale(image, new_size)

        except pygame.error as message:
            print("Cannot load image:", fullname)
            raise SystemExit(message)

        image = image.convert()
        if colorkey is not None:
            if colorkey is -1:
                colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, RLEACCEL)
        return image

    @classmethod
    def load_sound(cls, name):
        """
        Load sound file in "data/".
        """
        class NoneSound:
            def play(self): pass
        if not pygame.mixer:
            return NoneSound()
        try:
            sound = pygame.mixer.Sound(name)
        except pygame.error as message:
            print("Cannot load sound:", name)
            raise SystemExit(message)
        return sound

    @classmethod
    def load_items(cls, lst, blacklist, load_function):
        """
        Runs load_function on elements of lst unless they are blacklisted.
        """
        result = []
        for name in lst:
            if True in [fnmatch.fnmatch(name, p) for p in blacklist]:
                print("Skipping blacklisted item:", name)
            else:
                result.append(load_function(name))
        return result

    @classmethod
    def is_latin(cls, key):
        """
        Is the key that was pressed alphanumeric.
        """
        return (key < 255
                and (chr(key) in string.ascii_letters
                     or chr(key) in string.digits))

    def draw_dot(self):
        """
        draw filled circle at mouse position.
        """
        r = 30
        mousex, mousey = pygame.mouse.get_pos()

        dot = pygame.Surface((2 * r, 2 * r))
        pygame.draw.circle(dot, self.get_color(), (r, r), r, 0)
        dot.set_colorkey(0, pygame.RLEACCEL)

        self.screen.blit(dot, (mousex - r, mousey - r))

    def input(self, events, quit_pos):
        """
        Processes events.
        """
        for event in events:
            if event.type == QUIT:
                sys.exit(0)

            # handle keydown event
            elif event.type == KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                # check for words like quit
                if event.type == KEYDOWN:
                    if self.is_latin(event.key):
                        self.sequence += chr(event.key)
                        if self.sequence.find('quit') > -1:
                            sys.exit(0)
                        elif self.sequence.find('unmute') > -1:
                            self.sound_muted = False
                            # pygame.mixer.unpause()
                            self.sequence = ''
                        elif self.sequence.find('mute') > -1:
                            self.sound_muted = True
                            pygame.mixer.fadeout(1000)
                            self.sequence = ''

                # Clear the self.background 10% of the time
                if random.randint(0, 10) == 1:
                    self.screen.blit(self.background, (0, 0))
                    pygame.display.flip()

                # play random sound
                if not self.sound_muted:
                    if event.type == KEYDOWN and self.args.deterministic_sounds:
                        self.sounds[event.key % len(self.sounds)].play()
                    else:
                        self.sounds[random.randint(
                            0, len(self.sounds) - 1)].play()

                # show self.images
                if event.type == pygame.KEYDOWN and (event.unicode.isalpha() or event.unicode.isdigit()):
                    self.print_letter(event.unicode)
                else:
                    self.print_image()
                pygame.display.flip()

            # mouse motion
            elif event.type == MOUSEMOTION:
                if self.mouse_down:
                    self.draw_dot()
                    pygame.display.flip()

            # mouse button down
            elif event.type == MOUSEBUTTONDOWN:
                self.draw_dot()
                self.mouse_down = True
                pygame.display.flip()

            # mouse button up
            elif event.type == MOUSEBUTTONUP:
                self.mouse_down = False

        return quit_pos

    def print_image(self):
        """
        Prints an image at a random location.
        """
        img = self.images[random.randint(0, len(self.images) - 1)]
        w = random.randint(0, self.swidth - img.get_width())
        h = random.randint(0, self.sheight - img.get_height())
        self.screen.blit(img, (w, h))

    def print_letter(self, char):
        """
        Prints a letter at a random location.
        """
        font = pygame.font.Font(None, 256)
        if self.args.uppercase:
            char = char.upper()
        text = font.render(
            char, 1, self.colors[random.randint(0, len(self.colors) - 1)])
        textpos = text.get_rect()
        center = (textpos.width // 2, textpos.height // 2)
        w = random.randint(0 + center[0], self.swidth - center[0])
        h = random.randint(0 + center[1], self.sheight - center[1])
        textpos.centerx = w
        textpos.centery = h
        self.screen.blit(text, textpos)

    def glob_dir(self, path, pattern):
        files = glob.glob(os.path.join(path, pattern))
        dirs = [x for x in glob.glob(os.path.join(path, '*')) if os.path.isdir(x)]
        for subdir in dirs:
            files.extend(self.glob_dir(subdir, pattern))
        return files

    def glob_data(self, patterns):
        fileList = []
        for dataDir in self.dataDirs:
            for pattern in patterns:
                fileList.extend(self.glob_dir(dataDir, pattern))
        return fileList

    def run(self):
        """
        Main application entry point.
        """
        self.progInstallBase = os.path.dirname(os.path.realpath(sys.argv[0]))

        self.dataDirs = [os.path.join(self.progInstallBase, 'data')]
        xdg_data_home = os.getenv('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        extraDataDir = os.path.join(xdg_data_home, 'bambam/data')
        if os.path.isdir(extraDataDir):
            print('Extra data dir:', extraDataDir)
            self.dataDirs.append(extraDataDir)

        parser = argparse.ArgumentParser(
            description='A keyboard mashing game for babies.')
        parser.add_argument('-u', '--uppercase', action='store_true',
                            help='Whether to show UPPER-CASE letters.')
        parser.add_argument('--sound_blacklist', action='append', default=[],
                            help='List of sound filename patterns to never play.')
        parser.add_argument('--image_blacklist', action='append', default=[],
                            help='List of image filename patterns to never show.')
        parser.add_argument('-d', '--deterministic-sounds', action='store_true',
                            help='Whether to produce same sounds on same key presses.')
        parser.add_argument('-D', '--dark', action='store_true',
                            help='Use a dark background instead of a light one.')
        parser.add_argument('-m', '--mute', action='store_true',
                            help='No sound will be played.')
        self.args = parser.parse_args()

        if not pygame.font:
            print('Warning, fonts disabled')
        if not pygame.mixer:
            print('Warning, sound disabled')

        pygame.init()

        # swith to full self.screen at current self.screen resolution
        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

        # determine display resolution
        displayinfo = pygame.display.Info()
        self.swidth = displayinfo.current_w
        self.sheight = displayinfo.current_h

        pygame.display.set_caption('Bam Bam')
        self.screen = pygame.display.get_surface()

        self.background = pygame.Surface(self.screen.get_size())
        self.background = self.background.convert()
        if self.args.dark:
            self.background.fill((0, 0, 0))
        else:
            self.background.fill((250, 250, 250))
        captionFont = pygame.font.SysFont(None, 20)
        captionLabel = captionFont.render(
            "Commands: quit, mute, unmute",
            True,
            (210, 210, 210),
            (250, 250, 250))
        captionRect = captionLabel.get_rect()
        captionRect.x = 15
        captionRect.y = 10
        self.background.blit(captionLabel, captionRect)
        self.sequence = ""
        self.screen.blit(self.background, (0, 0))
        pygame.display.flip()

        self.mouse_down = False
        self.sound_muted = self.args.mute

        self.sounds = self.load_items(self.glob_data(
            ['*.wav']), self.args.sound_blacklist, self.load_sound)

        self.colors = ((0,   0, 255), (255,   0,   0), (255, 255,   0),
                       (255,   0, 128), (0,   0, 128), (0, 255,   0),
                       (255, 128,   0), (255,   0, 255), (0, 255, 255)
                       )

        imgs = self.glob_data(['*.gif', '*.jpg'])
        self.images = self.load_items(imgs, self.args.image_blacklist, self.load_image)

        quit_pos = 0

        clock = pygame.time.Clock()

        pygame.joystick.init()

        # Initialize all joysticks
        joystick_count = pygame.joystick.get_count()
        for i in range(joystick_count):
            joystick = pygame.joystick.Joystick(i)
            joystick.init()

        while True:
            clock.tick(60)
            quit_pos = self.input(pygame.event.get(), quit_pos)


if __name__ == '__main__':
    bambam = Bambam()
    bambam.run()
