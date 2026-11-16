from flask import Flask, render_template, request, send_file
import sqlite3
import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
)

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "portail.db")

# Intitules complets des UE (a completer si de nouveaux codes apparaissent
# avec les futurs semestres / rattrapages)
UE_LABELS = UE_LABELS = {
    "GEO231": "Elements de climatologie / Elements de geomorphologie",
    "GEO232": "Geographie de la population / Geographie economique",
    "GEO233": "TD geomorphologie structurale I / Cartographie",
    "GEO234": "Geographie regionale Europe / Geographie regionale Amerique du sud",
    "GEO235": "Geographie regionale Afrique / Geographie regionale Asie",
    "GEO241": "Elements d'hydrologie / Elements de biogeographie",
    "GEO242": "Questions de geographie actuelle / Mondialisation et territoires",
    "GEO243": "TD geomorphologie structurale II / Statistique descriptive",
    "GEO244": "Methodologie historique / Elements de sociologie",
    "GEO245": "Methodologie historique / Elements de demographie",
    "GEO246": "Methodologie historique / Elements d'economie",
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/resultats", methods=["POST"])
def resultats():
    matricule = request.form.get("matricule", "").strip().upper()

    if not matricule:
        return render_template("index.html", error="Veuillez saisir votre matricule.")

    conn = get_db()
    etudiant = conn.execute(
        "SELECT * FROM etudiants WHERE matricule = ?", (matricule,)
    ).fetchone()

    if not etudiant:
        conn.close()
        return render_template(
            "index.html", error="Aucun resultat trouve pour ce matricule."
        )

    bilans = conn.execute(
        """SELECT * FROM bilans WHERE matricule = ?
           ORDER BY annee DESC, semestre ASC, session ASC""",
        (matricule,),
    ).fetchall()

    releves_par_bilan = []
    for b in bilans:
        notes = conn.execute(
            """SELECT * FROM releves
               WHERE matricule = ? AND semestre = ? AND session = ? AND annee = ?
               ORDER BY ue_code""",
            (matricule, b["semestre"], b["session"], b["annee"]),
        ).fetchall()
        releves_par_bilan.append({"bilan": b, "notes": notes})

    conn.close()
    return render_template(
        "resultats.html",
        etudiant=etudiant,
        releves_par_bilan=releves_par_bilan,
        ue_labels=UE_LABELS,
    )


def generer_pdf_releve(etudiant, semestre, session, annee, bilan, notes):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    navy = colors.HexColor("#0c1f3f")
    gold = colors.HexColor("#d4af37")

    title_style = ParagraphStyle(
        "TitleUCAD", parent=styles["Title"], fontSize=13, textColor=navy,
        spaceAfter=2, alignment=1,
    )
    sub_style = ParagraphStyle(
        "SubUCAD", parent=styles["Normal"], fontSize=9.5, textColor=colors.grey,
        alignment=1, spaceAfter=2,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=11, textColor=navy,
        spaceBefore=14, spaceAfter=6,
    )

    story = []
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo-ucad.png")
    if os.path.exists(logo_path):
        logo_img = RLImage(logo_path, width=22 * mm, height=22 * mm)
        logo_img.hAlign = "CENTER"
        story.append(logo_img)
        story.append(Spacer(1, 6))
    story.append(Paragraph("UNIVERSITE CHEIKH ANTA DIOP DE DAKAR", title_style))
    story.append(Paragraph("Faculte des Lettres et Sciences Humaines", sub_style))
    story.append(Paragraph("Releve de notes individuel", sub_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.4, color=gold))
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        f"<b>{etudiant['prenom']} {etudiant['nom']}</b>", styles["Heading2"]
    ))
    story.append(Paragraph(f"Matricule : {etudiant['matricule']}", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"{semestre} &mdash; {session} &mdash; {annee}", section_style))

    data = [["UE", "Note 1", "Note 2", "Resultat"]]
    for n in notes:
        data.append([
            n["ue_code"], n["note1"] or "-", n["note2"] or "-", n["resultat_ue"]
        ])

    table = Table(data, colWidths=[70 * mm, 30 * mm, 30 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde2ec")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8fb")]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))

    resultat_txt = "Valide" if bilan["resultat_semestre"] == "SV" else "Non valide"
    resultat_color = "#1e7a4c" if bilan["resultat_semestre"] == "SV" else "#b83b3b"
    bilan_data = [[
        Paragraph(f"<b>{bilan['total_credit']}</b><br/><font size=8 color=grey>Credits obtenus / 30</font>", styles["Normal"]),
        Paragraph(f"<b><font color='{resultat_color}'>{resultat_txt}</font></b><br/><font size=8 color=grey>Resultat du semestre</font>", styles["Normal"]),
    ]]
    bilan_table = Table(bilan_data, colWidths=[80 * mm, 80 * mm])
    bilan_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde2ec")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde2ec")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(bilan_table)
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#dde2ec")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Document genere automatiquement par le portail de resultats L2 Geographie UCAD. "
        "Ne remplace pas le releve de notes officiel delivre par la scolarite.",
        ParagraphStyle("Footnote", parent=styles["Normal"], fontSize=7.5, textColor=colors.grey),
    ))

    doc.build(story)
    buf.seek(0)
    return buf


@app.route("/telecharger-pdf")
def telecharger_pdf():
    matricule = request.args.get("matricule", "").strip().upper()
    semestre = request.args.get("semestre", "")
    session_ = request.args.get("session", "")
    annee = request.args.get("annee", "")

    conn = get_db()
    etudiant = conn.execute(
        "SELECT * FROM etudiants WHERE matricule = ?", (matricule,)
    ).fetchone()
    if not etudiant:
        conn.close()
        return "Etudiant introuvable", 404

    bilan = conn.execute(
        """SELECT * FROM bilans WHERE matricule=? AND semestre=? AND session=? AND annee=?""",
        (matricule, semestre, session_, annee),
    ).fetchone()
    if not bilan:
        conn.close()
        return "Releve introuvable", 404

    notes = conn.execute(
        """SELECT * FROM releves WHERE matricule=? AND semestre=? AND session=? AND annee=?
           ORDER BY ue_code""",
        (matricule, semestre, session_, annee),
    ).fetchall()
    conn.close()

    pdf_buf = generer_pdf_releve(etudiant, semestre, session_, annee, bilan, notes)
    filename = f"releve_{matricule}_{semestre}_{session_}".replace(" ", "_")
    return send_file(
        pdf_buf, mimetype="application/pdf", as_attachment=True,
        download_name=f"{filename}.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)
@app.route("/stats", methods=["GET"])
def stats():
    conn = get_db()
    lignes = conn.execute(
        """SELECT semestre, session, annee, resultat_semestre, COUNT(*) as nombre
           FROM bilans
           GROUP BY semestre, session, annee, resultat_semestre
           ORDER BY annee DESC, semestre ASC, session ASC"""
    ).fetchall()
    conn.close()

    stats_groupees = {}
    for l in lignes:
        cle = (l["semestre"], l["session"], l["annee"])
        stats_groupees.setdefault(cle, {"SV": 0, "SNV": 0})
        stats_groupees[cle][l["resultat_semestre"]] = l["nombre"]

    return render_template("stats.html", stats=stats_groupees)