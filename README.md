Bambam is a simple baby keyboard (and gamepad) masher application that locks the keyboard and mouse and instead displays bright colors, pictures, and sounds.  While OSX has great programs like [AlphaBaby](http://www.kldickey.addr.com/alphababy/), the original author couldn't find anything for Linux and having wanted to learn Python for a while, Bambam was his excuse.

![Bambam screenshot](docs/bambam.png "Bambam screenshot")

## Usage ##

Before running this application, ensure you have the following installed:
  * [Python](http://python.org) - version 3.x is recommended but version 2.7 should work too
  * [Pygame](http://www.pygame.org/)

### Installation ###

First, see if your distribution has a bambam package already, for example:
```
sudo apt install bambam
man bambam
bambam
```

If not, you can install it manually as follows:
  1. [Download](https://github.com/porridge/bambam/releases) the bambam-1.1.0.zip or bambam-1.1.0.tar.gz file.
  1. Unzip bambam-1.1.0.zip or "tar zxvf bambam-1.1.0.tar.gz" to create the bambam-1.1.0 directory.
  1. Move into the 'bambam-1.1.0' directory
```
cd bambam-1.1.0
```
  1. Execute
```
./bambam.py
```
  1. To exit, just directly type the command mentioned in the upper left-hand corner of the window. In the English locales, this is:
```
quit
```
  1. More information is in the man page. To view it, type:
```
man ./bambam.6
```

Comments or suggestions? Any feedback is appreciated, please send it to [the bambam-users forum](https://groups.google.com/forum/#!forum/bambam-users).

Translations for this game are done on [Weblate](https://hosted.weblate.org/projects/bambam/). Please help translating for your mothe tongue!

---

This project was moved from [its code.google.com location](https://code.google.com/p/bambam/) in April 2015, since that site was about to be shut down.

Note that changes (as of 2010-08-17) from [the launchpad bambam fork](https://launchpad.net/bambam) had been merged back to this project in February 2014.
