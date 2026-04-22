import base64
import uuid
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
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_W, PAGE_H = A4
CONTENT_W = PAGE_W - 4 * cm


def save_photo_from_dataurl(data_url: str, dest_dir: Path, basename: str) -> Path:
    if "," in data_url:
        _, encoded = data_url.split(",", 1)
    else:
        encoded = data_url
    raw = base64.b64decode(encoded)
    img = Image.open(BytesIO(raw)).convert("RGB")
    max_side = 1600
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{basename}.jpg"
    img.save(path, "JPEG", quality=85, optimize=True)
    return path


def _fit_image(photo_path: Path, max_w_cm: float, max_h_cm: float) -> RLImage:
    with Image.open(photo_path) as im:
        w, h = im.size
    max_w = max_w_cm * cm
    max_h = max_h_cm * cm
    ratio = min(max_w / w, max_h / h)
    return RLImage(str(photo_path), width=w * ratio, height=h * ratio)


def _styles():
    base = getSampleStyleSheet()
    return {
        "title_big": ParagraphStyle(
            "TitleBig", parent=base["Heading1"], alignment=1,
            fontSize=20, leading=26, spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], alignment=1,
            fontSize=12, leading=16, textColor=colors.HexColor("#334155"),
            spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontSize=13, spaceBefore=8, spaceAfter=6,
        ),
        "normal": ParagraphStyle(
            "Body", parent=base["Normal"], fontSize=10.5, leading=15,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=base["Normal"], fontSize=9.5, alignment=1,
            textColor=colors.HexColor("#475569"), spaceBefore=4,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"], alignment=1,
            fontSize=8.5, textColor=colors.grey,
        ),
    }


def _info_table(rows):
    tbl = Table(rows, colWidths=[5 * cm, CONTENT_W - 5 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tbl


def _draw_header_footer(canvas, doc):
    canvas.saveState()
    # top band
    canvas.setFillColor(colors.HexColor("#0f172a"))
    canvas.rect(0, PAGE_H - 1.1 * cm, PAGE_W, 1.1 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(2 * cm, PAGE_H - 0.7 * cm, "MONITORING BERITA ACARA")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(PAGE_W - 2 * cm, PAGE_H - 0.7 * cm,
                           datetime.now().strftime("%d %B %Y"))
    # footer
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(
        PAGE_W / 2, 1 * cm,
        f"Halaman {doc.page} - Dokumen dihasilkan otomatis oleh Monitoring BA",
    )
    canvas.restoreState()


def build_ba_pdf(
    output_path: Path,
    ba_number: str,
    title: str,
    unit_name: str,
    project_code: str,
    project_name: str,
    pic: str,
    notes: str,
    photos: list,
    created_by: str,
):
    """
    photos: list of dict {"path": Path, "caption": str}
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"{ba_number} - {title}",
    )
    s = _styles()
    story = []
    today = datetime.now().strftime("%d %B %Y")

    # --- COVER PAGE ---
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("BERITA ACARA", s["title_big"]))
    story.append(Paragraph("PENYELESAIAN PEKERJAAN", s["title_big"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"Nomor: <b>{ba_number}</b>", s["subtitle"]))
    story.append(Spacer(1, 1.2 * cm))

    # hero photo (first photo) on cover if available
    if photos:
        try:
            hero = _fit_image(photos[0]["path"], 14, 9)
            hero.hAlign = "CENTER"
            story.append(hero)
            story.append(Spacer(1, 0.3 * cm))
            cap = photos[0].get("caption") or "Dokumentasi lapangan"
            story.append(Paragraph(cap, s["caption"]))
        except Exception:
            pass

    story.append(Spacer(1, 1 * cm))

    meta = [
        ["Judul", title],
        ["Unit", unit_name],
        ["Kode Proyek", project_code],
        ["Nama Proyek", project_name],
        ["Penanggung Jawab", pic or "-"],
        ["Dibuat Oleh", created_by or "-"],
        ["Tanggal", today],
        ["Jumlah Lampiran Foto", str(len(photos))],
    ]
    story.append(_info_table(meta))
    story.append(PageBreak())

    # --- DETAIL / NARRATIVE PAGE ---
    story.append(Paragraph("RINCIAN PEKERJAAN", s["h2"]))
    intro = (
        f"Pada hari ini, <b>{today}</b>, telah dilaksanakan pemeriksaan dan "
        f"verifikasi penyelesaian pekerjaan pada unit <b>{unit_name}</b> "
        f"dengan rincian pada tabel berikut."
    )
    story.append(Paragraph(intro, s["normal"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_info_table(meta))
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("CATATAN / KETERANGAN", s["h2"]))
    if notes:
        story.append(Paragraph(notes.replace("\n", "<br/>"), s["normal"]))
    else:
        story.append(Paragraph("<i>Tidak ada catatan tambahan.</i>", s["normal"]))
    story.append(Spacer(1, 0.8 * cm))

    # signature block
    sign_data = [
        ["Dibuat oleh,", "", "Mengetahui,"],
        ["", "", ""],
        ["", "", ""],
        ["", "", ""],
        [f"({created_by or '..............'})", "", f"({pic or '..............'})"],
    ]
    sign_tbl = Table(sign_data, colWidths=[6.5 * cm, 3 * cm, 6.5 * cm])
    sign_tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("LINEABOVE", (0, 4), (0, 4), 0.5, colors.black),
                ("LINEABOVE", (2, 4), (2, 4), 0.5, colors.black),
            ]
        )
    )
    story.append(sign_tbl)

    # --- PHOTO ATTACHMENTS ---
    if photos:
        story.append(PageBreak())
        story.append(Paragraph("LAMPIRAN FOTO LAPANGAN", s["h2"]))
        story.append(Paragraph(
            f"Total dokumentasi foto: <b>{len(photos)}</b> lembar.", s["normal"]
        ))
        story.append(Spacer(1, 0.3 * cm))

        # 2 photos per page
        for idx, p in enumerate(photos, start=1):
            if idx > 1 and (idx - 1) % 2 == 0:
                story.append(PageBreak())
            try:
                img = _fit_image(p["path"], 15, 9)
                img.hAlign = "CENTER"
                story.append(img)
            except Exception:
                continue
            cap = p.get("caption") or ""
            label = f"<b>Foto {idx}</b>"
            if cap:
                label += f" - {cap}"
            story.append(Paragraph(label, s["caption"]))
            story.append(Spacer(1, 0.5 * cm))

    doc.build(story, onFirstPage=_draw_header_footer,
              onLaterPages=_draw_header_footer)
    return output_path
