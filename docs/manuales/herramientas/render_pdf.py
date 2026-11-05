"""Convierte las paginas de un PDF a PNG (para mostrar un acta en una captura).

    backend/.venv/Scripts/python.exe render_pdf.py entrada.pdf salida-prefijo [escala]

Escribe salida-prefijo-1.png, salida-prefijo-2.png, ... y imprime cuantas paginas hay.
Usa pypdfium2 (ya instalado en el venv del backend).
"""
import sys

import pypdfium2 as pdfium

pdf = pdfium.PdfDocument(sys.argv[1])
escala = float(sys.argv[3]) if len(sys.argv) > 3 else 1.4
for i in range(len(pdf)):
    pdf[i].render(scale=escala).to_pil().save(f"{sys.argv[2]}-{i + 1}.png")
print(len(pdf))
