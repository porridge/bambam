VERSION = 1.1.1
LINGUAS = eo fr nb_NO pl
PREFIX ?=

.PHONY: all-mo
all-mo: $(LINGUAS:%=po/%.mo)

.PHONY: all
all: all-mo all-manpages

.PHONY: all-manpages
all-manpages: $(LINGUAS:%=bambam.%.6)

.PHONY: install-mo
install-mo: $(LINGUAS:%=install-mo-%)

.PHONY: install-mo-%
install-mo-%: po/%.mo
	install -o root -g root -m 0644 -D $< $(PREFIX)/usr/share/locale/$*/LC_MESSAGES/bambam.mo

po/%.mo: po/%.po
	msgfmt -o $@ $<

po/%.po: bambam.pot
	msgmerge -U $@ $<
	touch $@

bambam.pot: bambam-py.pot bambam-man.pot
	msgcat $^ > $@

bambam-py.pot: bambam.py Makefile
	xgettext -d bambam --msgid-bugs-address=marcin@owsiany.pl --package-name bambam --package-version $(VERSION) -o $@ -kN_ -c $<

bambam-man.pot: bambam.6
	po4a-gettextize -f man -m $< -p $@

bambam.%.6: po/%.po bambam.6
	po4a-translate -f man -m bambam.6 -p $< -l $@

.PHONY: clean
clean:
	rm -f $(LINGUAS:%=po/%.mo)
