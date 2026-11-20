from solution import lire_env
t = '''
# commentaire
export HIBOU_DOMAINE = hibou.lan
CLE="a=b c"
VIDE=
MOT='simple'
'''
assert lire_env(t) == {"HIBOU_DOMAINE": "hibou.lan", "CLE": "a=b c", "VIDE": "", "MOT": "simple"}
try:
    lire_env("SANS_EGAL"); raise SystemExit("accepté")
except ValueError:
    pass
