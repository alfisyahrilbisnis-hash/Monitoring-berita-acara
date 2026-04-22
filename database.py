import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "monitoring.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            location TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            pic TEXT,
            status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
            completion_file TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS berita_acara (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            ba_number TEXT NOT NULL,
            title TEXT NOT NULL,
            notes TEXT,
            photo_path TEXT NOT NULL,
            pdf_path TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ba_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ba_id INTEGER NOT NULL,
            photo_path TEXT NOT NULL,
            caption TEXT,
            order_idx INTEGER DEFAULT 0,
            FOREIGN KEY (ba_id) REFERENCES berita_acara(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) AS c FROM units")
    if cur.fetchone()["c"] == 0:
        seed_units = [
            ("Unit Operasi", "Jakarta"),
            ("Unit Pemeliharaan", "Bandung"),
            ("Unit Distribusi", "Surabaya"),
        ]
        cur.executemany("INSERT INTO units (name, location) VALUES (?, ?)", seed_units)
        cur.executemany(
            "INSERT INTO projects (unit_id, code, name, description, pic) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "PRJ-001", "Perbaikan Jaringan Gardu A", "Peningkatan kapasitas gardu A", "Budi"),
                (1, "PRJ-002", "Instalasi Panel Baru", "Instalasi panel LV baru", "Siti"),
                (2, "PRJ-003", "Maintenance Trafo 20KV", "Pemeliharaan rutin trafo", "Andi"),
                (3, "PRJ-004", "Ekspansi Feeder 7", "Perluasan feeder area timur", "Dewi"),
            ],
        )
        conn.commit()

    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
