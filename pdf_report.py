"""
pdf_report.py - PDF Report Generator V6
Supports:
- normal screenshot
- AI annotated frame
- drawing overlay frame
"""

import os
import cv2
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage
)

ACCENT = colors.HexColor("#00e5ff")
TEXT_LIGHT = colors.HexColor("#e2e8f0")
TEXT_MUTED = colors.HexColor("#64748b")
SUCCESS = colors.HexColor("#22c55e")
WARNING = colors.HexColor("#f59e0b")
DANGER = colors.HexColor("#ef4444")
ROW_EVEN = colors.HexColor("#1e293b")
ROW_ODD = colors.HexColor("#0f172a")
HEADER_BG = colors.HexColor("#1e40af")


def accuracy_color(acc):
    return {
        "High": SUCCESS,
        "Medium": WARNING,
        "Low": DANGER,
        "Estimated": ACCENT
    }.get(acc, TEXT_MUTED)


def _add_frame_image_to_story(story, frame, title):
    if frame is None:
        return

    styles = getSampleStyleSheet()
    section_style = ParagraphStyle(
        "SectionTemp",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=ACCENT,
        spaceBefore=14,
        spaceAfter=6,
        fontName="Helvetica-Bold",
    )

    story.append(Paragraph(title, section_style))

    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        cv2.imwrite(tmp.name, frame)
        tmp.close()

        img_w = 15 * cm
        img_h = img_w * (frame.shape[0] / frame.shape[1])
        rl_img = RLImage(tmp.name, width=img_w, height=img_h)
        story.append(rl_img)
        story.append(Spacer(1, 0.3 * cm))
    except Exception:
        pass


def generate_pdf_report(measurements: list, screenshot_frame=None, output_path=None, drawing_frame=None, annotated_frame=None) -> str:
    os.makedirs("reports", exist_ok=True)

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join("reports", f"measurement_report_{ts}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=26,
        textColor=ACCENT,
        alignment=TA_CENTER,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=TEXT_MUTED,
        alignment=TA_CENTER,
        spaceAfter=2,
        fontName="Helvetica",
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=ACCENT,
        spaceBefore=14,
        spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        textColor=TEXT_LIGHT,
        fontName="Helvetica",
        leading=16,
    )
    muted_style = ParagraphStyle(
        "Muted",
        parent=styles["Normal"],
        fontSize=9,
        textColor=TEXT_MUTED,
        fontName="Helvetica",
    )

    story = []

    story.append(Paragraph("AI Measure Pro YOLO", title_style))
    story.append(Paragraph("Measurement Report — Version 6", subtitle_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y  %H:%M:%S')}",
        subtitle_style
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph("Session Summary", section_style))

    total = len(measurements)
    persons = sum(1 for m in measurements if "person" in str(m.get("object_name", "")).lower())
    objects = total - persons
    high_acc = sum(1 for m in measurements if m.get("accuracy") in ("High", None))

    summary_data = [
        ["Total Detections", str(total)],
        ["Person Detections", str(persons)],
        ["Object Detections", str(objects)],
        ["High Accuracy Readings", str(high_acc)],
        ["Report Time", datetime.now().strftime("%H:%M:%S")],
    ]
    summary_table = Table(summary_data, colWidths=[8 * cm, 8 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("BACKGROUND", (0, 0), (0, -1), ROW_EVEN),
        ("BACKGROUND", (1, 0), (1, -1), ROW_ODD),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_LIGHT),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    _add_frame_image_to_story(story, screenshot_frame, "Captured Frame")
    _add_frame_image_to_story(story, annotated_frame, "AI Annotated Frame")
    _add_frame_image_to_story(story, drawing_frame, "Drawing Overlay")

    story.append(HRFlowable(width="100%", thickness=0.5, color=TEXT_MUTED, spaceAfter=6))
    story.append(Paragraph("Detailed Measurements", section_style))

    if not measurements:
        story.append(Paragraph("No measurements recorded in this session.", body_style))
    else:
        header = ["#", "Object", "Confidence", "Width (cm)", "Height (cm)", "Extra", "Accuracy"]
        table_data = [header]

        for m in measurements:
            table_data.append([
                str(m.get("object_id", "-")),
                str(m.get("object_name", "-")),
                str(m.get("confidence", "-")),
                str(m.get("width_cm", "N/A")),
                str(m.get("height_cm", "N/A")),
                str(m.get("extra", "")),
                str(m.get("accuracy", "N/A")),
            ])

        col_widths = [1.0 * cm, 3.0 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 3.5 * cm, 2.0 * cm]
        meas_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        row_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_LIGHT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ROW_EVEN, ROW_ODD]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#334155")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]

        for i, m in enumerate(measurements, start=1):
            acc = m.get("accuracy", "N/A")
            col = accuracy_color(acc)
            row_styles.append(("TEXTCOLOR", (6, i), (6, i), col))
            row_styles.append(("FONTNAME", (6, i), (6, i), "Helvetica-Bold"))

        meas_table.setStyle(TableStyle(row_styles))
        story.append(meas_table)

    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEXT_MUTED, spaceAfter=6))
    story.append(Paragraph("Notes", section_style))
    story.append(Paragraph(
        "This report includes measurement data, AI annotation output, and optional air-drawing overlay.",
        body_style
    ))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "AI Measure Pro YOLO V6  |  Powered by YOLOv8 + MediaPipe  |  For academic use",
        muted_style
    ))

    doc.build(story)
    return output_path