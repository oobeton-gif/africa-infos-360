import os, sqlite3, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort, session, Response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE-ME-BEFORE-PUBLISHING-" + secrets.token_hex(16))
DB = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "africa_infos.db"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

CATEGORIES = ["Actualités", "Emploi", "Concours", "Formation", "Business", "Finance",
              "Technologie", "Immobilier", "Éducation", "Guides pratiques"]

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS articles(
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL, excerpt TEXT NOT NULL, body TEXT NOT NULL,
            image_url TEXT DEFAULT '', author TEXT DEFAULT 'La rédaction',
            published INTEGER DEFAULT 1, created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, message TEXT,
            created_at TEXT NOT NULL)""")
        count = con.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        if count == 0:
            samples = [
              ("Bienvenue sur Africa Infos 360", "bienvenue-africa-infos-360", "Actualités",
               "Un média indépendant pour comprendre l'actualité et découvrir les opportunités en Afrique.",
               "Africa Infos 360 est un média numérique généraliste consacré à l'information utile en Afrique francophone. Notre ambition est de proposer des contenus clairs, vérifiés et accessibles sur l'actualité, l'emploi, la formation, l'entrepreneuriat, la technologie et la vie pratique.\\n\\nLes informations importantes sont datées et accompagnées, lorsque cela est possible, de liens vers les sources officielles. Les lecteurs sont invités à vérifier les conditions et échéances auprès des organismes concernés.",
               "", "La rédaction"),
              ("Comment préparer efficacement sa recherche d'emploi", "preparer-recherche-emploi", "Emploi",
               "CV, lettre de motivation, veille et préparation aux entretiens : les étapes essentielles.",
               "Une recherche d'emploi efficace commence par un objectif professionnel clair. Identifiez les secteurs et les postes correspondant à vos compétences, puis adaptez votre CV à chaque candidature.\\n\\nPrivilégiez les informations concrètes : expériences, résultats, formations et compétences. Préparez également une présentation courte de votre parcours et renseignez-vous sur l'entreprise avant un entretien.\\n\\nConsultez régulièrement les plateformes et sites officiels des employeurs. Ne payez jamais des frais à un prétendu recruteur sans avoir vérifié l'authenticité de l'offre.",
               "", "La rédaction"),
              ("Les étapes pour structurer une petite activité commerciale", "structurer-petite-activite-commerciale", "Business",
               "Quelques repères pour passer d'une idée à une activité organisée et durable.",
               "Avant de lancer une activité, vérifiez qu'il existe une demande réelle. Échangez avec de futurs clients, observez les concurrents et estimez vos coûts.\\n\\nÉtablissez un budget de démarrage, séparez autant que possible les finances personnelles et professionnelles et conservez les justificatifs. Définissez un prix qui couvre les charges et permet une marge raisonnable.\\n\\nRenseignez-vous auprès des organismes compétents sur les formalités applicables à votre activité et à votre pays.",
               "", "La rédaction")
            ]
            for title, slug, cat, excerpt, body, image, author in samples:
                con.execute("INSERT INTO articles(title,slug,category,excerpt,body,image_url,author,published,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                            (title, slug, cat, excerpt, body, image, author, 1, datetime.utcnow().isoformat()))

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"): return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_globals():
    return {"categories": CATEGORIES, "year": datetime.now().year}

@app.route("/")
def home():
    category = request.args.get("category", "")
    q = request.args.get("q", "").strip()
    con = db()
    sql = "SELECT * FROM articles WHERE published=1"
    params = []
    if category in CATEGORIES:
        sql += " AND category=?"; params.append(category)
    if q:
        sql += " AND (title LIKE ? OR excerpt LIKE ? OR body LIKE ?)"
        params += [f"%{q}%"]*3
    sql += " ORDER BY created_at DESC LIMIT 30"
    articles = con.execute(sql, params).fetchall()
    return render_template("home.html", articles=articles, selected=category, q=q)

@app.route("/article/<slug>")
def article(slug):
    item = db().execute("SELECT * FROM articles WHERE slug=? AND published=1", (slug,)).fetchone()
    if not item: abort(404)
    return render_template("article.html", article=item)

@app.route("/categorie/<category>")
def category_page(category):
    if category not in CATEGORIES: abort(404)
    return redirect(url_for("home", category=category))

@app.route("/a-propos")
def about(): return render_template("page.html", title="À propos", page="about")
@app.route("/confidentialite")
def privacy(): return render_template("page.html", title="Politique de confidentialité", page="privacy")
@app.route("/mentions-legales")
def legal(): return render_template("page.html", title="Mentions légales", page="legal")
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip(); message=request.form.get("message","").strip()
        if name and email and message:
            with db() as con:
                con.execute("INSERT INTO messages(name,email,message,created_at) VALUES(?,?,?,?)",
                            (name,email,message,datetime.utcnow().isoformat()))
            flash("Votre message a bien été envoyé.")
            return redirect(url_for("contact"))
        flash("Veuillez remplir tous les champs.")
    return render_template("contact.html")

@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\\nAllow: /\\nSitemap: " + request.url_root.rstrip("/") + "/sitemap.xml\\n", mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap():
    rows=db().execute("SELECT slug,created_at FROM articles WHERE published=1").fetchall()
    urls=[f"<url><loc>{request.url_root.rstrip('/')}/</loc></url>"]
    urls += [f"<url><loc>{request.url_root.rstrip('/')}/article/{r['slug']}</loc><lastmod>{r['created_at'][:10]}</lastmod></url>" for r in rows]
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(urls)+'</urlset>', mimetype="application/xml")

@app.route("/admin/login", methods=["GET","POST"])
def login():
    if not ADMIN_PASSWORD:
        flash("Configurez ADMIN_PASSWORD dans les variables d'environnement avant d'activer l'administration.")
    if request.method=="POST":
        if ADMIN_PASSWORD and request.form.get("username")==ADMIN_USER and secrets.compare_digest(request.form.get("password",""), ADMIN_PASSWORD):
            session["admin"]=True
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Identifiants incorrects.")
    return render_template("login.html")

@app.route("/admin/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def dashboard():
    con=db()
    articles=con.execute("SELECT * FROM articles ORDER BY created_at DESC").fetchall()
    messages=con.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT 20").fetchall()
    return render_template("admin.html", articles=articles, messages=messages)

@app.route("/admin/article/nouveau", methods=["GET","POST"])
@app.route("/admin/article/<int:article_id>/modifier", methods=["GET","POST"])
@admin_required
def edit_article(article_id=None):
    con=db()
    item=con.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone() if article_id else None
    if request.method=="POST":
        title=request.form.get("title","").strip()
        slug=request.form.get("slug","").strip().lower()
        category=request.form.get("category","")
        excerpt=request.form.get("excerpt","").strip()
        body=request.form.get("body","").strip()
        image=request.form.get("image_url","").strip()
        published=1 if request.form.get("published") else 0
        if not all([title,slug,category,excerpt,body]) or category not in CATEGORIES:
            flash("Veuillez remplir les champs obligatoires."); return redirect(request.url)
        try:
            with db() as con:
                if item:
                    con.execute("UPDATE articles SET title=?,slug=?,category=?,excerpt=?,body=?,image_url=?,published=? WHERE id=?",
                                (title,slug,category,excerpt,body,image,published,article_id))
                else:
                    con.execute("INSERT INTO articles(title,slug,category,excerpt,body,image_url,published,created_at) VALUES(?,?,?,?,?,?,?,?)",
                                (title,slug,category,excerpt,body,image,published,datetime.utcnow().isoformat()))
            flash("Article enregistré."); return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Ce lien (slug) existe déjà.")
    return render_template("edit_article.html", article=item)

@app.route("/admin/article/<int:article_id>/supprimer", methods=["POST"])
@admin_required
def delete_article(article_id):
    with db() as con: con.execute("DELETE FROM articles WHERE id=?", (article_id,))
    flash("Article supprimé."); return redirect(url_for("dashboard"))

init_db()
if __name__ == "__main__":
    app.run(debug=True)
