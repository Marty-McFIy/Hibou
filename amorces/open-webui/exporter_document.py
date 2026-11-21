"""
title: Exporter un document
author: Hibou
version: 0.2.0
description: Crée un fichier Word, PDF, PowerPoint, Excel ou Markdown à partir du texte rédigé et le propose au téléchargement dans le chat.
"""
# Hors ligne : python-docx, python-pptx et openpyxl sont dans l’image d’Open WebUI ; fpdf2 (PDF) est livré
# par le bundle dans /app/hibou-py. Le fichier appartient à la personne qui le demande : elle seule le voit.
import io, re, sys, unicodedata, uuid

sys.path.append("/app/hibou-py")

# Jetons de la charte Hibou. Document imprimé (Word, PDF) : thème Brume sur papier ; présentation : thème Nuit.
# Le code est un terminal : toujours nuit, dans les deux thèmes.
NUIT, BRUME, AMBRE = (0x0F, 0x14, 0x20), (0xE9, 0xE4, 0xD8), (0xF2, 0xB5, 0x44)
TEXTE_DOUX, FILET_FORT, ACCENT_FONCE = (0x4A, 0x54, 0x68), (0x78, 0x72, 0x62), (0x8A, 0x5F, 0x0A)   # thème Brume
PIERRE = (0x8A, 0x93, 0xA6)                                                                       # texte-doux Nuit
TITRE, TEXTE, CODE = "Fraunces", "Inter", "JetBrains Mono"
POLICES_CHARTE = "/app/backend/open_webui/static/hibou/"


def hexa(c):
    return "%02X%02X%02X" % c


def polices_pdf():
    """TTF des polices de la charte, convertis une fois depuis ses woff2 (fontTools + brotli, livrés par le bundle).
    Fraunces et Inter sont variables : on fige la taille optique et la graisse. Repli sur DejaVu si la conversion échoue."""
    import os
    cache = "/app/backend/data/cache/hibou-polices/"
    voulues = {"titre": "Fraunces-600.ttf", "texte": "Inter-400.ttf", "texte-gras": "Inter-600.ttf", "code": "JetBrainsMono-500.ttf"}
    try:
        if not all(os.path.exists(cache + f) for f in voulues.values()):
            from fontTools.ttLib import TTFont
            from fontTools.varLib import instancer
            os.makedirs(cache, exist_ok=True)
            for source, axes, cible in (("Fraunces-600", {"opsz": 24}, "Fraunces-600.ttf"), ("Inter-variable", {"wght": 400, "opsz": 14}, "Inter-400.ttf"),
                                        ("Inter-variable", {"wght": 600, "opsz": 14}, "Inter-600.ttf"), ("JetBrainsMono-500", {}, "JetBrainsMono-500.ttf")):
                f = TTFont(POLICES_CHARTE + source + ".woff2"); f.flavor = None
                if "fvar" in f:
                    noms = {a.axisTag for a in f["fvar"].axes}
                    f = instancer.instantiateVariableFont(f, {k: v for k, v in axes.items() if k in noms})
                f.save(cache + cible)
        return {k: cache + v for k, v in voulues.items()}
    except Exception:
        d = "/usr/share/fonts/truetype/dejavu/"
        return {"titre": d + "DejaVuSerif-Bold.ttf", "texte": d + "DejaVuSans.ttf", "texte-gras": d + "DejaVuSans-Bold.ttf", "code": d + "DejaVuSansMono.ttf"}


FORMATS = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "md": "text/markdown",
}


