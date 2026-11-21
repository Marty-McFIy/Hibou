"""
title: Publier dans Forgejo
author: Hibou
version: 0.2.0
description: Dépose un document Markdown dans hibou-docs, sur une branche, et ouvre une pull request.
"""
import base64, datetime, re
import requests
from pydantic import BaseModel, Field


URL_NUE = re.compile(r"(?<![<(`\[])\bhttps?://[^\s<>()`]+[^\s<>()`.,;:!?]")


def normaliser(md: str) -> str:
    """Règles du runner (markdownlint) qu'un petit modèle oublie : langage et lignes vides autour des blocs de code,
    adresses nues entre chevrons, un seul saut de ligne final. Le texte lui-même n'est pas touché."""
    sortie, dans_bloc, fermeture = [], False, ""
    lignes = md.replace("\r\n", "\n").split("\n")
    for i, l in enumerate(lignes):
        m = re.match(r"^(\s*)(`{3,}|~{3,})(.*)$", l)
        if m and not dans_bloc:
            dans_bloc, fermeture = True, m.group(2)
            if sortie and sortie[-1].strip():
                sortie.append("")
            sortie.append(l if m.group(3).strip() else f"{m.group(1)}{m.group(2)}text")
            continue
        if m and dans_bloc and m.group(2).startswith(fermeture[0]) and len(m.group(2)) >= len(fermeture) and not m.group(3).strip():
            dans_bloc = False
            sortie.append(l)
            if i + 1 < len(lignes) and lignes[i + 1].strip():
                sortie.append("")
            continue
        if not dans_bloc:
            # Hors code en ligne : les segments entre accents graves restent tels quels.
            l = "`".join(p if k % 2 else URL_NUE.sub(lambda u: f"<{u.group(0)}>", p) for k, p in enumerate(l.split("`")))
        sortie.append(l)
    return "\n".join(sortie).rstrip("\n") + "\n"


class Tools:
    class Valves(BaseModel):
        forgejo_url: str = Field("https://forge.hibou.lan", description="Adresse de Forgejo.")
        depot: str = Field("hibou/hibou-docs", description="Dépôt cible, organisation/nom.")
        jeton: str = Field("", description="Jeton du compte hibou-redac (donné par « hibou configurer »).")

    def __init__(self):
        self.valves = self.Valves()

    def _api(self, methode, chemin, **kw):
        r = requests.request(methode, f"{self.valves.forgejo_url}/api/v1/repos/{self.valves.depot}{chemin}",
                             headers={"Authorization": f"token {self.valves.jeton}"}, timeout=30, **kw)
        r.raise_for_status()
        return r.json() if r.content else {}

    def publier_document(self, titre: str, chemin: str, contenu: str, __user__: dict = {}) -> str:
        """
        Publie un document Markdown dans Forgejo et ouvre une pull request à relire.
        :param titre: Titre du document, utilisé pour la pull request.
        :param chemin: Chemin du fichier dans le dépôt, sous docs/, terminé par .md (ex. docs/procedures/sauvegarde-forgejo.md).
        :param contenu: Le document Markdown complet, en-tête YAML compris.
        :return: L’adresse de la pull request, ou ce qu’il faut corriger.
        """
        if not self.valves.jeton:
            return "Aucun jeton configuré. Renseigne-le dans les réglages de l’outil."
        if not re.fullmatch(r"docs/[a-z0-9][a-z0-9/_-]*\.md", chemin) or ".." in chemin:
            return "Chemin refusé. Utilise docs/<dossier>/<nom-en-minuscules>.md, sans espace ni accent."
        contenu = normaliser(contenu)
        if not contenu.startswith("---"):
            return "Le document doit commencer par son en-tête YAML (modele, titre)."
        auteur = (__user__ or {}).get("name", "inconnu")
        branche = "redaction/" + re.sub(r"[^a-z0-9-]", "-", chemin[5:-3]) + datetime.datetime.now().strftime("-%Y%m%d%H%M")
        try:
            self._api("POST", "/branches", json={"new_branch_name": branche, "old_branch_name": "main"})
            self._api("POST", f"/contents/{chemin}", json={
                "branch": branche, "message": f"Rédaction : {titre}",
                "content": base64.b64encode(contenu.encode()).decode()})
            pr = self._api("POST", "/pulls", json={
                "head": branche, "base": "main", "title": titre,
                "body": f"Document rédigé avec Hibou pour {auteur}. Le runner vérifie le style, les sections et les schémas."})
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 422:
                return "Ce fichier existe déjà sur main. Choisis un autre chemin, ou modifie-le dans Forgejo."
            return f"Forgejo a refusé la publication ({e}). Vérifie le jeton et le dépôt dans les réglages de l’outil."
        return f"J’ai ouvert la pull request : {pr.get('html_url')}"
