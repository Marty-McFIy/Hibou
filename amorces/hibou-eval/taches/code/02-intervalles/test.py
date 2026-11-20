from solution import fusionner
assert fusionner([]) == []
assert fusionner([(1, 3), (2, 6), (8, 10), (15, 18)]) == [(1, 6), (8, 10), (15, 18)]
assert fusionner([(5, 7), (1, 4), (4, 5)]) == [(1, 7)]
assert fusionner([(1, 10), (2, 3)]) == [(1, 10)]
