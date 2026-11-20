from solution import CacheLRU
c = CacheLRU(2)
c.ecrire("a", 1); c.ecrire("b", 2)
assert c.lire("a") == 1
c.ecrire("c", 3)
assert c.lire("b") is None and c.lire("a") == 1 and c.lire("c") == 3
c.ecrire("a", 10); c.ecrire("d", 4)
assert c.lire("c") is None and c.lire("a") == 10
