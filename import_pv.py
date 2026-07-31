"""
Script d'import d'un PV de délibération (PDF UCAD) dans la base SQLite.

Usage :
    python3 import_pv.py chemin/vers/pv.pdf

Peut être relancé pour chaque nouveau PV (2e semestre, rattrapage, etc.) :
les nouvelles notes s'ajoutent, rien n'est écrasé (sauf si même
matricule + semestre + session + année déjà en base -> mise à jour).
"""

import sys
import re
import sqlite3
import pdfplumber

DB_PATH = "data/portail.db"


def init_db(conn):
    with open("schema.sql", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()


def extract_metadata(pdf):
    """Cherche Semestre / Session / Année sur la 1ere page."""
    text = pdf.pages[0].extract_text() or ""
    semestre = re.search(r"SEMESTRE\s*:\s*(.+)", text)
    session = re.search(r"SESSION\s*:\s*(.+)", text)
    annee = re.search(r"ANNEE\s*:\s*(.+)", text)
    return (
        semestre.group(1).strip() if semestre else "Semestre inconnu",
        session.group(1).strip() if session else "Session inconnue",
        annee.group(1).strip() if annee else "Annee inconnue",
    )


def extract_ue_codes(pdf):
    """Repere les codes d'UE (ex: GEO231) dans l'en-tete, avant la 1ere ligne d'etudiant."""
    text = pdf.pages[0].extract_text() or ""
    # On ne regarde que le texte AVANT la premiere ligne de donnees (matricule),
    # pour eviter de capter des faux positifs dans les cellules de notes.
    m = re.search(r"20\d{2}[A-Z0-9]{5,6}\b", text)
    header_text = text[: m.start()] if m else text
    codes = re.findall(r"\b[A-Z]{2,5}\s?\d{3}\b", header_text)
    seen = []
    for c in codes:
        c = c.replace(" ", "")
        if c not in seen:
            seen.append(c)
    return seen


def extract_rows(pdf):
    all_rows = []
    for page in pdf.pages:
        for table in page.find_tables():
            for row in table.extract():
                cell0 = str(row[0]).strip() if row[0] else ""
                if re.match(r"^20\d{2}[A-Z0-9]{5,6}$", cell0):
                    all_rows.append(row)
    return all_rows


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 import_pv.py chemin/vers/pv.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    cur = conn.cursor()

    with pdfplumber.open(pdf_path) as pdf:
        semestre, session, annee = extract_metadata(pdf)
        ue_codes = extract_ue_codes(pdf)
        rows = extract_rows(pdf)

    print(f"Semestre : {semestre}")
    print(f"Session  : {session}")
    print(f"Annee    : {annee}")
    print(f"UE detectees : {ue_codes}")
    print(f"Lignes etudiants trouvees : {len(rows)}")

    n_ue = len(ue_codes) if ue_codes else 5  # repli par defaut

    inserted, updated_bilan = 0, 0
    for r in rows:
        matricule = r[0].strip()
        nom = (r[1] or "").strip()
        prenom = (r[2] or "").strip()

        cur.execute(
            "INSERT OR IGNORE INTO etudiants (matricule, nom, prenom) VALUES (?, ?, ?)",
            (matricule, nom, prenom),
        )

        # Supprime les anciennes notes de ce meme (matricule, semestre, session, annee)
        cur.execute(
            "DELETE FROM releves WHERE matricule=? AND semestre=? AND session=? AND annee=?",
            (matricule, semestre, session, annee),
        )

        idx = 3
        for i in range(n_ue):
            if idx + 2 >= len(r) - 2:
                break
            note1 = (r[idx] or "").strip()
            note2 = (r[idx + 1] or "").strip()
            res = (r[idx + 2] or "").strip()
            if note1 or note2 or res:
                ue_code = ue_codes[i] if i < len(ue_codes) else f"UE{i+1}"
                cur.execute(
                    """INSERT INTO releves
                       (matricule, semestre, session, annee, ue_code, note1, note2, resultat_ue)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (matricule, semestre, session, annee, ue_code, note1, note2, res),
                )
                inserted += 1
            idx += 3

        total_credit = (r[-2] or "").strip()
        resultat_sem = (r[-1] or "").strip()
        cur.execute(
            """INSERT INTO bilans (matricule, semestre, session, annee, total_credit, resultat_semestre)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(matricule, semestre, session, annee)
               DO UPDATE SET total_credit=excluded.total_credit,
                             resultat_semestre=excluded.resultat_semestre""",
            (matricule, semestre, session, annee, total_credit, resultat_sem),
        )
        updated_bilan += 1

    conn.commit()
    conn.close()
    print(f"OK : {inserted} lignes de notes inserees, {updated_bilan} bilans mis a jour.")


if __name__ == "__main__":
    main()
