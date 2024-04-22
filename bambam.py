#!/usr/bin/env python3
# Copyright (C)
#    2007-2008 Don Brown,
#    2010 Spike Burch <spikeb@gmail.com>,
#    2015-2016 Vasya Novikov
#    2018 Olivier Mehani <shtrom+bambam@ssji.net>
#    2018-2024 Marcin Owsiany <marcin@owsiany.pl>
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

import argparse
import fnmatch
import gettext
import logging
import math
import os
import pygame
from pygame.locals import Color, QUIT, KEYDOWN, MOUSEMOTION, MOUSEBUTTONDOWN, MOUSEBUTTONUP
import random
import sys
from textwrap import fill

try:
    import yaml
    _YAML_LOADED = True
except ImportError:
    _YAML_LOADED = False


# noinspection PyPep8Naming
def N_(s): return s


# TRANSLATORS: command string to mute sounds.
# Must not contain spaces, and should be be at least 4 characters long,
# so that it is unlikely to be generated by a keyboard-mashing baby.
# However it is recommended to keep it shorter than 10 characters so that
# it is relatively easy to type by an adult without making mistakes.
MUTE_STRING = N_('mute')
# TRANSLATORS: command string to unmute sounds.
# Must not contain spaces, and should be be at least 4 characters long,
# so that it is unlikely to be generated by a keyboard-mashing baby.
# However it is recommended to keep it shorter than 10 characters so that
# it is relatively easy to type by an adult without making mistakes.
UNMUTE_STRING = N_('unmute')
# TRANSLATORS: command string to quit the game.
# Must not contain spaces, and should be be at least 4 characters long,
# so that it is unlikely to be generated by a keyboard-mashing baby.
# However it is recommended to keep it shorter than 10 characters so that
# it is relatively easy to type by an adult without making mistakes.
QUIT_STRING = N_('quit')


class BambamException(Exception):
    """Represents a bambam-specific exception."""
    pass


class ResourceLoadException(BambamException):
    """Represents a failure to load a resource."""

    def __init__(self, resource, message):
        self._resource = resource
        self._message = message

    def __str__(self):
        return _('Failed to load file "%(file)s": %(message)s') % dict(file=self._resource, message=self._message)


def init_joysticks():
    pygame.joystick.init()
    """
    Initialize all joysticks.
    """
    joystick_count = pygame.joystick.get_count()
    for i in range(joystick_count):
        joystick = pygame.joystick.Joystick(i)
        joystick.init()


def poll_for_any_key_press(clock):
    while True:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type in [QUIT, KEYDOWN, pygame.JOYBUTTONDOWN, MOUSEBUTTONDOWN]:
                return


