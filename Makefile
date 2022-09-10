VERSION = 1.2.0
LINGUAS = $(shell awk '$$1=="[po4a_langs]"{$$1="";print}' po4a.conf)
PREFIX ?=

.PHONY: all-mo
all-mo: $(LINGUAS:%=po/%.mo)

.PHONY: all
all: all-mo all-manpages bambam-session.desktop bambam.desktop

.PHONY: all-manpages
all-manpages: $(LINGUAS:%=bambam.%.6)

.PHONY: install-mo
install-mo: $(LINGUAS:%=install-mo-%)

.PHONY: install-mo-%
install-mo-%: po/%.mo
	install -o root -g root -m 0644 -D $< $(PREFIX)/usr/share/locale/$*/LC_MESSAGES/bambam.mo

po/%.po: bambam.pot
	msgmerge -U $@ $<
	touch $@

po/%.mo: po/%.po
	msgfmt -o $@ $<

po/LINGUAS: Makefile po4a.conf
	echo $(LINGUAS) > $@

# Pot files:

bambam.pot: bambam-py.pot bambam-man.pot bambam-desktop.pot bambam-session-desktop.pot
	msgcat $^ > $@

bambam-py.pot: bambam.py Makefile
	xgettext -d bambam --msgid-bugs-address=marcin@owsiany.pl --package-name bambam --package-version $(VERSION) -o $@ -kN_ -c $<

%-desktop.pot: %.en.desktop Makefile
	xgettext -d bambam --msgid-bugs-address=marcin@owsiany.pl --package-name bambam --package-version $(VERSION) -o $@ -c $<

bambam-man.pot: bambam.6
	po4a-gettextize -f man -m $< -p $@

# Localized artifacts:

bambam.%.6: po/%.po bambam.6
	po4a-translate -f man -m bambam.6 -p $< -l $@

%.desktop: %.en.desktop $(LINGUAS:%=po/%.mo) po/LINGUAS
	msgfmt --desktop --template $< -d po/ -o $@

.PHONY: clean
clean:
	rm -f $(LINGUAS:%=po/%.mo) po/LINGUAS
