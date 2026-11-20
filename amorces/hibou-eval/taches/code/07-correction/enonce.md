Cette fonction doit renvoyer la moyenne glissante sur `k` valeurs, mais elle est fausse. Corrige-la sans changer sa signature.

```python
def moyenne_glissante(valeurs, k):
    resultat = []
    somme = 0
    for i, v in enumerate(valeurs):
        somme += v
        if i > k:
            somme -= valeurs[i - k]
        if i >= k:
            resultat.append(somme / k)
    return resultat
```
