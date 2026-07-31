-- Schema du portail de résultats
-- Une ligne = une note d'UE pour un étudiant, dans un semestre et une session donnés

CREATE TABLE IF NOT EXISTS etudiants (
    matricule TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS releves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matricule TEXT NOT NULL,
    semestre TEXT NOT NULL,       -- ex: "Semestre 3"
    session TEXT NOT NULL,        -- ex: "Premiere session" ou "Rattrapage"
    annee TEXT NOT NULL,          -- ex: "2025-2026"
    ue_code TEXT NOT NULL,        -- ex: "GEO231"
    ue_intitule TEXT,
    note1 TEXT,
    note2 TEXT,
    resultat_ue TEXT,             -- V / VC / NV
    FOREIGN KEY (matricule) REFERENCES etudiants(matricule)
);

CREATE TABLE IF NOT EXISTS bilans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matricule TEXT NOT NULL,
    semestre TEXT NOT NULL,
    session TEXT NOT NULL,
    annee TEXT NOT NULL,
    total_credit TEXT,
    resultat_semestre TEXT,       -- SV / SNV
    UNIQUE(matricule, semestre, session, annee),
    FOREIGN KEY (matricule) REFERENCES etudiants(matricule)
);

CREATE INDEX IF NOT EXISTS idx_releves_matricule ON releves(matricule);
CREATE INDEX IF NOT EXISTS idx_bilans_matricule ON bilans(matricule);
