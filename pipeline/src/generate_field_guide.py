"""Generate a printable one-shot field guide PDF for the data-collection day.

Page 1: photo protocol + phone tips + golden rules.
Page 2: logbook table to fill in by hand (one row per cow).

    python3 src/generate_field_guide.py --out data/guia_campo.pdf --rows 35
"""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem,
)


def build(out_path: Path, rows: int) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.3 * cm, bottomMargin=1.3 * cm,
    )
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=16, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4,
                        textColor=colors.HexColor("#1a5276"))
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=10, leading=14, alignment=TA_LEFT)
    note = ParagraphStyle("note", parent=body, textColor=colors.HexColor("#922b21"))

    el = []
    el.append(Paragraph("Guía de campo — Captura de datos (peso bovino)", h1))
    el.append(Paragraph("Estimación de peso por visión por computadora · Finca San José Pinula", body))
    el.append(Spacer(1, 6))

    el.append(Paragraph("📷 Ajustes del celular (Xiaomi 15 Ultra)", h2))
    el.append(ListFlowable([
        ListItem(Paragraph("Lente <b>normal (1x)</b> — NUNCA el gran angular (0.5x).", body)),
        ListItem(Paragraph("Foto <b>horizontal</b>, máxima resolución, <b>sin zoom digital</b>.", body)),
        ListItem(Paragraph("Vaca + marcador <b>hacia el centro</b> del cuadro.", body)),
        ListItem(Paragraph("<b>A la sombra</b>; usa SIEMPRE el mismo teléfono para todas.", body)),
    ], bulletType="bullet", leftIndent=14))

    el.append(Paragraph("🐄 Por cada vaca (en orden)", h2))
    el.append(ListFlowable([
        ListItem(Paragraph("<b>FOTO DE ID primero:</b> close-up del arete (que se lea el número) "
                           "o un papel con el número a la par de la vaca.", body)),
        ListItem(Paragraph("Pésala con la cinta y <b>anota el peso</b> en la tabla.", body)),
        ListItem(Paragraph("Mide con cinta métrica: perímetro torácico, largo, altura.", body)),
        ListItem(Paragraph("Vaca <b>de perfil</b>, parada y quieta; marcador <b>vertical</b> a su costado.", body)),
        ListItem(Paragraph("Tú a <b>~3 m</b>; toma <b>10–20 fotos</b> (que se mueva un poco entre tomas).", body)),
        ListItem(Paragraph("Revisa que en cada foto salgan <b>vaca completa + marcador</b>.", body)),
        ListItem(Paragraph("Siguiente vaca.", body)),
    ], bulletType="1", leftIndent=14))

    el.append(Paragraph("⭐ Reglas de oro", h2))
    el.append(ListFlowable([
        ListItem(Paragraph("El marcador <b>vertical y viéndote de frente</b> (NO acostado en el suelo).", note)),
        ListItem(Paragraph("El marcador <b>a la par de la vaca</b> (misma distancia de la cámara que su cuerpo).", note)),
        ListItem(Paragraph("Que <b>nadie tape</b> el cuerpo de la vaca ni el marcador.", note)),
        ListItem(Paragraph("Cada bloque de fotos empieza con su <b>foto de ID</b>.", note)),
    ], bulletType="bullet", leftIndent=14))

    el.append(Spacer(1, 6))
    el.append(Paragraph("Marcador impreso: medirlo con regla tras imprimir. Tamaño real usado = ______ cm", body))

    el.append(PageBreak())

    # ---- Page 2: logbook table ----
    el.append(Paragraph("Tabla de registro — una fila por vaca", h1))
    el.append(Paragraph("PT = perímetro torácico · LC = largo de cuerpo · ALT = altura a la cruz", body))
    el.append(Spacer(1, 8))

    header = ["#", "Nombre", "Arete / ID", "Peso (kg)", "PT (cm)", "LC (cm)", "ALT (cm)", "# fotos", "Notas"]
    data = [header]
    for i in range(1, rows + 1):
        data.append([str(i), "", "", "", "", "", "", "", ""])

    col_widths = [0.8 * cm, 2.3 * cm, 2.0 * cm, 1.7 * cm, 1.6 * cm, 1.6 * cm, 1.6 * cm, 1.4 * cm, 3.0 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef5fb")]),
        ("TOPPADDING", (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    el.append(table)

    doc.build(el)


def main() -> int:
    p = argparse.ArgumentParser(description="Generate printable field-data-collection guide PDF")
    p.add_argument("--out", default="data/guia_campo.pdf")
    p.add_argument("--rows", type=int, default=35)
    args = p.parse_args()
    build(Path(args.out), args.rows)
    print(f"Wrote field guide -> {args.out} ({args.rows} logbook rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
