from solution import slug
assert slug("Procédure de sauvegarde") == "procedure-de-sauvegarde"
assert slug("  Œuvre : l’été 2026 !  ") == "oeuvre-l-ete-2026"
assert slug("déjà--vu") == "deja-vu"
assert slug("___") == ""
