import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from ba_generator import build_ba_pdf, save_photo_from_dataurl
from database import get_conn, init_db

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
COMPLETION_DIR = UPLOAD_DIR / "completion"
PHOTO_DIR = UPLOAD_DIR / "photos"
BA_DIR = UPLOAD_DIR / "ba"

ALLOWED_COMPLETION_EXT = {"pdf", "png", "jpg", "jpeg", "doc", "docx", "xls", "xlsx"}
MAX_UPLOAD_BYTES = 16 * 1024 * 1024

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

for d in (COMPLETION_DIR, PHOTO_DIR, BA_DIR):
    d.mkdir(parents=True, exist_ok=True)

init_db()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_COMPLETION_EXT


def generate_ba_number(project_id: int) -> str:
    now = datetime.now()
    return f"BA/{now.strftime('%Y%m%d')}/{project_id:04d}/{now.strftime('%H%M%S')}"


@app.route("/")
def dashboard():
    conn = get_conn()
    units = conn.execute("SELECT * FROM units ORDER BY name").fetchall()

    unit_stats = []
    for unit in units:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status='IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress
            FROM projects WHERE unit_id = ?
            """,
            (unit["id"],),
        ).fetchone()
        ba_count = conn.execute(
            """
            SELECT COUNT(*) AS c FROM berita_acara ba
            JOIN projects p ON p.id = ba.project_id
            WHERE p.unit_id = ?
            """,
            (unit["id"],),
        ).fetchone()["c"]
        total = row["total"] or 0
        completed = row["completed"] or 0
        pct = int((completed / total) * 100) if total else 0
        unit_stats.append(
            {
                "unit": unit,
                "total": total,
                "completed": completed,
                "in_progress": row["in_progress"] or 0,
                "ba_count": ba_count,
                "pct": pct,
            }
        )

    totals = conn.execute(
        """
        SELECT
            COUNT(*) AS total_projects,
            SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) AS total_completed
        FROM projects
        """
    ).fetchone()
    total_ba = conn.execute("SELECT COUNT(*) AS c FROM berita_acara").fetchone()["c"]

    recent_ba = conn.execute(
        """
        SELECT ba.*, p.code AS project_code, p.name AS project_name, u.name AS unit_name
        FROM berita_acara ba
        JOIN projects p ON p.id = ba.project_id
        JOIN units u ON u.id = p.unit_id
        ORDER BY ba.created_at DESC
        LIMIT 6
        """
    ).fetchall()

    conn.close()
    return render_template(
        "dashboard.html",
        unit_stats=unit_stats,
        totals=totals,
        total_ba=total_ba,
        recent_ba=recent_ba,
    )


@app.route("/units", methods=["GET", "POST"])
def units():
    conn = get_conn()
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        location = (request.form.get("location") or "").strip()
        if not name:
            flash("Nama unit wajib diisi.", "error")
        else:
            try:
                conn.execute(
                    "INSERT INTO units (name, location) VALUES (?, ?)", (name, location)
                )
                conn.commit()
                flash(f"Unit '{name}' berhasil ditambahkan.", "success")
            except Exception as e:
                flash(f"Gagal menambah unit: {e}", "error")
        conn.close()
        return redirect(url_for("units"))

    rows = conn.execute("SELECT * FROM units ORDER BY name").fetchall()
    conn.close()
    return render_template("units.html", units=rows)


@app.route("/projects")
def projects():
    unit_id = request.args.get("unit_id", type=int)
    status = request.args.get("status")

    conn = get_conn()
    query = """
        SELECT p.*, u.name AS unit_name,
            (SELECT COUNT(*) FROM berita_acara ba WHERE ba.project_id = p.id) AS ba_count
        FROM projects p
        JOIN units u ON u.id = p.unit_id
        WHERE 1=1
    """
    params = []
    if unit_id:
        query += " AND p.unit_id = ?"
        params.append(unit_id)
    if status in ("COMPLETED", "IN_PROGRESS"):
        query += " AND p.status = ?"
        params.append(status)
    query += " ORDER BY p.created_at DESC"

    rows = conn.execute(query, params).fetchall()
    units_rows = conn.execute("SELECT * FROM units ORDER BY name").fetchall()
    conn.close()
    return render_template(
        "projects.html",
        projects=rows,
        units=units_rows,
        selected_unit=unit_id,
        selected_status=status,
    )


@app.route("/projects/new", methods=["GET", "POST"])
def project_new():
    conn = get_conn()
    if request.method == "POST":
        unit_id = request.form.get("unit_id", type=int)
        code = (request.form.get("code") or "").strip()
        name = (request.form.get("name") or "").strip()
        description = (request.form.get("description") or "").strip()
        pic = (request.form.get("pic") or "").strip()

        if not (unit_id and code and name):
            flash("Unit, kode dan nama proyek wajib diisi.", "error")
        else:
            conn.execute(
                """INSERT INTO projects (unit_id, code, name, description, pic)
                   VALUES (?, ?, ?, ?, ?)""",
                (unit_id, code, name, description, pic),
            )
            conn.commit()
            flash(f"Proyek '{name}' berhasil dibuat.", "success")
            conn.close()
            return redirect(url_for("projects"))
    units_rows = conn.execute("SELECT * FROM units ORDER BY name").fetchall()
    conn.close()
    return render_template("project_form.html", units=units_rows)


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    conn = get_conn()
    project = conn.execute(
        """SELECT p.*, u.name AS unit_name FROM projects p
           JOIN units u ON u.id = p.unit_id WHERE p.id = ?""",
        (project_id,),
    ).fetchone()
    if not project:
        conn.close()
        abort(404)
    ba_list = conn.execute(
        "SELECT * FROM berita_acara WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    ).fetchall()
    conn.close()
    return render_template("project_detail.html", project=project, ba_list=ba_list)


@app.route("/projects/<int:project_id>/complete", methods=["POST"])
def complete_project(project_id):
    conn = get_conn()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        conn.close()
        abort(404)

    file = request.files.get("completion_file")
    if not file or file.filename == "":
        flash("File penyelesaian wajib di-upload.", "error")
        conn.close()
        return redirect(url_for("project_detail", project_id=project_id))

    if not allowed_file(file.filename):
        flash("Format file tidak diizinkan.", "error")
        conn.close()
        return redirect(url_for("project_detail", project_id=project_id))

    safe = secure_filename(file.filename)
    stored_name = f"proj{project_id}_{uuid.uuid4().hex[:8]}_{safe}"
    dest = COMPLETION_DIR / stored_name
    file.save(dest)

    conn.execute(
        """UPDATE projects
           SET status='COMPLETED',
               completion_file=?,
               completed_at=datetime('now','localtime')
           WHERE id=?""",
        (stored_name, project_id),
    )
    conn.commit()
    conn.close()
    flash("Proyek ditandai SELESAI dan file bukti tersimpan.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/reopen", methods=["POST"])
def reopen_project(project_id):
    conn = get_conn()
    conn.execute(
        "UPDATE projects SET status='IN_PROGRESS', completed_at=NULL WHERE id=?",
        (project_id,),
    )
    conn.commit()
    conn.close()
    flash("Proyek dibuka kembali.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/ba/capture")
def ba_capture(project_id):
    conn = get_conn()
    project = conn.execute(
        """SELECT p.*, u.name AS unit_name FROM projects p
           JOIN units u ON u.id = p.unit_id WHERE p.id = ?""",
        (project_id,),
    ).fetchone()
    conn.close()
    if not project:
        abort(404)
    return render_template("ba_capture.html", project=project)


@app.route("/projects/<int:project_id>/ba", methods=["POST"])
def ba_create(project_id):
    conn = get_conn()
    project = conn.execute(
        """SELECT p.*, u.name AS unit_name FROM projects p
           JOIN units u ON u.id = p.unit_id WHERE p.id = ?""",
        (project_id,),
    ).fetchone()
    if not project:
        conn.close()
        return jsonify({"ok": False, "error": "Proyek tidak ditemukan"}), 404

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip() or f"BA {project['name']}"
    notes = (data.get("notes") or "").strip()
    created_by = (data.get("created_by") or "").strip() or "Petugas Lapangan"
    photo_data = data.get("photo")

    if not photo_data:
        conn.close()
        return jsonify({"ok": False, "error": "Foto wajib diambil"}), 400

    ba_number = generate_ba_number(project_id)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    basename = f"proj{project_id}_{stamp}_{uuid.uuid4().hex[:6]}"

    photo_path = save_photo_from_dataurl(photo_data, PHOTO_DIR, basename)
    pdf_path = BA_DIR / f"{basename}.pdf"
    build_ba_pdf(
        output_path=pdf_path,
        ba_number=ba_number,
        title=title,
        unit_name=project["unit_name"],
        project_code=project["code"],
        project_name=project["name"],
        pic=project["pic"] or "",
        notes=notes,
        photo_path=photo_path,
        created_by=created_by,
    )

    conn.execute(
        """INSERT INTO berita_acara
           (project_id, ba_number, title, notes, photo_path, pdf_path, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            project_id,
            ba_number,
            title,
            notes,
            photo_path.name,
            pdf_path.name,
            created_by,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify(
        {
            "ok": True,
            "ba_number": ba_number,
            "pdf_url": url_for("download_ba", filename=pdf_path.name),
            "detail_url": url_for("project_detail", project_id=project_id),
        }
    )


@app.route("/ba")
def ba_list():
    conn = get_conn()
    rows = conn.execute(
        """SELECT ba.*, p.code AS project_code, p.name AS project_name, u.name AS unit_name
           FROM berita_acara ba
           JOIN projects p ON p.id = ba.project_id
           JOIN units u ON u.id = p.unit_id
           ORDER BY ba.created_at DESC"""
    ).fetchall()
    conn.close()
    return render_template("ba_list.html", ba_list=rows)


@app.route("/files/ba/<path:filename>")
def download_ba(filename):
    return send_from_directory(BA_DIR, filename, as_attachment=False)


@app.route("/files/photos/<path:filename>")
def download_photo(filename):
    return send_from_directory(PHOTO_DIR, filename)


@app.route("/files/completion/<path:filename>")
def download_completion(filename):
    return send_from_directory(COMPLETION_DIR, filename, as_attachment=True)


@app.errorhandler(413)
def too_large(_e):
    flash("File terlalu besar (maks 16MB).", "error")
    return redirect(request.referrer or url_for("dashboard")), 302


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
