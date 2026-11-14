import os
import secrets
import ipaddress
import json
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
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
                    "preparer-recherche-emploi",
                    "Emploi",
                    "CV, lettre de motivation, veille et préparation aux entretiens : les étapes essentielles.",
                    "Une recherche d'emploi efficace commence par un objectif professionnel clair. Identifiez les secteurs et les postes correspondant à vos compétences, puis adaptez votre CV à chaque candidature.",
                    "",
                    "La rédaction"
                ),
                (
                    "Les étapes pour structurer une petite activité commerciale",
                    "structurer-petite-activite-commerciale",
                    "Business",
                    "Quelques repères pour passer d'une idée à une activité organisée et durable.",
                    "Avant de lancer une activité, vérifiez qu'il existe une demande réelle. Établissez un budget de démarrage et définissez un prix adapté à vos charges.",
                    "",
                    "La rédaction"
                )
            ]

            for item in samples:

                con.execute("""
                    INSERT INTO articles
                    (title, slug, category, excerpt, body,
                     image_url, author, published, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    *item[:5],
                    item[5],
                    item[6],
                    1,
                    datetime.utcnow().isoformat()
                ))


# =====================================
# PROTECTION ADMINISTRATEUR
# =====================================

def admin_required(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):

        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))

        return fn(*args, **kwargs)

    return wrapper


@app.context_processor
def inject_globals():

    return {
        "categories": CATEGORIES,
        "year": datetime.now().year
    }


# =====================================
# PAGE D'ACCUEIL
# =====================================

@app.route("/")
def home():

    category = request.args.get("category", "")
    q = request.args.get("q", "").strip()

    sql = "SELECT * FROM articles WHERE published=1"
    params = []

    if category in CATEGORIES:
        sql += " AND category=%s"
        params.append(category)

    if q:
        sql += " AND (title ILIKE %s OR excerpt ILIKE %s OR body ILIKE %s)"
        params += [f"%{q}%"] * 3

    sql += " ORDER BY created_at DESC LIMIT 30"

    with db() as con:
        articles = con.execute(sql, params).fetchall()

    return render_template(
        "home.html",
        articles=articles,
        selected=category,
        q=q
    )


# =====================================
# LECTURE D'UN ARTICLE
# =====================================

@app.route("/article/<slug>")
def article(slug):

    with db() as con:
        item = con.execute(
            "SELECT * FROM articles WHERE slug=%s AND published=1",
            (slug,)
        ).fetchone()

    if not item:
        abort(404)

    return render_template("article.html", article=item)


@app.route("/categorie/<category>")
def category_page(category):

    if category not in CATEGORIES:
        abort(404)

    return redirect(url_for("home", category=category))


# =====================================
# PAGES INFORMATIVES
# =====================================

@app.route("/a-propos")
def about():
    return render_template("page.html", title="À propos", page="about")


@app.route("/confidentialite")
def privacy():
    return render_template(
        "page.html",
        title="Politique de confidentialité",
        page="privacy"
    )


@app.route("/mentions-legales")
def legal():
    return render_template(
        "page.html",
        title="Mentions légales",
        page="legal"
    )


# =====================================
# CONTACT
# =====================================

@app.route("/contact", methods=["GET", "POST"])
def contact():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if name and email and message:

            with db() as con:
                con.execute("""
                    INSERT INTO messages
                    (name, email, message, created_at)
                    VALUES (%s,%s,%s,%s)
                """, (
                    name,
                    email,
                    message,
                    datetime.utcnow().isoformat()
                ))

            flash("Votre message a bien été envoyé.")
            return redirect(url_for("contact"))

        flash("Veuillez remplir tous les champs.")

    return render_template("contact.html")


# =====================================
# REFERENCEMENT
# =====================================

@app.route("/robots.txt")
def robots():

    return Response(
        "User-agent: *\nAllow: /\nSitemap: "
        + request.url_root.rstrip("/")
        + "/sitemap.xml\n",
        mimetype="text/plain"
    )


@app.route("/sitemap.xml")
def sitemap():

    with db() as con:
        rows = con.execute(
            "SELECT slug, created_at FROM articles WHERE published=1"
        ).fetchall()

    urls = [
        f"<url><loc>{request.url_root.rstrip('/')}/</loc></url>"
    ]

    urls += [
        f"<url><loc>{request.url_root.rstrip('/')}/article/{r['slug']}</loc>"
        f"<lastmod>{r['created_at'][:10]}</lastmod></url>"
        for r in rows
    ]

    return Response(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls)
        + "</urlset>",
        mimetype="application/xml"
    )


# =====================================
# CONNEXION ADMINISTRATEUR
# =====================================

@app.route("/admin/login", methods=["GET", "POST"])
def login():

    if not ADMIN_PASSWORD:
        flash("Configurez ADMIN_PASSWORD dans les variables d'environnement.")

    if request.method == "POST":

        if (
            ADMIN_PASSWORD
            and request.form.get("username") == ADMIN_USER
            and secrets.compare_digest(
                request.form.get("password", ""),
                ADMIN_PASSWORD
            )
        ):

            session["admin"] = True

            return redirect(
                request.args.get("next") or url_for("dashboard")
            )

        flash("Identifiants incorrects.")

    return render_template("login.html")


@app.route("/admin/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =====================================
# TABLEAU DE BORD ADMINISTRATEUR
# =====================================

@app.route("/admin")
@admin_required
def dashboard():

    with db() as con:

        articles = con.execute(
            "SELECT * FROM articles ORDER BY created_at DESC"
        ).fetchall()

        messages = con.execute(
            "SELECT * FROM messages ORDER BY created_at DESC LIMIT 20"
        ).fetchall()

    return render_template(
        "admin.html",
        articles=articles,
        messages=messages
    )

@app.route("/admin/statistiques")
@admin_required
def statistiques():
    with db() as con:
        # INDICATEURS DU JOUR
        today = con.execute("""
            SELECT COUNT(*) AS visites,
                   COUNT(DISTINCT visitor_id) AS visiteurs
            FROM site_visits
            WHERE visited_at::date = CURRENT_DATE
        """).fetchone()

        # INDICATEURS DU MOIS EN COURS
        month = con.execute("""
            SELECT COUNT(*) AS visites,
                   COUNT(DISTINCT visitor_id) AS visiteurs
            FROM site_visits
            WHERE visited_at >= DATE_TRUNC('month', CURRENT_DATE)
        """).fetchone()

        # INDICATEURS SUR LES 30 DERNIERS JOURS
        last_30_days = con.execute("""
            SELECT COUNT(*) AS visites,
                   COUNT(DISTINCT visitor_id) AS visiteurs
            FROM site_visits
            WHERE visited_at >= CURRENT_DATE - INTERVAL '29 days'
        """).fetchone()

        # TOTAL DEPUIS LA MISE EN PLACE DU SUIVI
        total = con.execute("""
            SELECT COUNT(*) AS visites,
                   COUNT(DISTINCT visitor_id) AS visiteurs
            FROM site_visits
        """).fetchone()

        # PAGES LES PLUS CONSULTEES
        top_pages = con.execute("""
            SELECT path, COUNT(*) AS visites
            FROM site_visits
            GROUP BY path
            ORDER BY visites DESC
            LIMIT 10
        """).fetchall()

        # FREQUENTATION QUOTIDIENNE DES 30 DERNIERS JOURS
        daily_stats = con.execute("""
            SELECT TO_CHAR(visited_at::date, 'YYYY-MM-DD') AS jour,
                   COUNT(*) AS visites,
                   COUNT(DISTINCT visitor_id) AS visiteurs
            FROM site_visits
            WHERE visited_at >= CURRENT_DATE - INTERVAL '29 days'
            GROUP BY visited_at::date
            ORDER BY visited_at::date
        """).fetchall()

        # ARTICLES LES PLUS LUS
        top_articles = con.execute("""
            SELECT a.title, a.slug, COUNT(v.id) AS visites
            FROM articles AS a
            JOIN site_visits AS v
              ON v.path = '/article/' || a.slug
            WHERE a.published = 1
              AND v.visited_at >= CURRENT_DATE - INTERVAL '29 days'
            GROUP BY a.id, a.title, a.slug
            ORDER BY visites DESC
            LIMIT 10
        """).fetchall()

        # PROVENANCE GEOGRAPHIQUE (pays connus uniquement)
        countries = con.execute("""
            SELECT country_name, country_code, COUNT(*) AS visites,
                   COUNT(DISTINCT visitor_id) AS visiteurs
            FROM site_visits
            WHERE country_name IS NOT NULL
              AND country_name <> 'Non déterminé'
              AND visited_at >= CURRENT_DATE - INTERVAL '29 days'
            GROUP BY country_name, country_code
            ORDER BY visites DESC
            LIMIT 10
        """).fetchall()

    return render_template(
        "statistiques.html",
        today=today,
        month=month,
        last_30_days=last_30_days,
        total=total,
        top_pages=top_pages,
        daily_stats=daily_stats,
        top_articles=top_articles,
        countries=countries
    )


# =====================================
# CREATION ET MODIFICATION DES ARTICLES
# =====================================

@app.route("/admin/article/nouveau", methods=["GET", "POST"])
@app.route("/admin/article/<int:article_id>/modifier", methods=["GET", "POST"])
@admin_required
def edit_article(article_id=None):

    with db() as con:
        item = con.execute(
            "SELECT * FROM articles WHERE id=%s",
            (article_id,)
        ).fetchone() if article_id else None

    if article_id and not item:
        abort(404)

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip().lower()
        category = request.form.get("category", "")
        excerpt = request.form.get("excerpt", "").strip()
        body = request.form.get("body", "").strip()
        image = request.form.get("image_url", "").strip()

        published = 1 if request.form.get("published") else 0

        if not all([title, slug, category, excerpt, body]) or category not in CATEGORIES:

            flash("Veuillez remplir les champs obligatoires.")
            return redirect(request.url)

        try:

            with db() as con:

                if item:

                    con.execute("""
                        UPDATE articles
                        SET title=%s, slug=%s, category=%s,
                            excerpt=%s, body=%s,
                            image_url=%s, published=%s
                        WHERE id=%s
                    """, (
                        title, slug, category,
                        excerpt, body, image,
                        published, article_id
                    ))

                else:

                    con.execute("""
                        INSERT INTO articles
                        (title, slug, category, excerpt, body,
                         image_url, published, created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        title, slug, category,
                        excerpt, body, image,
                        published,
                        datetime.utcnow().isoformat()
                    ))

            flash("Article enregistré.")

            return redirect(url_for("dashboard"))

        except psycopg.IntegrityError:

            flash("Ce lien (slug) existe déjà.")

    return render_template("edit_article.html", article=item)


