"""Transcribe los audios de la revision con AssemblyAI.

Uso:
    $env:ASSEMBLYAI_API_KEY = "tu_clave"
    python transcribir_revision.py                      # audio*.m4a de aqui -> transcripts/
    python transcribir_revision.py <carpeta> <salida>   # todos los audios de <carpeta>

Deja un .txt por audio en la salida, con marca de tiempo y hablante en cada
intervencion, mas un archivo combinado. No sobrescribe transcripciones que ya
existan: si un .txt ya esta, ese audio se salta.

La clave se lee de la variable de entorno a proposito: asi no queda escrita en
ningun archivo del repositorio.
"""

import os
import sys
from pathlib import Path

import assemblyai as aai

# ── Vocabulario ──────────────────────────────────────────────────────────────
# Sin esto el reconocedor destroza la jerga: "OT" sale como "ote", "CMMS" como
# un balbuceo y "acta de servicio" se pierde. Se envia como Custom Vocabulary
# para que el modelo prefiera estas formas cuando dude.

DOMINIO = [
    "TodoGas", "CMMS", "gases medicinales", "orden de trabajo",
    "ordenes de trabajo", "acta de servicio", "hoja de vida",
    "mantenimiento preventivo", "mantenimiento correctivo",
    "plan de mantenimiento", "checklist", "plantilla de checklist",
    "activo", "activos", "ficha tecnica", "trazabilidad", "evidencia",
    "firma digital", "codigo QR", "inventario", "repuesto", "repuestos",
    "stock minimo", "auditoria", "cumplimiento", "indicador",
]

EQUIPOS = [
    "oxigeno", "nitrogeno", "oxido nitroso", "aire medicinal", "vacio",
    "cilindro", "cilindros", "manifold", "regulador", "central de gases",
    "concentrador de oxigeno", "ventilador mecanico", "red de gases",
]

PERSONAS = [
    "tecnico", "supervisor", "administrador", "cliente", "hospital", "sede",
]

TECNOLOGIA = [
    "Django", "React", "PostgreSQL", "Redis", "Celery", "WeasyPrint",
    "API REST", "endpoint", "serializer", "backend", "frontend",
    "Capacitor", "Android", "APK", "token", "JWT", "AWS", "despliegue",
]

REVISION = [
    "Fracttal", "protocolo", "protocolos", "ubicacion", "sububicacion",
    "tarea pendiente", "reprogramacion", "campo personalizado", "modelo",
    "numero de serie", "hallazgo", "hallazgos", "portal del hospital",
    "biomedica", "dar de baja", "PDF", "firma del cliente",
]

ACADEMICO = [
    "sprint", "requerimiento", "requerimientos funcionales",
    "requerimientos no funcionales", "alcance", "cronograma", "entregable",
    "sustentacion", "anteproyecto", "jurado",
]

VOCABULARIO = DOMINIO + EQUIPOS + PERSONAS + TECNOLOGIA + REVISION + ACADEMICO


# WhatsApp manda notas de voz en .ogg/.opus; AssemblyAI acepta todos estos.
FORMATOS = {".m4a", ".mp3", ".wav", ".ogg", ".opus", ".aac", ".mp4", ".webm", ".flac"}


def construir_config(con_vocabulario):
    opciones = {
        "language_code": "es",
        "speaker_labels": True,  # etiqueta quien habla en cada intervencion
    }
    if con_vocabulario:
        opciones["word_boost"] = VOCABULARIO
        opciones["boost_param"] = "high"
    return aai.TranscriptionConfig(**opciones)


def marca(milisegundos):
    total = int(milisegundos / 1000)
    return f"{total // 60:02d}:{total % 60:02d}"


def escribir(transcript, destino):
    with open(destino, "w", encoding="utf-8") as f:
        for u in transcript.utterances:
            f.write(f"[{marca(u.start)}] Hablante {u.speaker}: {u.text}\n\n")


def main():
    clave = os.environ.get("ASSEMBLYAI_API_KEY")
    if not clave:
        sys.exit(
            "Falta la clave. Ejecuta primero:\n"
            '    $env:ASSEMBLYAI_API_KEY = "tu_clave"'
        )
    aai.settings.api_key = clave

    if len(sys.argv) >= 2:
        carpeta = Path(sys.argv[1])
        audios = sorted(a for a in carpeta.iterdir() if a.suffix.lower() in FORMATOS)
        salida = Path(sys.argv[2]) if len(sys.argv) >= 3 else carpeta / "transcripts"
    else:
        carpeta = Path(".")
        audios = sorted(carpeta.glob("audio*.m4a"))
        salida = Path("transcripts")
    if not audios:
        sys.exit(f"No encontre audios en {carpeta.resolve()}.")

    salida.mkdir(parents=True, exist_ok=True)

    con_vocabulario = True
    generados = []

    for audio in audios:
        destino = salida / f"{audio.stem}.txt"
        if destino.exists():
            print(f"\n[{audio.name}] ya transcrito en {destino}, lo salto.")
            continue
        print(f"\n[{audio.name}] subiendo y transcribiendo...")
        try:
            transcriptor = aai.Transcriber(config=construir_config(con_vocabulario))
            transcript = transcriptor.transcribe(str(audio))
        except Exception as exc:
            # Si la cuenta o el idioma no admiten Custom Vocabulary, se reintenta
            # sin el en vez de dejar al usuario con un error cripcico.
            if not con_vocabulario:
                print(f"  ERROR: {exc}")
                continue
            print(f"  El vocabulario personalizado fue rechazado ({exc}).")
            print("  Reintentando sin el; la jerga puede salir peor.")
            con_vocabulario = False
            transcriptor = aai.Transcriber(config=construir_config(False))
            transcript = transcriptor.transcribe(str(audio))

        if transcript.status == "error":
            print(f"  ERROR: {transcript.error}")
            continue

        escribir(transcript, destino)
        generados.append((audio.stem, transcript))

        hablantes = sorted({u.speaker for u in transcript.utterances})
        duracion = marca(transcript.utterances[-1].end) if transcript.utterances else "?"
        print(f"  Listo -> {destino}")
        print(f"  {len(hablantes)} hablantes ({', '.join(hablantes)}), duracion {duracion}")
        print("  Primeras lineas para que revises la calidad:")
        for u in transcript.utterances[:3]:
            print(f"    [{marca(u.start)}] Hablante {u.speaker}: {u.text[:100]}")

    if generados:
        combinado = salida / "revision-completa.txt"
        with open(combinado, "w", encoding="utf-8") as f:
            for nombre, transcript in generados:
                f.write(f"\n{'=' * 70}\n{nombre.upper()}\n{'=' * 70}\n\n")
                for u in transcript.utterances:
                    f.write(f"[{marca(u.start)}] Hablante {u.speaker}: {u.text}\n\n")
        print(f"\nCombinado -> {combinado}")

    print(f"\n{len(generados)} de {len(audios)} audios transcritos.")


if __name__ == "__main__":
    main()