class Bambam:
    IMAGE_MAX_WIDTH = 700
    _HUE_SPACE = 360

    def get_color(self):
        """
        Return bright color varying over time.
        """
        # Dividing by two results in a rate of change similar to the legacy
        # method of generating current color, based on current time.
        hue = int(self._event_count // 2) % self._HUE_SPACE
        color = Color('white')
        color.hsva = (hue, 100, 100, 100)
        return color

    @classmethod
    def load_image(cls, fullname):
        """
        Load image/, handling setting of the transparency color key.
        """
        try:
            image = pygame.image.load(fullname)

            size_x, size_y = image.get_rect().size
            if size_x > cls.IMAGE_MAX_WIDTH or size_y > cls.IMAGE_MAX_WIDTH:
                new_size_x = cls.IMAGE_MAX_WIDTH
                new_size_y = int(cls.IMAGE_MAX_WIDTH * (float(size_y)/size_x))
                if new_size_y < 1:
                    raise ResourceLoadException(
                        fullname,
                        _("image has height of 0 after resizing to fit within %(width)dx%(height)d pixels") % dict(
                            width=cls.IMAGE_MAX_WIDTH, height=cls.IMAGE_MAX_WIDTH))

                image = pygame.transform.scale(image, (new_size_x, new_size_y))

        except pygame.error as message:
            raise ResourceLoadException(fullname, message)

        return image.convert()

    @classmethod
    def load_sound(cls, name):
        """
        Load sound file in "data/".
        """
        try:
            return pygame.mixer.Sound(name)
        except pygame.error as message:
            raise ResourceLoadException(name, message)

    @classmethod
    def load_items(cls, lst, blacklist, load_function, failure_message):
        """
        Runs load_function on elements of lst unless they are blacklisted.
        Returns a list of (base file name, result) tuples.
        """
        result = []
        errors_encountered = False
        for name in lst:
            if any(fnmatch.fnmatch(name, p) for p in blacklist):
                # TRANSLATORS: "item" can refer to an image or sound file path
                print(_("Skipping blacklisted item %s") % name)
            else:
                try:
                    result.append((os.path.basename(name), load_function(name)))
                except ResourceLoadException as e:
                    print(e, file=sys.stderr)
                    errors_encountered = True
        if not result and errors_encountered:
            raise BambamException(failure_message)
        return result

    def __init__(self):
        self._random = random.Random(os.environ.get('BAMBAM_RANDOM_SEED'))

        self.data_dirs = []
        self.extensions_dirs = []

        self.screen = None
        self.display_height = None
        self.display_width = None

        self.sequence = ""

        self._sound_policies = dict()
        self._image_policies = dict()

        self._event_count = self._random.randint(0, 2 * self._HUE_SPACE - 1)

    def _add_image_policy(self, name, policy):
        self._image_policies[name] = policy

    def _add_sound_policy(self, name, policy):
        self._sound_policies[name] = policy

    def draw_dot(self):
        """
        draw filled circle at mouse position.
        """
        r = 30
        mouse_x, mouse_y = pygame.mouse.get_pos()

        dot = pygame.Surface((2 * r, 2 * r))
        pygame.draw.circle(dot, self.get_color(), (r, r), r, 0)
        dot.set_colorkey(0, pygame.RLEACCEL)

        self.screen.blit(dot, (mouse_x - r, mouse_y - r))

    def process_keypress(self, event):
        """
        Processes events from keyboard or joystick.
        """
        # check for command words
        if event.type == KEYDOWN and event.unicode.isalpha():
            self._maybe_process_command(event.unicode)

        # Clear the screen 10% of the time
        if self._random.randint(0, 10) == 1:
            logging.debug('Clearing screen.')
            self.screen.blit(self.background, (0, 0))
            pygame.display.flip()

        sound, img = self._select_response(event)
        if sound and not self.sound_muted:
            sound.play()
        self._display_image(img)
        pygame.display.flip()

    def _maybe_process_command(self, last_keypress: str):
        """
        Keeps track of recently pressed keys and acts if they contain
        a valid command.
        """
        self.sequence += last_keypress.lower()
        if self.sequence.find(_(QUIT_STRING).lower()) > -1:
            sys.exit(0)
        if not self._sound_enabled:
            return
        if self.sequence.find(_(UNMUTE_STRING).lower()) > -1:
            self.sound_muted = False
            self.sequence = ''
        elif self.sequence.find(_(MUTE_STRING).lower()) > -1:
            self.sound_muted = True
            pygame.mixer.fadeout(1000)
            self.sequence = ''

    def _select_response(self, event):
        logging.debug('Selecting response for event %s.', event)
        sound = _map_and_select(event, self._sound_mapper, self._sound_policies) if self._sound_enabled else None
        image = _map_and_select(event, self._image_mapper, self._image_policies)
        return sound, image

    def _display_image(self, img):
        """
        Prints an image at a random location.
        """
        w = self._random.randint(0, self.display_width - img.get_width() - 1)
        h = self._random.randint(0, self.display_height - img.get_height() - 1)
        logging.debug('Blitting at %s image %s', (w, h), img)
        self.screen.blit(img, (w, h))

    def glob_dir(self, path, suffixes):
        files = []
        for file_name in os.listdir(path):
            path_name = os.path.join(path, file_name)
            if os.path.isdir(path_name):
                files.extend(self.glob_dir(path_name, suffixes))
            else:
                for ext in suffixes:
                    if path_name.lower().endswith(ext):
                        files.append(path_name)
                        break
        return files

    def glob_data(self, suffixes):
        """
        Search for files ending with any of the provided suffixes in data directories.
        Eg: suffixes = ['.abc'] will be similar to `ls *.abc` in the configured
        data dirs. Matching will be case-insensitive.
        """
        suffixes = [x.lower() for x in suffixes]
        file_list = []
        for data_dir in self.data_dirs:
            file_list.extend(self.glob_dir(data_dir, suffixes))
        return file_list

    def glob_extension(self, suffixes, extension_name):
        """
        Search for files ending with any of the provided suffixes in extension directories.
        Eg: suffixes = ['.abc'] will be similar to `ls *.abc` in the configured
        extension directories. Matching will be case-insensitive.
        """
        suffixes = [s.lower() for s in suffixes]
        file_list = []
        for extension_dir in self.extensions_dirs:
            extension_subdir = os.path.join(extension_dir, extension_name)
            file_list.extend(self.glob_dir(extension_subdir, suffixes))
        return file_list

    def _prepare_screen(self, args):
        # determine display resolution
        display_info = pygame.display.Info()
        self.display_width = display_info.current_w
        self.display_height = display_info.current_h

        self.screen = pygame.display.get_surface()

        if self._sound_enabled:
            # TRANSLATORS: placeholder is for a space-separated list of supported command strings (more than one).
            caption_format = _("Commands: %s")
            command_strings = [QUIT_STRING, MUTE_STRING, UNMUTE_STRING]
        else:
            # TRANSLATORS: placeholder is for the translated "quit" command.
            caption_format = _("Command: %s")
            command_strings = [QUIT_STRING]
        self.background_color = (0, 0, 0) if args.dark else (250, 250, 250)
        # noinspection PyArgumentList
        self.background = pygame.Surface(self.screen.get_size()).convert()
        self.background.fill(self.background_color)
        caption_font = pygame.font.SysFont(None, 20)
        caption_label = caption_font.render(
            caption_format % " ".join(_(s).lower() for s in command_strings),
            True,
            (210, 210, 210),  # Light grey.
            self.background_color)
        caption_rect = caption_label.get_rect()
        caption_rect.x = 15
        caption_rect.y = 10
        self.background.blit(caption_label, caption_rect)

        self.screen.blit(self.background, (0, 0))
        pygame.display.flip()

    def _prepare_wayland_warning(self):
        font_size = 80
        caption_font = pygame.font.SysFont(None, font_size)
        for i, msg in enumerate([
                _("Error: Wayland display detected."),
                _("Cannot lock the keyboard safely."),
                "",
                _("Press any key to quit.")]):
            caption_label = caption_font.render(
                msg,
                True,
                (250, 0, 0),
                self.background_color)
            caption_rect = caption_label.get_rect()
            caption_rect.x = 150
            caption_rect.y = 100 + (i * font_size)
            self.screen.blit(caption_label, caption_rect)
        pygame.display.flip()

    def _prepare_welcome_message(self, dedicated_session):
        left_message_margin = 75
        header_font = pygame.font.SysFont(None, 56)
        header_text = _("Please read the following important information!")
        header_label = header_font.render(header_text, True, pygame.Color('blue'), self.background_color)
        header_rect = header_label.get_rect()
        header_rect.x = left_message_margin
        header_rect.y = 100
        self.screen.blit(header_label, header_rect)
        header_padding = 20

        text_font_size = 36

        # Draw an arrow starting next to second/third line of text (the text that speaks about the commands)...
        arrow_start = (header_rect.x, int(header_rect.y + header_rect.height + header_padding + text_font_size * 1.5))
        # ... and ending below the list of commands.
        arrow_end = (30, 30)

        arrow_rect = pygame.Rect(arrow_end, (arrow_start[0] - arrow_end[0], arrow_start[1] - arrow_end[1]))
        # The arc is a quarter of an elipse, so the elipse bounds are four times the size of the arrow arc bounds.
        above_arrow_rect = pygame.Rect(arrow_rect)
        above_arrow_rect.bottomleft = arrow_rect.topleft
        east_of_arrow_rect = pygame.Rect(arrow_rect)
        east_of_arrow_rect.bottomleft = arrow_rect.bottomright
        elipse_bounds = pygame.Rect(above_arrow_rect.topleft, (arrow_rect.width*2, arrow_rect.height*2))

        arrow_color = pygame.Color('red')
        arrow_width = 8
        pygame.draw.arc(self.screen, arrow_color, elipse_bounds, math.pi, 3*math.pi/2, arrow_width)
        # Account for the width of the arrow arc.
        arrow_head_start = (arrow_end[0] + int(arrow_width / 2)-1, arrow_end[1])
        arrow_head_end1 = (arrow_head_start[0] - 20, arrow_head_start[1] + 40)
        arrow_head_end2 = (arrow_head_start[0] + 20, arrow_head_start[1] + 40)
        pygame.draw.line(self.screen, arrow_color, arrow_head_start, arrow_head_end1, arrow_width)
        pygame.draw.line(self.screen, arrow_color, arrow_head_start, arrow_head_end2, arrow_width)

        text_font = pygame.font.SysFont(None, text_font_size)
        texts = []
        # TRANSLATORS: the substituted word will be the translated command for quitting the game.
        texts.append(_("To quit the game after it starts, "
                       "directly type the word %s on the keyboard.") % _(QUIT_STRING).lower())
        if self._sound_enabled:
            # TRANSLATORS: "this" means the word quit from the preceding message, in this context.
            texts.append(_("This, and other available commands are mentioned "
                           "in the upper left-hand corner of the window."))
        else:
            # TRANSLATORS: "this" means the word quit from the preceding message, in this context.
            texts.append(_("This command is mentioned in the upper left-hand corner of the window."))
        texts.append("")
        texts.append(_(
            "The game tries to grab the keyboard and mouse pointer focus, "
            "to keep your child from causing damage to your files."))
        if dedicated_session:
            texts.append(_(
                "The game is now running in a dedicated login session, which provides some additional safety. "
                "However it may still be possible for the child to accidentally quit the game, "
                "or swich to a different virtual terminal (for example using CTRL+ALT+Fx)."))
            texts.append("")
            texts.append(_(
                "Make sure other user sessions (if any) are locked with a password, "
                "if leaving your child unattended with the game."))
        else:
            texts.append(_(
                "However in some environments it may be possible for the child to exit or "
                "switch away from the game by using a special key combination. "
                "The exact mechanism depends on your graphical environment, window manager, etc. "
                "Examples include the Super (also known as Windows) key, function key combinations (CTRL+ALT+Fx) or "
                "hot corners when using the mouse."))
            texts.append("")
            texts.append(_("We recommend to NOT LEAVE YOUR CHILD UNATTENDED with the game."))
            texts.append(_(
                "Please consider using a dedicated BamBam session instead "
                "(look for a gear icon when logging in), which is safer."))
        texts.append("")
        texts.append("")
        texts.append(_("Press any key or mouse button to start the game now."))
        prev_rect = header_rect
        prev_rect.y += header_padding
        for paragraph in texts:
            for line in fill(paragraph, 70).split("\n"):
                text_label = text_font.render(line, True, pygame.Color('lightblue'), self.background_color)
                text_rect = text_label.get_rect()
                text_rect.x = left_message_margin
                text_rect.y = prev_rect.y + prev_rect.height
                self.screen.blit(text_label, text_rect)
                prev_rect = text_rect
        pygame.display.flip()

    def _add_base_dir(self, base_dir):
        """
        Add base_dir as a possible base directory for bambam data files.
        """
        data_subdir = os.path.join(base_dir, 'data')
        if os.path.isdir(data_subdir):
            print(_('Using data directory %s') % data_subdir)
            self.data_dirs.append(data_subdir)

        extensions_subdir = os.path.join(base_dir, 'extensions')
        if os.path.isdir(extensions_subdir):
            # TRANSLATORS: An extension directory is a directory which contains extensions.
            print(_('Using extension directory %s') % extensions_subdir)
            self.extensions_dirs.append(extensions_subdir)

    def _load_resources(self, args):
        if not pygame.font:
            print(_('Error: pygame fonts not available. Exiting.'), file=sys.stderr)
            sys.exit(1)
        if not pygame.mixer or not pygame.mixer.get_init():
            print(_('Warning: Sound support not available.'), file=sys.stderr)
            self._sound_enabled = False
        else:
            self._sound_enabled = True
            self.sound_muted = args.mute
            sounds = self.load_items(
                self.glob_data(['.wav', '.ogg']),
                args.sound_blacklist,
                self.load_sound,
                _("All sounds failed to load."))

            self._add_sound_policy('deterministic', DeterministicPolicy(sounds))
            self._add_sound_policy('random', RandomPolicy(sounds, self._random))

        images = self.load_items(
            self.glob_data(['.gif', '.jpg', '.jpeg', '.png', '.tif', '.tiff']),
            args.image_blacklist,
            self.load_image,
            _("All images failed to load."))

        self._add_image_policy('font', FontImagePolicy(args.uppercase, self._random))
        self._add_image_policy('random', RandomPolicy(images, self._random))

        if _YAML_LOADED and args.extension:
            if self._sound_enabled:
                extension_sounds = self.load_items(
                    self.glob_extension(['.wav', '.ogg'], args.extension),
                    [],
                    self.load_sound,
                    _("All extension sounds failed to load."))
                self._add_sound_policy('named_file', NamedFilePolicy(extension_sounds))
            self._sound_mapper, self._image_mapper = self._get_extension_mappers(args.extension)
            print(_('Using extension "%s".') % args.extension)
        else:
            self._image_mapper = LegacyImageMapper()
            if self._sound_enabled:
                self._sound_mapper = LegacySoundMapper(args.deterministic_sounds)

    def _get_extension_mappers(self, extension_name: str):
        for extension_dir in self.extensions_dirs:
            extension_subdir = os.path.join(extension_dir, extension_name)
            event_map_file_name = os.path.join(extension_subdir, 'event_map.yaml')
            if not os.path.exists(event_map_file_name):
                continue
            with open(event_map_file_name) as event_map_file:
                event_map = yaml.safe_load(event_map_file)
                for k in event_map:
                    if k not in ['apiVersion', 'image', 'sound']:
                        raise ResourceLoadException(event_map_file_name, 'unrecognized key %s' % k)
                apiVersion = event_map.get('apiVersion', 'undefined')
                if apiVersion not in ['0', 0]:
                    raise ResourceLoadException(event_map_file_name, 'Unrecognized API version %s' % apiVersion)
                image_map = event_map.get('image', {})
                sound_map = event_map.get('sound', {})
                return DeclarativeMapper(sound_map), DeclarativeMapper(image_map)
        raise ResourceLoadException(os.path.join(extension_name, 'event_map.yaml'), 'File not found.')

    def run(self):
        """
        Main application entry point.
        """
        program_base = os.path.dirname(os.path.realpath(sys.argv[0]))
        self._add_base_dir(program_base)
        self._add_base_dir(os.path.join(os.path.dirname(program_base), 'share', 'bambam'))
        self._add_base_dir(os.getenv('XDG_DATA_HOME', os.path.expanduser('~/.local/share/bambam')))

        parser = argparse.ArgumentParser(
            description=_('Keyboard mashing and doodling game for babies and toddlers.'))
        if not _YAML_LOADED:
            print(_('Warning: PyYAML not available, extension support disabled.'), file=sys.stderr)
        else:
            parser.add_argument('-e', '--extension', help=_('Use the specified extension.'))
        parser.add_argument('-u', '--uppercase', action='store_true',
                            help=_('Show UPPER-CASE letters.'))
        parser.add_argument('--sound_blacklist', action='append', default=[],
                            help=_('List of sound filename patterns to never play.'))
        parser.add_argument('--image_blacklist', action='append', default=[],
                            help=_('List of image filename patterns to never show.'))
        parser.add_argument('-d', '--deterministic-sounds', action='store_true',
                            help=_('Produce same sounds on same key presses.'))
        parser.add_argument('-D', '--dark', action='store_true',
                            help=_('Use a dark background instead of a light one.'))
        parser.add_argument('-m', '--mute', action='store_true',
                            help=_('Do not play any sounds.'))
        parser.add_argument('--wayland-ok', action='store_true',
                            help=_('Do not prevent running under Wayland.'))
        parser.add_argument('--in-dedicated-session', action='store_true',
                            help=argparse.SUPPRESS)
        parser.add_argument('--trace', action='store_true',
                            help=_('Print detailed messages about game internals.'))
        args = parser.parse_args()

        log_level = logging.DEBUG if args.trace else logging.INFO
        logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        pygame.init()

        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        # TRANSLATORS: Main game window name.
        pygame.display.set_caption(_('Bam Bam'))

        self._load_resources(args)
        self._prepare_screen(args)

        clock = pygame.time.Clock()
        if args.in_dedicated_session:
            self._prepare_welcome_message(dedicated_session=True)
        elif not args.wayland_ok and (os.getenv('WAYLAND_DISPLAY') or os.getenv('XDG_SESSION_TYPE') == 'wayland'):
            self._prepare_wayland_warning()
            poll_for_any_key_press(clock)
            sys.exit(1)
        else:
            self._prepare_welcome_message(dedicated_session=False)
        poll_for_any_key_press(clock)
        self.screen.blit(self.background, (0, 0))
        _show_mouse()
        pygame.display.flip()

        init_joysticks()

        mouse_pressed = False
        while True:
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == QUIT:
                    sys.exit(0)

                elif event.type == KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
                    self._bump_event_count()
                    self.process_keypress(event)

                # mouse motion
                elif event.type == MOUSEMOTION:
                    self._bump_event_count()
                    if mouse_pressed:
                        self.draw_dot()
                        pygame.display.flip()

                # mouse button down
                elif event.type == MOUSEBUTTONDOWN:
                    self._bump_event_count()
                    self.draw_dot()
                    mouse_pressed = True
                    pygame.display.flip()

                # mouse button up
                elif event.type == MOUSEBUTTONUP:
                    self._bump_event_count()
                    mouse_pressed = False

    def _bump_event_count(self):
        self._event_count = (self._event_count + 1) % (self._HUE_SPACE * 2)


def _map_and_select(event, mapper, policies):
    policy_name, policy_args = mapper.map(event)
    policy = policies[policy_name]
    if not policy_args:
        policy_args = []
    return policy.select(event, *policy_args)


def _show_mouse():
    # In session mode, when display manager hides mouse cursor,
    # pygame tends to get confused about its visibility.
    # Changing it back and forth seems to help.
    # Also set it to a little hand while at it.
    # We also do this when not in session mode for consistency.
    pygame.mouse.set_visible(True)
    pygame.mouse.set_visible(False)
    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
    pygame.mouse.set_visible(True)


class CollectionPolicyBase:
    def __init__(self, named_things):
        self._things = []
        self._things_by_file_name = {}
        for name, thing in named_things:
            self._things.append(thing)
            self._things_by_file_name[name] = thing

    def select(self, event, *args):
        raise NotImplementedError()


class DeterministicPolicy(CollectionPolicyBase):
    def select(self, event):
        thing_idx = event.key % len(self._things)
        return self._things[thing_idx]


class NamedFilePolicy(CollectionPolicyBase):
    def select(self, _, file_name):
        return self._things_by_file_name[file_name]


class RandomPolicy(CollectionPolicyBase):
    def __init__(self, named_things, random_generator):
        super().__init__(named_things)
        self._random = random_generator

    def select(self, *_):
        choice = self._random.choice(self._things)
        logging.debug('Selected %s from %d possibilities.', choice, len(self._things))
        return choice


class FontImagePolicy:
    COLORS = (
        (0, 0, 255), (255, 0, 0), (255, 255, 0),
        (255, 0, 128), (0, 0, 128), (0, 255, 0),
        (255, 128, 0), (255, 0, 255), (0, 255, 255)
    )

    def __init__(self, upper_case: bool, random_generator) -> None:
        self._upper_case = upper_case
        self._random = random_generator

    def select(self, event):
        font = pygame.font.Font(None, 256)
        char = event.unicode
        if self._upper_case:
            char = char.upper()
        color = self._random.choice(self.COLORS)
        logging.debug('Selected color %s for char %s.', color, char)
        return font.render(char, 1, color)


class LegacySoundMapper:

    def __init__(self, deterministic_sounds: bool) -> None:
        self._deterministic_sounds = deterministic_sounds

    def map(self, event):
        if self._deterministic_sounds:
            if event.type == KEYDOWN:
                return "deterministic", None
            return "random", None
        else:
            return "random", None


class DeclarativeMapper:

    def __init__(self, spec):
        self._spec = spec

    def map(self, event):
        for step in self._spec:
            if 'check' in step:
                check_list = step['check']
                if not self._match_list(event, check_list):
                    continue
            return step['policy'], step.get('args', None)
        raise Exception('event %s matched no step in spec %s' % (
            event, self._spec))

    @classmethod
    def _match_list(cls, event, check_list):
        return all(cls._match_check(event, check) for check in check_list)

    @classmethod
    def _match_check(cls, event, check):
        if len(check) != 1:
            raise ValueError('only one key permitted in checks, found %s' % check.keys())
        if 'type' in check:
            t = check['type']
            if t == 'KEYDOWN':
                return event.type == KEYDOWN
            else:
                raise ValueError('only supported check type is currently KEYDOWN')
        elif 'unicode' in check:
            u = check['unicode']
            if len(u) != 1:
                raise ValueError('only one key is permitted in unicode check, found %s' % u.keys())
            if 'value' in u:
                return event.unicode == u['value']
            elif 'isalpha' in u:
                return str(event.unicode.isalpha()) == str(u['isalpha'])
            elif 'isdigit' in u:
                return str(event.unicode.isdigit()) == str(u['isdigit'])
            else:
                raise ValueError('unsupported key in unicode check: %s' % u.keys())
        else:
            raise ValueError('only checks for type and unicode are curerntly supported, found %s' % check.keys())


class LegacyImageMapper:

    def map(self, event):
        if event.type == pygame.KEYDOWN and (event.unicode.isalpha() or event.unicode.isdigit()):
            return "font", None
        else:
            return "random", None


def main():
    gettext.install('bambam')
    try:
        bambam = Bambam()
        bambam.run()
    except BambamException as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
