"""Genera los manuales de TodoGas CMMS en PDF y Word, con las capturas insertadas.

    backend/.venv/Scripts/python.exe docs/manuales/herramientas/generar_documentos.py

Entradas (no se modifican):
    docs/manuales/manual-completo.md, manual-rapido.md, glosario.md
    docs/manuales/capturas-pendientes.md   (tabla: numero, manual, descripcion)
    docs/manuales/herramientas/capturas.json (numero -> archivo PNG)
    frontend/public/logo.png               (logo de la portada)

Salida (se regenera; no va a git):
    docs/manuales/salida/manual-completo.pdf/.docx, manual-rapido.pdf/.docx, glosario.pdf/.docx

Cada marcador `> [CAPTURA: descripcion — Rol, Web]` se cambia por la imagen de la captura
(el n-esimo marcador de un manual es la n-esima fila de ese manual en la tabla). Si la captura
no existe, se deja un recuadro gris «Captura pendiente: ...» y el generador lo reporta al final.

PDF: Markdown -> HTML (paquete `markdown`) -> PDF con WeasyPrint.
Word: Pandoc si esta instalado; si no, python-docx.
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
MANUALES = ROOT / "docs" / "manuales"
SALIDA = MANUALES / "salida"
CAPTURAS_JSON = MANUALES / "herramientas" / "capturas.json"
CAPTURAS_MD = MANUALES / "capturas-pendientes.md"
LOGO = ROOT / "frontend" / "public" / "logo.png"

# (nombre del archivo sin extension, etiqueta de la tabla de capturas o None)
DOCUMENTOS = [
    ("manual-completo", "completo"),
    ("manual-rapido", "rapido"),
    ("glosario", None),
]

# Forma: "> [CAPTURA: descripcion — Rol, Web]"; a veces termina en " (captura N)" fuera del corchete.
MARCADOR = re.compile(r"^> \[CAPTURA:\s*(.*?)\]\s*(\(captura \d+\))?\s*$")
ANCHO_MAX_CM = 15.5
ALTO_MAX_CM = 20.0

CSS = """
@page {
  size: A4;
  margin: 2.3cm 2cm 2.2cm 2cm;
  @top-right { content: "{{HEADER}}"; font-family: "Segoe UI", Arial, sans-serif; font-size: 8pt; color: #6b7280; }
  @bottom-center { content: "Página " counter(page) " de " counter(pages); font-family: "Segoe UI", Arial, sans-serif; font-size: 8.5pt; color: #6b7280; }
}
@page :first {
  @top-right { content: none; }
  @bottom-center { content: none; }
}
html { font-family: "Segoe UI", Arial, Helvetica, sans-serif; }
body { font-size: 10.5pt; line-height: 1.45; color: #1f2937; }
.portada { text-align: center; padding-top: 4.2cm; page-break-after: always; }
.portada img.logo { width: 7.5cm; margin-bottom: 1.6cm; }
.portada .titulo { font-size: 30pt; color: #0b4f6c; margin: 0 0 0.3cm 0; border: none; }
.portada .subtitulo { font-size: 17pt; color: #1f2937; font-weight: normal; margin: 0 0 0.8cm 0; }
.portada .version { font-size: 11pt; color: #4b5563; }
h1 { font-size: 20pt; color: #0b4f6c; border-bottom: 2px solid #0b4f6c; padding-bottom: 4pt; }
h2 { font-size: 16pt; color: #0b4f6c; margin-top: 20pt; page-break-after: avoid; bookmark-level: 1; }
h3 { font-size: 13pt; color: #0b4f6c; margin-top: 16pt; page-break-after: avoid; bookmark-level: 2; }
h4 { font-size: 11pt; color: #1f2937; margin-top: 12pt; page-break-after: avoid; bookmark-level: 3; }
p { margin: 5pt 0; orphans: 3; widows: 3; }
a { color: #0b4f6c; text-decoration: none; }
ul, ol { margin: 4pt 0 6pt 0; padding-left: 1.2cm; }
li { margin: 2pt 0; }
hr { border: none; border-top: 1px solid #d1d5db; margin: 14pt 0; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt; background: #f3f4f6; padding: 0 2pt; }
pre { background: #f3f4f6; padding: 6pt; font-size: 9pt; white-space: pre-wrap; }
blockquote { border-left: 3pt solid #0b4f6c; background: #f1f7fa; margin: 8pt 0; padding: 4pt 10pt; color: #1f2937; }
blockquote p { margin: 3pt 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 10pt 0; font-size: 9.5pt; }
th, td { border: 1px solid #9ca3af; padding: 4pt 6pt; vertical-align: top; text-align: left; }
th { background: #e6f0f4; color: #0b4f6c; }
tr { page-break-inside: avoid; }
p > img, img { display: block; max-width: 100%; height: auto; margin: 8pt auto 2pt auto; border: 1px solid #d1d5db; page-break-inside: avoid; }
p em { color: #4b5563; font-size: 9pt; }
.captura-pendiente { background: #e5e7eb; border: 1px dashed #6b7280; color: #374151; font-style: italic; text-align: center; padding: 16pt 10pt; margin: 10pt 0; page-break-inside: avoid; }
"""


# ---------------------------------------------------------------------------
# Lectura de tablas y de capturas
# ---------------------------------------------------------------------------

def norm(texto):
    """Minusculas, sin acentos ni signos, para comparar descripciones."""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\W+", " ", t.lower()).strip()


def leer_tabla_capturas():
    """Devuelve las filas de capturas-pendientes.md: n, archivo, manual, descripcion."""
    filas = []
    for linea in CAPTURAS_MD.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\|\s*\d+\s*\|", linea):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) < 5:
            print(f"AVISO: fila con pocas columnas en capturas-pendientes.md: {celdas[0]}")
            continue
        filas.append({
            "n": int(celdas[0]),
            "archivo": celdas[1].strip("`"),
            "manual": norm(celdas[2].split(":")[0]),
            "descr": celdas[4],
        })
    return filas


def leer_capturas_json():
    datos = json.loads(CAPTURAS_JSON.read_text(encoding="utf-8"))
    return {c["n"]: c for c in datos["capturas"]}


# ---------------------------------------------------------------------------
# Preprocesado del Markdown
# ---------------------------------------------------------------------------

def asignar_filas(pies, filas, informe, nombre):
    """Empareja cada marcador con una fila de la tabla del mismo manual, por similitud de la descripcion.

    El orden de los marcadores en el Markdown no es el de la tabla, por eso no se empareja por posicion.
    Emparejamiento voraz: primero los pares mas parecidos. Devuelve (fila, similitud) por marcador."""
    import difflib
    pares = []
    for i, pie in enumerate(pies):
        for f in filas:
            s = difflib.SequenceMatcher(None, norm(pie), norm(f["descr"])).ratio()
            pares.append((s, i, f["n"]))
    pares.sort(reverse=True)
    por_indice = [None] * len(pies)
    usados = set()
    por_n = {f["n"]: f for f in filas}
    for s, i, n in pares:
        if por_indice[i] is None and n not in usados and s >= 0.5:
            por_indice[i] = (por_n[n], s)
            usados.add(n)
    for i, pie in enumerate(pies):
        if por_indice[i] is None:
            informe["avisos"].append(f"{nombre}: marcador sin fila en la tabla: {pie[:70]}")
        elif por_indice[i][1] < 0.8:
            informe["avisos"].append(
                f"{nombre}: coincidencia dudosa ({por_indice[i][1]:.2f}) con la fila {por_indice[i][0]['n']}:\n"
                f"   md:    {pie[:90]}\n   tabla: {por_indice[i][0]['descr'][:90]}")
    sin_marcador = [f["n"] for f in filas if f["n"] not in usados]
    if sin_marcador:
        informe["avisos"].append(f"{nombre}: filas de la tabla sin marcador: {sin_marcador}")
    return por_indice


def procesar_md(texto, nombre, filas, capturas, pandoc, informe):
    """Cambia cada marcador [CAPTURA: ...] por imagen o por recuadro pendiente."""
    lineas = texto.splitlines()
    marcas = []  # (indice de linea, descripcion sin rol, numero explicito o None)
    for idx, linea in enumerate(lineas):
        m = MARCADOR.match(linea)
        if m:
            inner = m.group(1).strip()
            pie = inner.rsplit(" — ", 1)[0].strip()
            explicito = int(m.group(2)[len("(captura "):-1]) if m.group(2) else None
            marcas.append((idx, pie, explicito))
    asignados = asignar_filas([p for _, p, _ in marcas], filas, informe, nombre)

    salida = []
    k = 0
    for idx, linea in enumerate(lineas):
        if not MARCADOR.match(linea):
            salida.append(linea)
            continue
        _, pie, explicito = marcas[k]
        fila = asignados[k][0] if asignados[k] else None
        if explicito is not None and (fila is None or fila["n"] != explicito):
            informe["avisos"].append(f"{nombre}: el marcador dice (captura {explicito}) y la tabla no coincide")
        k += 1

        n = fila["n"] if fila else None
        cap = capturas.get(n) if n is not None else None
        ruta = ROOT / cap["archivo"] if cap and cap.get("archivo") else None
        salida.append("")
        if ruta is not None and ruta.exists():
            alt = pie.replace("[", "").replace("]", "")
            src = ruta.as_posix() if pandoc else ruta.as_uri()
            salida.append(f"![{alt}]({src})")
            salida.append("")
            salida.append(f"*{pie}*")
            informe["insertadas"] += 1
        else:
            informe["pendientes"].append((n, pie))
            if pandoc:
                salida.append(f"> **Captura pendiente:** {pie}")
            else:
                salida.append(f'<div class="captura-pendiente">Captura pendiente: {html.escape(pie, quote=False)}</div>')
        salida.append("")
    return "\n".join(salida) + "\n"


def separar_portada(texto):
    """Quita el titulo, el subtitulo y la version del Markdown; se usan en la portada."""
    titulo = sub = version = None
    resto = []
    for linea in texto.splitlines():
        if titulo is None and linea.startswith("# "):
            titulo = linea[2:].strip()
            continue
        if sub is None and linea.startswith("## "):
            sub = linea[3:].strip()
            continue
        if version is None and linea.startswith("**Versión"):
            version = linea.strip().strip("*").strip()
            continue
        resto.append(linea)
    return titulo or "TodoGas CMMS", sub or "", version or "", "\n".join(resto)


def markdown_a_html(cuerpo):
    import markdown
    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"])
    return md.convert(cuerpo)


# ---------------------------------------------------------------------------
# PDF (WeasyPrint)
# ---------------------------------------------------------------------------

def generar_pdf(md_tmp_texto, titulo, sub, version, cabecera, destino):
    from weasyprint import HTML

    cuerpo = markdown_a_html(md_tmp_texto)
    portada = (
        '<section class="portada">'
        f'<img class="logo" src="{LOGO.as_uri()}" alt="Logo TodoGas">'
        f'<h1 class="titulo">{html.escape(titulo)}</h1>'
        f'<p class="subtitulo">{html.escape(sub)}</p>'
        f'<p class="version">{html.escape(version)}</p>'
        "</section>"
    )
    documento = (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f"<title>{html.escape(sub or titulo)}</title>"
        f"<style>{CSS.replace('{{HEADER}}', html.escape(cabecera, quote=True))}</style>"
        f"</head><body>{portada}<main>{cuerpo}</main></body></html>"
    )
    HTML(string=documento, base_url=str(ROOT)).write_pdf(str(destino))


# ---------------------------------------------------------------------------
# Word: Pandoc si esta instalado
# ---------------------------------------------------------------------------

def generar_docx_pandoc(md_tmp, titulo, sub, destino):
    subprocess.run(
        ["pandoc", str(md_tmp), "-f", "markdown", "-o", str(destino),
         "--resource-path", str(ROOT), "--toc", "--toc-depth=2",
         "-M", f"title={titulo}", "-M", f"subtitle={sub}", "-M", "lang=es"],
        check=True)


# ---------------------------------------------------------------------------
# Word: python-docx (sin Pandoc)
# ---------------------------------------------------------------------------

class Nodo:
    def __init__(self, tag, attrs=None, texto=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.texto = texto
        self.hijos = []


class Arbol(HTMLParser):
    VACIOS = {"img", "br", "hr", "meta", "input", "link"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = Nodo("raiz")
        self.pila = [self.raiz]

    def handle_starttag(self, tag, attrs):
        nodo = Nodo(tag, attrs)
        self.pila[-1].hijos.append(nodo)
        if tag not in self.VACIOS:
            self.pila.append(nodo)

    def handle_startendtag(self, tag, attrs):
        self.pila[-1].hijos.append(Nodo(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.pila) - 1, 0, -1):
            if self.pila[i].tag == tag:
                del self.pila[i:]
                break

    def handle_data(self, data):
        self.pila[-1].hijos.append(Nodo("#texto", texto=data))


def _texto_plano(nodo):
    if nodo.tag == "#texto":
        return nodo.texto
    return "".join(_texto_plano(h) for h in nodo.hijos)


def _sombrear(pr, color):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    pr.append(shd)


def _campo(parrafo, instruccion):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def fld(tipo):
        r = parrafo.add_run()
        e = OxmlElement("w:fldChar")
        e.set(qn("w:fldCharType"), tipo)
        r._r.append(e)

    fld("begin")
    r = parrafo.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instruccion
    r._r.append(it)
    fld("separate")
    parrafo.add_run("1")
    fld("end")


def _formato(run, fmt):
    from docx.shared import Pt
    if fmt.get("bold"):
        run.bold = True
    if fmt.get("italic"):
        run.italic = True
    if fmt.get("mono"):
        run.font.name = "Consolas"
        run.font.size = Pt(9)


def _imagen(parrafo, src):
    from PIL import Image
    from docx.shared import Cm
    from urllib.request import url2pathname
    ruta = Path(url2pathname(urlparse(src).path)) if src.startswith("file:") else Path(src)
    if not ruta.exists():
        parrafo.add_run("[imagen no encontrada]")
        return
    with Image.open(ruta) as im:
        ancho, alto = im.size
    ancho_cm = ANCHO_MAX_CM
    if ancho_cm * alto / ancho > ALTO_MAX_CM:
        ancho_cm = ALTO_MAX_CM * ancho / alto
    parrafo.add_run().add_picture(str(ruta), width=Cm(ancho_cm))


def _inline(nodos, parrafo, fmt):
    for h in nodos:
        if h.tag == "#texto":
            r = parrafo.add_run(h.texto.replace("\n", " "))
            _formato(r, fmt)
        elif h.tag == "br":
            parrafo.add_run().add_break()
        elif h.tag == "img":
            _imagen(parrafo, h.attrs.get("src", ""))
        elif h.tag in ("strong", "b"):
            _inline(h.hijos, parrafo, {**fmt, "bold": True})
        elif h.tag in ("em", "i"):
            _inline(h.hijos, parrafo, {**fmt, "italic": True})
        elif h.tag == "code":
            _inline(h.hijos, parrafo, {**fmt, "mono": True})
        else:
            _inline(h.hijos, parrafo, fmt)


def _lista(doc, nodo, nivel):
    from docx.shared import Cm, Pt
    numero = int(nodo.attrs.get("start", 1))
    for li in [h for h in nodo.hijos if h.tag == "li"]:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.7 * (nivel + 1))
        pf.first_line_indent = Cm(-0.5)
        pf.space_after = Pt(3)
        if nodo.tag == "ol":
            p.add_run(f"{numero}. ")
            numero += 1
        else:
            p.add_run("• ")
        _inline([h for h in li.hijos if h.tag not in ("ul", "ol")], p, {})
        for anidada in [h for h in li.hijos if h.tag in ("ul", "ol")]:
            _lista(doc, anidada, nivel + 1)


def _tabla(doc, nodo):
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    filas = []
    for sec in nodo.hijos:
        if sec.tag in ("thead", "tbody", "tfoot"):
            for tr in sec.hijos:
                if tr.tag == "tr":
                    filas.append((sec.tag == "thead", [c for c in tr.hijos if c.tag in ("th", "td")]))
        elif sec.tag == "tr":
            filas.append((False, [c for c in sec.hijos if c.tag in ("th", "td")]))
    if not filas:
        return
    ncols = max(len(c) for _, c in filas) or 1
    tabla = doc.add_table(rows=len(filas), cols=ncols)
    tabla.style = "Table Grid"
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (cabecera, celdas) in enumerate(filas):
        for j, celda in enumerate(celdas):
            es_th = cabecera or celda.tag == "th"
            cel = tabla.cell(i, j)
            p = cel.paragraphs[0]
            _inline(celda.hijos, p, {"bold": es_th})
            for r in p.runs:
                r.font.size = Pt(9.5)
            if es_th:
                _sombrear(cel._tc.get_or_add_tcPr(), "E6F0F4")
        if cabecera:
            trPr = tabla.rows[i]._tr.get_or_add_trPr()
            e = OxmlElement("w:tblHeader")
            e.set(qn("w:val"), "true")
            trPr.append(e)
    doc.add_paragraph()


def _pendiente(doc, texto):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    tabla = doc.add_table(rows=1, cols=1)
    tabla.style = "Table Grid"
    cel = tabla.cell(0, 0)
    _sombrear(cel._tc.get_or_add_tcPr(), "D9D9D9")
    p = cel.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto)
    r.italic = True
    doc.add_paragraph()


def _bloques(doc, nodos):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt
    for n in nodos:
        t = n.tag
        clases = n.attrs.get("class", "")
        if t == "#texto":
            if n.texto.strip():
                _inline([n], doc.add_paragraph(), {})
        elif re.fullmatch(r"h[1-6]", t):
            p = doc.add_heading(level=min(int(t[1]), 4))
            _inline(n.hijos, p, {})
        elif t == "p":
            p = doc.add_paragraph()
            solo_imagen = all(h.tag == "img" or (h.tag == "#texto" and not h.texto.strip()) for h in n.hijos) \
                and any(h.tag == "img" for h in n.hijos)
            if solo_imagen:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _inline(n.hijos, p, {})
            p.paragraph_format.space_after = Pt(6)
        elif t in ("ul", "ol"):
            _lista(doc, n, 0)
        elif t == "table":
            _tabla(doc, n)
        elif t == "blockquote":
            for h in n.hijos:
                if h.tag == "p":
                    p = doc.add_paragraph()
                    p.paragraph_format.left_indent = Cm(0.5)
                    _sombrear(p._p.get_or_add_pPr(), "EEF5F8")
                    _inline(h.hijos, p, {})
                elif h.tag in ("ul", "ol"):
                    _lista(doc, h, 0)
        elif t == "pre":
            p = doc.add_paragraph()
            r = p.add_run(_texto_plano(n))
            r.font.name = "Consolas"
            r.font.size = Pt(9)
        elif t == "div" and "captura-pendiente" in clases:
            texto = _texto_plano(n).strip()
            _pendiente(doc, texto)
        elif t == "hr":
            doc.add_paragraph()
        else:
            _bloques(doc, n.hijos)


def generar_docx_python(cuerpo_html, titulo, sub, version, cabecera, destino):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(10.5)

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    sec.different_first_page_header_footer = True

    # Portada
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(70)
    p.add_run().add_picture(str(LOGO), width=Cm(7.5))
    for texto, tam, negrita, color in [
        (titulo, 28, True, RGBColor(0x0B, 0x4F, 0x6C)),
        (sub, 17, False, RGBColor(0x1F, 0x29, 0x37)),
        (version, 11, False, RGBColor(0x4B, 0x55, 0x63)),
    ]:
        q = doc.add_paragraph()
        q.alignment = WD_ALIGN_PARAGRAPH.CENTER
        q.paragraph_format.space_before = Pt(10)
        r = q.add_run(texto)
        r.font.size = Pt(tam)
        r.bold = negrita
        r.font.color.rgb = color
    doc.add_page_break()

    # Encabezado y pie de pagina (no aparecen en la portada)
    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    rh = hp.add_run(cabecera)
    rh.font.size = Pt(8)
    rh.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.add_run("Página ")
    _campo(fp, "PAGE")
    fp.add_run(" de ")
    _campo(fp, "NUMPAGES")
    for r in fp.runs:
        r.font.size = Pt(8.5)

    arbol = Arbol()
    arbol.feed(cuerpo_html)
    arbol.close()
    _bloques(doc, arbol.raiz.hijos)
    doc.save(str(destino))


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solo", nargs="*", choices=[d[0] for d in DOCUMENTOS],
                    help="genera solo estos documentos")
    args = ap.parse_args()

    filas = leer_tabla_capturas()
    capturas = leer_capturas_json()
    por_manual = {
        "completo": [f for f in filas if f["manual"] == "completo"],
        "rapido": [f for f in filas if f["manual"] == "rapido"],
        None: [],
    }
    pandoc = shutil.which("pandoc")
    print(f"Word: {'Pandoc ' + pandoc if pandoc else 'python-docx (Pandoc no esta instalado)'}")

    SALIDA.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="todogas_manuales_"))
    resumen = []
    try:
        for nombre, clave in DOCUMENTOS:
            if args.solo and nombre not in args.solo:
                continue
            texto = (MANUALES / f"{nombre}.md").read_text(encoding="utf-8")
            informe = {"insertadas": 0, "pendientes": [], "avisos": []}
            md = procesar_md(texto, nombre, por_manual[clave], capturas, bool(pandoc), informe)
            md_tmp = tmp / f"{nombre}.md"
            md_tmp.write_text(md, encoding="utf-8")

            titulo, sub, version, cuerpo = separar_portada(md)
            cabecera = f"TodoGas CMMS · {sub}" if sub else "TodoGas CMMS"

            pdf = SALIDA / f"{nombre}.pdf"
            generar_pdf(cuerpo, titulo, sub, version, cabecera, pdf)

            docx = SALIDA / f"{nombre}.docx"
            if pandoc:
                generar_docx_pandoc(md_tmp, titulo, sub, docx)
            else:
                cuerpo_html = markdown_a_html(cuerpo)
                generar_docx_python(cuerpo_html, titulo, sub, version, cabecera, docx)

            resumen.append((nombre, informe, pdf, docx))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    for nombre, informe, pdf, docx in resumen:
        print(f"== {nombre}")
        print(f"   capturas insertadas: {informe['insertadas']}")
        pend = informe["pendientes"]
        print(f"   pendientes: {len(pend)}")
        for n, pie in pend:
            print(f"     - #{n}: {pie}")
        for aviso in informe["avisos"]:
            print(f"   AVISO: {aviso}")
        print(f"   salida: {pdf}")
        print(f"           {docx}")


if __name__ == "__main__":
    main()
