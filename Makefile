LINGUAS = pl

.PHONY: allmos
allmos: $(LINGUAS:%=po/%.mo)

po/%.mo: po/%.po
	msgfmt -o $@ $<

po/%.po: bambam.pot
	msgmerge -U $@ $<

bambam.pot: bambam.py
	xgettext -d bambam --msgid-bugs-address=marcin@owsiany.pl --package-name bambam --package-version 1.0.2 -o $@ -kN_ -c $^
