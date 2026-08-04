from flask import Flask, render_template, request
import sqlite3
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "portail.db")

# Intitules complets des UE (a completer si de nouveaux codes apparaissent
# avec les futurs semestres / rattrapages)
UE_LABELS = {
    "GEO231": "Elements de climatologie / Elements de geomorphologie",
    "GEO232": "Geographie de la population / Geographie economique",
    "GEO233": "TD geomorphologie structurale I / Cartographie",
    "GEO234": "Geographie regionale Europe / Geographie regionale Amerique du sud",
    "GEO235": "Geographie regionale Afrique / Geographie regionale Asie",
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


if __name__ == "__main__":
    app.run(debug=True)
