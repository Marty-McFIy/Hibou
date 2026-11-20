from solution import dans_reseau
assert dans_reseau("192.168.10.12", "192.168.10.0/24")
assert not dans_reseau("192.168.11.1", "192.168.10.0/24")
assert dans_reseau("10.1.2.3", "0.0.0.0/0")
assert dans_reseau("172.16.5.4", "172.16.0.0/12")
for a, r in [("256.1.1.1", "10.0.0.0/8"), ("1.2.3", "10.0.0.0/8"), ("1.2.3.4", "10.0.0.0/33")]:
    try:
        dans_reseau(a, r); raise SystemExit(f"accepté : {a} {r}")
    except ValueError:
        pass
