"""Sorgu geçmişi (SQLite). KVKK gereği TC/VKN maskeli saklanır."""
import csv
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "kwoly.db"


def _baglan():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS sorgular(
        id INTEGER PRIMARY KEY AUTOINCREMENT, zaman TEXT, brans TEXT,
        plaka TEXT, tc_maskeli TEXT, arac TEXT);
    CREATE TABLE IF NOT EXISTS sonuclar(
        sorgu_id INTEGER, sirket TEXT, yontem TEXT, durum TEXT, fiyat REAL,
        komisyon REAL, teklif_no TEXT, mesaj TEXT, sure_sn REAL,
        PRIMARY KEY(sorgu_id, sirket));
    """)
    return c


def maskele(tc: str) -> str:
    tc = tc.strip()
    return tc[:2] + "*" * max(len(tc) - 4, 0) + tc[-2:] if len(tc) > 4 else "****"


def sorgu_ac(brans: str, plaka: str, tc: str, arac: dict | None = None) -> int:
    with _baglan() as c:
        cur = c.execute("INSERT INTO sorgular(zaman,brans,plaka,tc_maskeli,arac) VALUES(?,?,?,?,?)",
                        (datetime.now().isoformat(timespec="seconds"), brans,
                         plaka.upper(), maskele(tc), json.dumps(arac or {}, ensure_ascii=False)))
        return cur.lastrowid


def sonuc_kaydet(sorgu_id: int, r: dict):
    with _baglan() as c:
        c.execute("INSERT OR REPLACE INTO sonuclar VALUES(?,?,?,?,?,?,?,?,?)",
                  (sorgu_id, r["sirket"], r["yontem"], r["durum"], r["fiyat"],
                   r["komisyon"], r["teklif_no"], r["mesaj"], r["sure_sn"]))


def liste(limit: int = 50) -> list[dict]:
    with _baglan() as c:
        rows = c.execute("""
          SELECT s.*, MIN(CASE WHEN r.durum='OK' THEN r.fiyat END) AS en_ucuz,
                 SUM(r.durum='OK') AS basarili, COUNT(r.sirket) AS toplam
          FROM sorgular s LEFT JOIN sonuclar r ON r.sorgu_id=s.id
          GROUP BY s.id ORDER BY s.id DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(x) for x in rows]


def detay(sorgu_id: int) -> dict | None:
    with _baglan() as c:
        s = c.execute("SELECT * FROM sorgular WHERE id=?", (sorgu_id,)).fetchone()
        if not s:
            return None
        r = c.execute("SELECT * FROM sonuclar WHERE sorgu_id=? ORDER BY durum!='OK', fiyat",
                      (sorgu_id,)).fetchall()
        return {**dict(s), "arac": json.loads(s["arac"] or "{}"), "sonuclar": [dict(x) for x in r]}


def csv_metni(sorgu_id: int) -> str:
    d = detay(sorgu_id)
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")          # Türkçe Excel ; ayırıcı bekler
    w.writerow(["Sorgu", d["id"], d["zaman"], d["brans"], d["plaka"]])
    w.writerow([])
    w.writerow(["Şirket", "Yöntem", "Durum", "Brüt Prim", "Komisyon", "Teklif No", "Mesaj", "Süre (sn)"])
    tr = lambda n: "" if n is None else f"{n:.2f}".replace(".", ",")
    for r in d["sonuclar"]:
        w.writerow([r["sirket"], r["yontem"], r["durum"], tr(r["fiyat"]), tr(r["komisyon"]),
                    r["teklif_no"], r["mesaj"], tr(r["sure_sn"])])
    return "﻿" + out.getvalue()            # BOM: Excel Türkçe karakterleri doğru açsın
