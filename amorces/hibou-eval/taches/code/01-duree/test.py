from solution import parse_duree
assert parse_duree("1h30m") == 5400
assert parse_duree("45s") == 45
assert parse_duree("2h") == 7200
assert parse_duree("1h2m3s") == 3723
for mauvais in ["", "10x", "h", "1h1h", "m5"]:
    try:
        parse_duree(mauvais); raise SystemExit(f"accepté : {mauvais!r}")
    except ValueError:
        pass
