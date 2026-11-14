import os
import secrets
from datetime import datetime
from functools import wraps

import psycopg
from psycopg.rows import dict_row

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, abort, session, Response
)

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

DATABASE_URL = os.environ.get("DATABASE_URL")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


CATEGORIES = [
    "Actualités", "Emploi", "Concours", "Formation",
    "Business", "Finance", "Technologie",
    "Immobilier", "Éducation", "Guides pratiques"
]


# =====================================
# CONNEXION POSTGRESQL
# =====================================

def db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas configurée.")

    url = DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

    return psycopg.connect(url, row_factory=dict_row)


# =====================================
# INITIALISATION DE LA BASE
# =====================================

def init_db():

    with db() as con:

        con.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id BIGSERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                excerpt TEXT NOT NULL,
                body TEXT NOT NULL,
                image_url TEXT DEFAULT '',
                author TEXT DEFAULT 'La rédaction',
                published INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                name TEXT,
                email TEXT,
                message TEXT,
                created_at TEXT NOT NULL
            )
        """)

        count = con.execute(
            "SELECT COUNT(*) AS total FROM articles"
        ).fetchone()["total"]

        if count == 0:

            samples = [
                (
                    "Bienvenue sur Africa Infos 360",
                    "bienvenue-africa-infos-360",
                    "Actualités",
                    "Un média indépendant pour comprendre l'actualité et découvrir les opportunités en Afrique.",
                    "Africa Infos 360 est un média numérique généraliste consacré à l'information utile en Afrique francophone.",
                    "",
                    "La rédaction"
                ),
                (
                    "Comment préparer efficacement sa recherche d'emploi",
