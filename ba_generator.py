import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def save_photo_from_dataurl(data_url: str, dest_dir: Path, basename: str) -> Path:
    if "," in data_url:
        _, encoded = data_url.split(",", 1)
    else:
        encoded = data_url
    raw = base64.b64decode(encoded)
    img = Image.open(BytesIO(raw)).convert("RGB")
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{basename}.jpg"
    img.save(path, "JPEG", quality=88)
    return path


def build_ba_pdf(
    output_path: Path,
    ba_number: str,
    title: str,
    unit_name: str,
    project_code: str,
    project_name: str,
    pic: str,
    notes: str,
    photo_path: Path,
    created_by: str,
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    h_center = ParagraphStyle(
        "HCenter", parent=styles["Heading1"], alignment=1, fontSize=14, spaceAfter=2
    )
    sub_center = ParagraphStyle(
        "SubCenter", parent=styles["Normal"], alignment=1, fontSize=11, spaceAfter=6
    )
    normal = styles["Normal"]
    normal.fontSize = 10

    story = []
    story.append(Paragraph("<b>BERITA ACARA PENYELESAIAN PEKERJAAN</b>", h_center))
    story.append(Paragraph(f"Nomor: {ba_number}", sub_center))
    story.append(Spacer(1, 0.4 * cm))

    today = datetime.now().strftime("%d %B %Y")
    intro = (
        f"Pada hari ini, <b>{today}</b>, telah dilakukan pemeriksaan dan verifikasi "
        f"penyelesaian pekerjaan pada unit <b>{unit_name}</b> dengan rincian sebagai berikut:"
    )
    story.append(Paragraph(intro, normal))
    story.append(Spacer(1, 0.3 * cm))

    info = [
        ["Judul BA", title],
        ["Unit", unit_name],
        ["Kode Proyek", project_code],
        ["Nama Proyek", project_name],
        ["Penanggung Jawab", pic or "-"],
        ["Dibuat Oleh", created_by or "-"],
        ["Tanggal", today],
    ]
    tbl = Table(info, colWidths=[4.5 * cm, 11 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.4 * cm))

    if notes:
        story.append(Paragraph("<b>Catatan / Keterangan:</b>", normal))
        story.append(Paragraph(notes.replace("\n", "<br/>"), normal))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("<b>Dokumentasi Lapangan:</b>", normal))
    story.append(Spacer(1, 0.2 * cm))

    if photo_path and Path(photo_path).exists():
        with Image.open(photo_path) as im:
            w, h = im.size
        max_w = 14 * cm
        max_h = 10 * cm
        ratio = min(max_w / w, max_h / h)
        story.append(
            RLImage(str(photo_path), width=w * ratio, height=h * ratio)
        )
    story.append(Spacer(1, 0.6 * cm))

    sign_data = [
        ["Dibuat oleh,", "", "Mengetahui,"],
        ["", "", ""],
        ["", "", ""],
        ["", "", ""],
        [f"({created_by or '..............'})", "", f"({pic or '..............'})"],
    ]
    sign_tbl = Table(sign_data, colWidths=[6 * cm, 3 * cm, 6 * cm])
    sign_tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(sign_tbl)

    doc.build(story)
    return output_path
