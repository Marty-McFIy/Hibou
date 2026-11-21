"""
title: Publier dans Forgejo
author: Hibou
version: 0.4.1
description: Publie un document Markdown dans hibou-docs, lit un document publié ou en propose une nouvelle version, toujours par pull request.
"""
import base64, datetime, re
import requests
from pydantic import BaseModel, Field


URL_NUE = re.compile(r"(?<![<(`\[])\bhttps?://[^\s<>()`]+[^\s<>()`.,;:!?]")


def normaliser(md: str) -> str:
    """Règles du runner (markdownlint) qu'un petit modèle oublie : langage et lignes vides autour des blocs de code,
    adresses nues entre chevrons, un seul saut de ligne final. Un bloc de code placé sous une étape numérotée est
    indenté sous elle : sinon la liste s'arrête au bloc et l'étape suivante (« 4. ») est refusée (MD029) et mal
    numérotée sur le site. Le texte lui-même n'est pas touché."""
    sortie, dans_bloc, fermeture, etape, retrait = [], False, "", "", ""
    lignes = md.replace("\r\n", "\n").split("\n")
    for i, l in enumerate(lignes):
        m = re.match(r"^(\s*)(`{3,}|~{3,})(.*)$", l)
        if m and not dans_bloc:
            dans_bloc, fermeture = True, m.group(2)
            retrait = etape if not m.group(1) else ""
            if sortie and sortie[-1].strip():
                sortie.append("")
            sortie.append(retrait + (l if m.group(3).strip() else f"{m.group(1)}{m.group(2)}text"))
            continue
        if m and dans_bloc and m.group(2).startswith(fermeture[0]) and len(m.group(2)) >= len(fermeture) and not m.group(3).strip():
            dans_bloc = False
            sortie.append(retrait + l)
            if i + 1 < len(lignes) and lignes[i + 1].strip():
                sortie.append("")
            continue
        if dans_bloc:
            l = retrait + l if l.strip() else l
        else:
            n = re.match(r"^\d+\.\s+", l)
            if n:
                etape = " " * len(n.group(0))
            elif l.strip() and not l.startswith((" ", "\t")):
                etape = ""
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
        if "<!--" in contenu:  # gabarit renvoyé tel quel : le runner le refuserait, autant le dire avant d’ouvrir la PR
            return "Le document contient encore des consignes du template (<!-- … -->). Remplace chacune par le contenu, puis publie à nouveau."
        auteur = (__user__ or {}).get("name") or "inconnu"
        courriel = (__user__ or {}).get("email") or ""
        # Une branche par personne (redaction/<personne>/…) ; le site docs montre tout ce qui est fusionné dans main.
        personne = re.sub(r"[^a-z0-9-]", "-", (courriel.split("@")[0] or auteur).lower()).strip("-") or "inconnu"
        branche = f"redaction/{personne}/" + re.sub(r"[^a-z0-9-]", "-", chemin[5:-3]) + datetime.datetime.now().strftime("-%Y%m%d%H%M")
        try:
            self._api("POST", "/branches", json={"new_branch_name": branche, "old_branch_name": "main"})
            self._api("POST", f"/contents/{chemin}", json={
                "branch": branche, "message": f"Rédaction : {titre}",
                **({"author": {"name": auteur, "email": courriel}} if courriel else {}),
                "content": base64.b64encode(contenu.encode()).decode()})
            pr = self._api("POST", "/pulls", json={
                "head": branche, "base": "main", "title": titre,
                "body": f"Demandé par {auteur}" + (f" ({courriel})" if courriel else "") + ", rédigé avec Hibou. Le runner vérifie le style, les sections et les schémas."})
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 422:
                return "Ce fichier existe déjà : lis-le avec lire_document, puis propose une nouvelle version avec mettre_a_jour_document."
            return f"Forgejo a refusé la publication ({e}). Vérifie le jeton et le dépôt dans les réglages de l’outil."
        return f"J’ai ouvert la pull request : {pr.get('html_url')}"

    def _branche(self, chemin, courriel, auteur, prefixe=""):
        personne = re.sub(r"[^a-z0-9-]", "-", (courriel.split("@")[0] or auteur).lower()).strip("-") or "inconnu"
        return f"redaction/{personne}/{prefixe}" + re.sub(r"[^a-z0-9-]", "-", chemin[5:-3]) + datetime.datetime.now().strftime("-%Y%m%d%H%M")

    def lire_document(self, chemin: str) -> str:
        """
        Lit un document déjà publié dans la documentation (branche main de hibou-docs), pour le relire ou le mettre à jour.
        :param chemin: Chemin du fichier dans le dépôt, sous docs/, terminé par .md (ex. docs/procedures/sauvegarde-forgejo.md).
        :return: Le contenu Markdown du document, ou la raison de l’échec.
        """
        if not re.fullmatch(r"docs/[a-z0-9][a-z0-9/_-]*\.md", chemin) or ".." in chemin:
            return "Chemin refusé. Utilise docs/<dossier>/<nom-en-minuscules>.md."
        try:
            r = self._api("GET", f"/contents/{chemin}?ref=main")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return "Ce document n’existe pas dans la documentation publiée."
            return f"Forgejo a refusé la lecture ({e})."
        return base64.b64decode(r.get("content", "")).decode()

    def mettre_a_jour_document(self, titre: str, chemin: str, contenu: str, resume: str = "", __user__: dict = {}) -> str:
        """
        Propose une nouvelle version d’un document déjà publié, par une pull request à relire. Lis-le d’abord avec lire_document.
        :param titre: Titre du document.
        :param chemin: Chemin du fichier existant, sous docs/, terminé par .md.
        :param contenu: Le document Markdown complet, en-tête YAML compris, dans sa nouvelle version.
        :param resume: Ce qui change, en une ou deux phrases.
        :return: L’adresse de la pull request, ou ce qu’il faut corriger.
        """
        if not self.valves.jeton:
            return "Aucun jeton configuré. Renseigne-le dans les réglages de l’outil."
        if not re.fullmatch(r"docs/[a-z0-9][a-z0-9/_-]*\.md", chemin) or ".." in chemin:
            return "Chemin refusé. Utilise docs/<dossier>/<nom-en-minuscules>.md."
        contenu = normaliser(contenu)
        if not contenu.startswith("---"):
            return "Le document doit commencer par son en-tête YAML (modele, titre)."
        if "<!--" in contenu:
            return "Le document contient encore des consignes du template (<!-- … -->). Remplace chacune par le contenu, puis propose à nouveau."
        auteur = (__user__ or {}).get("name") or "inconnu"
        courriel = (__user__ or {}).get("email") or ""
        branche = self._branche(chemin, courriel, auteur, "maj-")
        try:
            sha = self._api("GET", f"/contents/{chemin}?ref=main").get("sha")
        except requests.HTTPError:
            return "Ce document n’existe pas encore : publie-le comme un nouveau document."
        try:
            self._api("POST", "/branches", json={"new_branch_name": branche, "old_branch_name": "main"})
            self._api("PUT", f"/contents/{chemin}", json={
                "branch": branche, "sha": sha, "message": f"Mise à jour : {titre}",
                "content": base64.b64encode(contenu.encode()).decode(),
                **({"author": {"name": auteur, "email": courriel}} if courriel else {})})
            pr = self._api("POST", "/pulls", json={
                "head": branche, "base": "main", "title": f"Mise à jour : {titre}",
                "body": (resume + "\n\n" if resume else "") + f"Demandé par {auteur}" + (f" ({courriel})" if courriel else "")
                        + ", rédigé avec Hibou. Le runner vérifie le style, les sections et les schémas."})
        except requests.HTTPError as e:
            return f"Forgejo a refusé la mise à jour ({e}). Vérifie le jeton et le dépôt dans les réglages de l’outil."
        return f"J’ai ouvert la pull request de mise à jour : {pr.get('html_url')}"
