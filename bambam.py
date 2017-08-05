#!/usr/bin/env python2
# Copyright (C)
#    2007-2008 Don Brown,
#    2010 Spike Burch <spikeb@gmail.com>,
#    2015-2016 Vasya Novikov
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

import pygame, sys,os, random, string, glob
import argparse
import fnmatch
from pygame.locals import * 

# draw filled circle at mouse position
def draw_dot():
    r = 30
    mousex, mousey = pygame.mouse.get_pos()
    
    dot = pygame.Surface((2 * r, 2 * r))
    pygame.draw.circle(dot, get_color(), (r, r), r, 0)
    dot.set_colorkey(0, pygame.RLEACCEL)
    
    screen.blit(dot, (mousex - r, mousey - r))


# Return bright color varying over time
def get_color():
    col = Color('white');
    
    hue = pygame.time.get_ticks() / 50 % 360
    col.hsva = (hue, 100, 100, 50)
    
    return Color(col.r, col.g, col.b)


# Load image/, handling setting of the transparency color key
def load_image(fullname, colorkey = None):
    try:
        image = pygame.image.load(fullname)
    except pygame.error, message:
        print "Cannot load image:", fullname
        raise SystemExit, message
    image = image.convert()
    if colorkey is not None:
        if colorkey is -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey, RLEACCEL)
    return image


# Load sound file in data/
def load_sound(name):
    class NoneSound:
        def play(self): pass
    if not pygame.mixer:
        return NoneSound()
    try:
        sound = pygame.mixer.Sound(name)
    except pygame.error, message:
        print "Cannot load sound:", name
        raise SystemExit, message
    return sound


def load_items(lst, blacklist, load_function):
    """Runs load_function on elements of lst unless they are blacklisted."""
    result = []
    for name in lst:
        if True in [fnmatch.fnmatch(name, p) for p in blacklist]:
            print "Skipping blacklisted item:", name
        else:
            result.append(load_function(name))
    return result


# Processes events
def input(events, quit_pos):
    global sequence, mouse_down, sound_muted, caps_on, num_lock
    for event in events: 
        if event.type == QUIT: 
            sys.exit(0)
        
        # handle keydown event
        elif event.type == KEYDOWN or event.type == pygame.JOYBUTTONDOWN:
            # check for words like quit
            if event.type == KEYDOWN:
                if event.key == pygame.K_CAPSLOCK:
                    caps_on = True
                if event.key == pygame.K_NUMLOCK:
                    num_lock = True
                if is_alpha(event.key):
                    sequence += chr(event.key)
                    if sequence.find('quit') > -1:
                        if caps_on:
                            sys.stdout.write('\nYour CAPSLOCK may have been '
                                'reversed! Be sure to check CAPSLOCK now.\n\n')
                        if num_lock:
                            sys.stdout.write('\nYour NUMLOCK may have been '
                                'reversed! Be sure to check NUMLOCK now.\n\n')
                        sys.exit(0)
                    elif sequence.find('unmute') > -1:
                        sound_muted = False
                        #pygame.mixer.unpause()
                        sequence = ''
                    elif sequence.find('mute') > -1:
                        sound_muted = True
                        pygame.mixer.fadeout(1000)
                        sequence = ''
            
            # Clear the background 10% of the time
            if random.randint(0, 10) == 1:
                screen.blit(background, (0, 0))
                pygame.display.flip()
            
            # play random sound
            if not sound_muted:
                if event.type == KEYDOWN and args.deterministic_sounds:
                    sounds[event.key % len(sounds)].play()
                else:
                    sounds[random.randint(0, len(sounds) -1)].play()

            # show images
            if event.type == pygame.KEYDOWN and (event.unicode.isalpha() or event.unicode.isdigit()):
                print_letter(event.unicode)
            else:
                print_image()
            pygame.display.flip()
            
        # mouse motion
        elif event.type == MOUSEMOTION :
            if mouse_down:
                draw_dot()
                pygame.display.flip()
        
        # mouse button down
        elif event.type == MOUSEBUTTONDOWN:
            draw_dot()
            mouse_down = True
            pygame.display.flip()

        # mouse button up
        elif event.type == MOUSEBUTTONUP:
            mouse_down = False
        
    return quit_pos


# Prints an image at a random location
def print_image():
    #global swidth, sheigh
    img = images[random.randint(0, len(images) - 1)]
    w = random.randint(0, swidth  - img.get_width())
    h = random.randint(0, sheight - img.get_height())
    screen.blit(img, (w, h))

# Is the key that was pressed alphanumeric
def is_alpha(key):
    return key < 255 and (chr(key) in string.letters or chr(key) in string.digits)

# Prints a letter at a random location
def print_letter(char):
    global args
    font = pygame.font.Font(None, 256)
    if args.uppercase:
        char = char.upper()
    text = font.render(char, 1, colors[random.randint(0, len(colors) - 1)])
    textpos = text.get_rect()
    center = (textpos.width / 2, textpos.height / 2)
    w = random.randint(0 + center[0], swidth - center[0])
    h = random.randint(0 + center[1], sheight - center[1])
    textpos.centerx = w
    textpos.centery = h
    screen.blit(text, textpos) 

# Main application
#
parser = argparse.ArgumentParser(description='A keyboard mashing game for babies.')
parser.add_argument('-u', '--uppercase', action='store_true', help='Whether to show UPPER-CASE letters.')
parser.add_argument('--sound_blacklist', action='append', default=[], help='List of sound filename patterns to never play.')
parser.add_argument('--image_blacklist', action='append', default=[], help='List of image filename patterns to never show.')
parser.add_argument('-d', '--deterministic-sounds', action='store_true', help='Whether to produce same sounds on same key presses.')
parser.add_argument('-m', '--mute', action='store_true', help='No sound will be played.')
args = parser.parse_args()

if not pygame.font: print 'Warning, fonts disabled'
if not pygame.mixer: print 'Warning, sound disabled'
 
pygame.init()
caps_on = False
num_lock = False

# figure out the install base to use with image and sound loading
progInstallBase = os.path.dirname(os.path.realpath(sys.argv[0]));

# swith to full screen at current screen resolution 
window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

# determine display resolution
displayinfo = pygame.display.Info()
swidth = displayinfo.current_w
sheight = displayinfo.current_h

pygame.display.set_caption('Bam Bam') 
screen = pygame.display.get_surface() 

background = pygame.Surface(screen.get_size())
background = background.convert()
background.fill((250, 250, 250))
captionFont = pygame.font.SysFont(None, 20)
captionLabel = captionFont.render("Commands: quit, mute, unmute", True, (210, 210, 210), (250, 250, 250))
captionRect = captionLabel.get_rect()
captionRect.x = 15
captionRect.y = 10
background.blit(captionLabel, captionRect)
sequence = ""
screen.blit(background, (0, 0))
pygame.display.flip()

mouse_down = False
sound_muted = args.mute

def glob_data(pattern):
    return glob.glob(os.path.join(progInstallBase, 'data', pattern))

sounds = load_items(glob_data('*.wav'), args.sound_blacklist, load_sound)

colors = ((  0,   0, 255), (255,   0,   0), (255, 255,   0), 
          (255,   0, 128), (  0,   0, 128), (  0, 255,   0), 
          (255, 128,   0), (255,   0, 255), (  0, 255, 255)
)

images = load_items(glob_data('*.gif'), args.image_blacklist, load_image)

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
    quit_pos = input(pygame.event.get(), quit_pos)