# =====================================
# SUPPRESSION DES ARTICLES
# =====================================

@app.route("/admin/article/<int:article_id>/supprimer", methods=["POST"])
@admin_required
def delete_article(article_id):

    with db() as con:
        con.execute(
            "DELETE FROM articles WHERE id=%s",
            (article_id,)
        )

    flash("Article supprimé.")

    return redirect(url_for("dashboard"))
# ==========================================
# STATISTIQUES DE FREQUENTATION
# AFRICA INFOS 360
# ==========================================

def init_analytics_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS site_visits (
                id BIGSERIAL PRIMARY KEY,
                visitor_id VARCHAR(100) NOT NULL,
                path TEXT NOT NULL,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_site_visits_date
            ON site_visits (visited_at)
        """)

        con.execute("""
            ALTER TABLE site_visits
            ADD COLUMN IF NOT EXISTS country_name TEXT
        """)
        con.execute("""
            ALTER TABLE site_visits
            ADD COLUMN IF NOT EXISTS country_code VARCHAR(2)
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS visitor_geo (
                visitor_id VARCHAR(100) PRIMARY KEY,
                country_name TEXT,
                country_code VARCHAR(2),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_site_visits_country
            ON site_visits (country_code)
        """)


def get_visitor_country(visitor_id):
    """Retourne le pays approximatif du visiteur sans conserver son adresse IP."""
    try:
        with db() as con:
            cached = con.execute("""
                SELECT country_name, country_code
                FROM visitor_geo
                WHERE visitor_id = %s
                  AND updated_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """, (visitor_id,)).fetchone()

        if cached:
            return cached["country_name"], cached["country_code"]

        # Render transmet généralement l'adresse cliente dans X-Forwarded-For.
        candidates = list(request.access_route)
        if not candidates and request.remote_addr:
            candidates = [request.remote_addr]

        client_ip = None
        for candidate in candidates:
            try:
                parsed_ip = ipaddress.ip_address(candidate.strip())
                if parsed_ip.is_global:
                    client_ip = str(parsed_ip)
                    break
            except ValueError:
                continue

        country_name = "Non déterminé"
        country_code = None

        if client_ip:
            # Le fournisseur reçoit l'IP pour déterminer le pays.
            # L'adresse IP brute n'est jamais enregistrée dans notre base.
            api_url = "https://ipwho.is/" + client_ip
            try:
                with urlopen(api_url, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if payload.get("success"):
                    country_name = payload.get("country") or country_name
                    country_code = payload.get("country_code")
            except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
                app.logger.warning("Géolocalisation indisponible pour un visiteur.")

        with db() as con:
            con.execute("""
                INSERT INTO visitor_geo
                    (visitor_id, country_name, country_code, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (visitor_id) DO UPDATE SET
                    country_name = EXCLUDED.country_name,
                    country_code = EXCLUDED.country_code,
                    updated_at = CURRENT_TIMESTAMP
            """, (visitor_id, country_name, country_code))

        return country_name, country_code

    except Exception:
        app.logger.exception("Erreur pendant la géolocalisation du visiteur.")
        return None, None


@app.before_request
def track_public_visits():

    if request.method != "GET":
        return

    if request.endpoint == "static":
        return

    if request.path.startswith("/admin"):
        return

    if request.path in ["/favicon.ico", "/robots.txt"]:
        return

    visitor_id = session.get("analytics_visitor_id")

    if not visitor_id:
        visitor_id = secrets.token_urlsafe(16)
        session["analytics_visitor_id"] = visitor_id

    country_name, country_code = get_visitor_country(visitor_id)

    try:
        with db() as con:
            con.execute(
                """
                INSERT INTO site_visits
                    (visitor_id, path, country_name, country_code)
                VALUES (%s, %s, %s, %s)
                """,
                (visitor_id, request.path, country_name, country_code)
            )

    except Exception:
        app.logger.exception("Erreur de suivi des visiteurs")

# =====================================
# DEMARRAGE
# =====================================

init_db()
init_analytics_db()

if __name__ == "__main__":
    app.run(debug=False)