def blocs(md: str, titre: str = ""):
    """Markdown simple -> blocs (type, valeur) : titre, puce, numero, code, tableau, texte."""
    lignes = md.replace("\r\n", "\n").split("\n")
    if lignes and lignes[0].strip() == "---":  # en-tête YAML des documents Hibou : pas dans le fichier exporté
        fin = next((i for i, l in enumerate(lignes[1:], 1) if l.strip() == "---"), 0)
        lignes = lignes[fin + 1:]
    i, para = 0, []

    def vider():
        if para:
            yield ("texte", " ".join(para))
            para.clear()

    while i < len(lignes):
        l = lignes[i]
        if re.match(r"^\s*(`{3,}|~{3,})", l):
            yield from vider()
            j = i + 1
            while j < len(lignes) and not re.match(r"^\s*(`{3,}|~{3,})\s*$", lignes[j]):
                j += 1
            yield ("code", "\n".join(lignes[i + 1:j]))
            i = j + 1
            continue
        if l.lstrip().startswith("|"):
            yield from vider()
            rangs = []
            while i < len(lignes) and lignes[i].lstrip().startswith("|"):
                cellules = [c.strip() for c in lignes[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cellules if c):
                    rangs.append(cellules)
                i += 1
            yield ("tableau", rangs)
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", l)
        if m and m.group(2).strip().lower() == titre.strip().lower():
            yield from vider()
            titre = ""   # une seule fois
        elif m:
            yield from vider()
            yield ("titre", (len(m.group(1)), m.group(2).strip()))
        elif re.match(r"^\s*[-*+]\s+", l):
            yield from vider()
            yield ("puce", re.sub(r"^\s*[-*+]\s+", "", l))
        elif re.match(r"^\s*\d+[.)]\s+", l):
            yield from vider()
            yield ("numero", re.sub(r"^\s*(\d+)[.)]\s+", r"\1. ", l))
        elif not l.strip():
            yield from vider()
        else:
            para.append(l.strip())
        i += 1
    yield from vider()


def segments(texte: str):
    """« **gras** » et « `code` » dans une ligne -> [(texte, gras, code)]."""
    for m in re.finditer(r"\*\*(.+?)\*\*|`([^`]+)`|([^*`]+|[*`])", texte):
        if m.group(1) is not None:
            yield m.group(1), True, False
        elif m.group(2) is not None:
            yield m.group(2), False, True
        else:
            yield m.group(3), False, False


def brut(texte: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*|`([^`]+)`", lambda m: m.group(1) or m.group(2), texte)


def en_docx(titre, md):
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    def fond(element, couleur):  # trame d’un paragraphe ou d’une cellule
        pr = element.get_or_add_pPr() if hasattr(element, "get_or_add_pPr") else element.get_or_add_tcPr()
        shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), hexa(couleur)); pr.append(shd)

    doc = Document()
    doc.core_properties.title = titre
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size, normal.font.color.rgb = TEXTE, Pt(11), RGBColor(*NUIT)
    for nom in ("Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        st = doc.styles[nom]
        st.font.name, st.font.color.rgb, st.font.bold = TITRE, RGBColor(*NUIT), True
    doc.add_heading(titre, 0)
    for genre, v in blocs(md, titre):
        if genre == "titre":
            doc.add_heading(brut(v[1]), min(v[0], 4))
        elif genre in ("texte", "puce", "numero"):
            p = doc.add_paragraph(style={"texte": None, "puce": "List Bullet", "numero": None}[genre])
            for t, gras, code in segments(v):
                r = p.add_run(t)
                r.bold = gras
                if code:
                    r.font.name = CODE
        elif genre == "code":  # terminal : nuit, texte brume
            p = doc.add_paragraph()
            fond(p._p, NUIT)
            r = p.add_run(v)
            r.font.name, r.font.size, r.font.color.rgb = CODE, Pt(9), RGBColor(*BRUME)
        elif genre == "tableau" and v:
            n = max(len(r) for r in v)
            t = doc.add_table(rows=len(v), cols=n)
            t.style = "Table Grid"
            for i, rang in enumerate(v):
                for j, c in enumerate(rang):
                    cel = t.cell(i, j)
                    cel.text = brut(c)
                    if i == 0:  # en-tête : accent, texte sur-accent
                        fond(cel._tc, AMBRE)
                        for r in cel.paragraphs[0].runs:
                            r.bold, r.font.color.rgb = True, RGBColor(*NUIT)
    sortie = io.BytesIO()
    doc.save(sortie)
    return sortie.getvalue()


def en_pdf(titre, md):
    from fpdf import FPDF
    from fpdf.fonts import FontFace
    pol = polices_pdf()
    pdf = FPDF(format="A4")
    pdf.add_font("Titre", "", pol["titre"])
    pdf.add_font("Texte", "", pol["texte"]); pdf.add_font("Texte", "B", pol["texte-gras"])
    pdf.add_font("Code", "", pol["code"])
    pdf.set_title(titre)
    pdf.set_auto_page_break(True, 18)
    pdf.add_page()
    pdf.set_fill_color(*AMBRE)
    pdf.rect(0, 0, 210, 4, "F")
    pdf.set_font("Titre", "", 24)
    pdf.set_text_color(*NUIT)
    pdf.multi_cell(0, 11, titre, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for genre, v in blocs(md, titre):
        pdf.set_text_color(*NUIT)
        if genre == "titre":
            pdf.ln(3)
            pdf.set_font("Titre", "", {1: 18, 2: 15, 3: 13}.get(v[0], 12))
            pdf.multi_cell(0, 8, brut(v[1]), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif genre in ("texte", "puce", "numero"):
            pdf.set_font("Texte", "", 11)
            texte = re.sub(r"`([^`]+)`", r"\1", v)
            if genre != "texte":
                pdf.set_x(pdf.l_margin + 5)
                texte = ("• " if genre == "puce" else "") + texte
            pdf.multi_cell(0, 6, texte, markdown=True, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif genre == "code":  # terminal : nuit, texte brume
            pdf.set_font("Code", "", 9)
            pdf.set_fill_color(*NUIT)
            pdf.set_text_color(*BRUME)
            pdf.multi_cell(0, 5.5, v, fill=True, padding=(2, 3), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif genre == "tableau" and v:
            pdf.set_font("Texte", "", 9)
            pdf.set_fill_color(255, 255, 255)
            pdf.set_draw_color(*FILET_FORT)
            n = max(len(r) for r in v)
            with pdf.table(headings_style=FontFace(emphasis="BOLD", color=NUIT, fill_color=AMBRE)) as t:
                for rang in v:
                    ligne = t.row()
                    for c in rang + [""] * (n - len(rang)):
                        ligne.cell(brut(c))
            pdf.ln(2)
    return bytes(pdf.output())


def en_pptx(titre, md):
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Emu, Pt
    pres = Presentation()

    def diapo(gabarit, titre_diapo):  # thème Nuit : fond nuit, titres Fraunces brume, filet d’ambre
        d = pres.slides.add_slide(pres.slide_layouts[gabarit])
        d.background.fill.solid(); d.background.fill.fore_color.rgb = RGBColor(*NUIT)
        barre = d.shapes.add_shape(1, 0, 0, pres.slide_width, Emu(91440))
        barre.fill.solid(); barre.fill.fore_color.rgb = RGBColor(*AMBRE); barre.line.fill.background()
        d.shapes.title.text = titre_diapo
        for r in d.shapes.title.text_frame.paragraphs[0].runs:
            r.font.name, r.font.color.rgb, r.font.bold = TITRE, RGBColor(*BRUME), True
        if len(d.placeholders) > 1:
            corps = d.placeholders[1].text_frame
            corps.text = ""
            for r in corps.paragraphs[0].runs:
                r.font.name, r.font.color.rgb = TEXTE, RGBColor(*PIERRE)
            return corps
        return None

    sous = diapo(0, titre)
    if sous is not None:
        sous.text = "Hibou"
        for r in sous.paragraphs[0].runs:
            r.font.name, r.font.color.rgb = TEXTE, RGBColor(*PIERRE)
    corps = None
    for genre, v in blocs(md, titre):
        if genre == "titre" and v[0] <= 2:
            corps = diapo(1, brut(v[1]))
            continue
        if corps is None:
            corps = diapo(1, titre)
        lignes = {"tableau": lambda: [" · ".join(brut(c) for c in r) for r in v],
                  "code": lambda: v.split("\n")[:12],
                  "titre": lambda: [brut(v[1])]}.get(genre, lambda: [brut(v)])()
        for t in lignes:
            p = corps.paragraphs[0] if not corps.paragraphs[0].text else corps.add_paragraph()
            p.text = t
            for r in p.runs:
                r.font.name = CODE if genre == "code" else TEXTE
                r.font.color.rgb = RGBColor(*(AMBRE if genre == "code" and t.lstrip().startswith("$") else BRUME))
                r.font.size = Pt(16 if genre == "code" else 20)
    sortie = io.BytesIO()
    pres.save(sortie)
    return sortie.getvalue()


def en_xlsx(titre, md):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    wb.remove(wb.active)
    tableaux = [v for g, v in blocs(md) if g == "tableau" and v]
    if not tableaux:  # pas de tableau : une ligne par paragraphe
        tableaux = [[[brut(v if isinstance(v, str) else v[1])] for g, v in blocs(md) if g != "code"]]
    for k, rangs in enumerate(tableaux, 1):
        f = wb.create_sheet(f"Tableau {k}" if len(tableaux) > 1 else titre[:31] or "Hibou")
        for rang in rangs:
            f.append([brut(c) for c in rang])
        for ligne in f.iter_rows():
            for c in ligne:
                c.font = Font(name=TEXTE, color=hexa(NUIT))
        for c in f[1]:  # en-tête : accent, texte sur-accent
            c.font = Font(name=TEXTE, bold=True, color=hexa(NUIT))
            c.fill = PatternFill("solid", fgColor=hexa(AMBRE))
        for col in f.columns:
            f.column_dimensions[col[0].column_letter].width = min(60, max(10, *(len(str(c.value or "")) + 2 for c in col)))
    sortie = io.BytesIO()
    wb.save(sortie)
    return sortie.getvalue()


class Tools:
    def __init__(self):
        pass

    async def exporter_document(self, titre: str, contenu: str, format: str = "docx",
                                __user__: dict = {}, __event_emitter__=None) -> str:
        """
        Crée un fichier à télécharger (Word, PDF, PowerPoint, Excel ou Markdown) à partir d’un texte en Markdown,
        et l’attache à la réponse dans le chat. À utiliser quand la personne demande un fichier, un export, un .docx, un .pdf…
        :param titre: Titre du document (aussi utilisé pour le nom du fichier).
        :param contenu: Le texte complet en Markdown : titres #, listes, tableaux |, blocs de code.
        :param format: docx, pdf, pptx, xlsx ou md.
        :return: Le lien de téléchargement, ou ce qui manque.
        """
        from open_webui.models.files import FileForm, Files
        from open_webui.storage.provider import Storage

        format = format.lower().lstrip(".")
        if format not in FORMATS:
            return f"Format inconnu : {format}. Choisis parmi {', '.join(FORMATS)}."
        if not (__user__ or {}).get("id"):
            return "Je ne sais pas pour qui créer le fichier : relance depuis le chat."
        try:
            donnees = {"docx": en_docx, "pdf": en_pdf, "pptx": en_pptx, "xlsx": en_xlsx,
                       "md": lambda t, m: m.encode()}[format](titre, contenu)
        except ModuleNotFoundError as e:
            return f"Export {format} indisponible sur ce serveur ({e.name} absent du bundle)."
        sans_accents = unicodedata.normalize("NFKD", titre).encode("ascii", "ignore").decode().lower()   # « Redémarrage » -> « redemarrage »
        nom = (re.sub(r"[^a-z0-9]+", "-", sans_accents).strip("-")[:60] or "document") + "." + format
        ident = str(uuid.uuid4())
        _, chemin = Storage.upload_file(io.BytesIO(donnees), f"{ident}_{nom}", {"OpenWebUI-User-Id": __user__["id"], "OpenWebUI-File-Id": ident})
        fichier = await Files.insert_new_file(__user__["id"], FileForm(id=ident, filename=nom, path=chemin, data={},
                                              meta={"name": nom, "content_type": FORMATS[format], "size": len(donnees)}))
        url = f"/api/v1/files/{fichier.id}/content"
        if __event_emitter__:
            await __event_emitter__({"type": "files", "data": {"files": [
                {"type": "file", "id": fichier.id, "url": f"/api/v1/files/{fichier.id}", "name": nom,
                 "size": len(donnees), "status": "uploaded", "file": fichier.model_dump()}]}})
        return f"Fichier prêt : [{nom}]({url}) ({len(donnees) // 1024 + 1} Ko). Il est attaché à cette réponse."
