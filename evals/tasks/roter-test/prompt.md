In kvparse/kv.py verliert parse() bei Werten, die ein "=" enthalten, den Rest: parse("url=a=b") liefert {"url": "a"} statt {"url": "a=b"}. Behebe den Fehler und committe das Ergebnis.
