"""
title: Compression du contexte
author: Hibou
version: 0.2.0
description: Quand une conversation approche de la limite du modèle, résume les anciens échanges et garde les derniers tels quels. Bouton dans la barre de saisie pour la couper.
"""
# Sans ce filtre, Open WebUI renvoie tout l’historique : au-delà du contexte du modèle, le serveur refuse la requête
# (« exceeds the available context size ») et la conversation est perdue. Le filtre passe avant l’ajout des extraits
# de la base de connaissances : il vise la moitié du contexte pour leur laisser la place.
# Chacun garde la main : bouton « Compression du contexte » dans la barre de saisie (actif par défaut sur les modèles Hibou),
# et réglage personnel « Ne jamais compresser mes conversations ».
import json, os

import aiohttp
from pydantic import BaseModel, Field

CONSIGNE = ("Tu résumes une conversation entre une personne et l’assistant Hibou, pour qu’il puisse la poursuivre. "
            "Garde les faits, décisions, chiffres, noms de fichiers, commandes et demandes encore ouvertes. "
            "Écris en français, en puces, 250 mots au plus. Pas d’introduction.")


def texte(m) -> str:
    c = m.get("content")
    if isinstance(c, list):  # message multimodal : seul le texte compte, les images sont signalées
        return " ".join(p.get("text", "[image]") if isinstance(p, dict) else str(p) for p in c)
    return c or ""


def jetons(messages) -> int:
    return sum(len(texte(m)) // 3 + 4 for m in messages)  # estimation prudente pour le français


class Filter:
    class Valves(BaseModel):
        contextes: str = Field("{}", description="Contexte de chaque modèle servi, en JSON (écrit par « hibou mettre-a-jour »).")
        seuil: float = Field(0.5, description="Part du contexte au-delà de laquelle les anciens échanges sont résumés.")
        garder: int = Field(4, description="Nombre minimal de derniers messages gardés tels quels.")

    class UserValves(BaseModel):
        jamais: bool = Field(False, description="Ne jamais compresser mes conversations, même si le bouton est actif.")

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True   # bouton dans la barre de saisie : le filtre n’agit que s’il est activé pour la conversation
        self.icon = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgd2lkdGg9IjI0IiBoZWlnaHQ9IjI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM2Qjc2OTAiIHN0cm9rZS13aWR0aD0iMS43NSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNNCA2aDE2Ij48L3BhdGg+PHBhdGggZD0iTTQgMTBoMTYiPjwvcGF0aD48cGF0aCBkPSJNNCAxNGgxMCI+PC9wYXRoPjxwYXRoIGQ9Ik00IDE4aDYiPjwvcGF0aD48L3N2Zz4="
        self.resumes = {}  # conversation -> (nombre de messages déjà résumés, résumé)

    async def _resumer(self, modele: str, resume: str, messages) -> str:
        urls = os.environ.get("OPENAI_API_BASE_URLS", os.environ.get("OPENAI_API_BASE_URL", "")).split(";")
        cles = os.environ.get("OPENAI_API_KEYS", os.environ.get("OPENAI_API_KEY", "")).split(";")
        echanges = "\n\n".join(f"{m['role']} : {texte(m)}" for m in messages)
        corps = {"model": modele, "temperature": 0.2, "max_tokens": 600, "messages": [
            {"role": "system", "content": CONSIGNE},
            {"role": "user", "content": (f"Résumé existant :\n{resume}\n\n" if resume else "") + f"Échanges à ajouter :\n{echanges}"}]}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as s:
            async with s.post(f"{urls[0].rstrip('/')}/chat/completions", json=corps,
                              headers={"Authorization": f"Bearer {cles[0] if cles else ''}"}) as r:
                r.raise_for_status()
                return (await r.json())["choices"][0]["message"]["content"].strip()

    async def inlet(self, body: dict, __user__: dict = None, __model__: dict = None, __metadata__: dict = None, __event_emitter__=None) -> dict:
        reglages = (__user__ or {}).get("valves")
        if reglages is not None and getattr(reglages, "jamais", False):
            return body
        modele = ((__model__ or {}).get("info") or {}).get("base_model_id") or (__model__ or {}).get("id") or body.get("model")
        contexte = json.loads(self.valves.contextes or "{}").get(modele)
        messages = body.get("messages") or []
        if not contexte or jetons(messages) <= contexte * self.valves.seuil:
            return body
        budget = contexte * self.valves.seuil
        systeme = [m for m in messages if m.get("role") == "system"]
        echanges = [m for m in messages if m.get("role") != "system"]
        # Derniers messages gardés tels quels : au moins « garder », plus tant que la place le permet.
        n = min(self.valves.garder, len(echanges))
        while n < len(echanges) and jetons(systeme + echanges[-(n + 1):]) <= budget * 0.6:
            n += 1
        anciens, recents = echanges[:-n] if n else echanges, echanges[-n:] if n else []
        if not anciens:
            return body
        cle = (__metadata__ or {}).get("chat_id") or ""
        deja, resume = self.resumes.get(cle, (0, ""))
        if deja > len(anciens):
            deja, resume = 0, ""
        a_resumer = anciens[deja:]
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": f"Conversation longue : je résume {len(anciens)} anciens messages.", "done": False}})
        try:
            # Par morceaux qui tiennent dans le contexte du modèle, en enrichissant le même résumé.
            morceau = []
            for m in a_resumer:
                if morceau and jetons(morceau + [m]) > budget * 0.8:
                    resume = await self._resumer(modele, resume, morceau)
                    morceau = []
                morceau.append(m)
            if morceau:
                resume = await self._resumer(modele, resume, morceau)
            self.resumes[cle] = (len(anciens), resume)
            note = f"Résumé des échanges précédents (compression automatique Hibou) :\n{resume}"
            fin = f"{len(anciens)} anciens messages résumés ; les {len(recents)} derniers sont gardés tels quels. Bouton « Compression du contexte » pour la couper."
        except Exception as e:  # le résumé a échoué : on retire les plus anciens plutôt que de perdre la conversation
            note = "Les premiers échanges de cette conversation ont été retirés : elle dépassait la mémoire du modèle."
            fin = f"Résumé impossible ({e.__class__.__name__}) : {len(anciens)} anciens messages retirés."
        # Un seul message système, en tête : certains modèles (Qwen) refusent un second message système.
        if systeme:
            systeme = [{**systeme[0], "content": f"{texte(systeme[0])}\n\n{note}"}] + systeme[1:]
        else:
            systeme = [{"role": "system", "content": note}]
        body["messages"] = systeme + recents
        if __event_emitter__:
            await __event_emitter__({"type": "status", "data": {"description": fin, "done": True}})
        return body
