from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash


UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"py", "cpp", "txt", "html", "js"}



app = Flask(__name__)
app.secret_key = 'super-secret-key'

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY,
              username TEXT UNIQUE,
              password TEXT,
              role TEXT -- 'admin' sau 'user'
              )
''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS proiecte (
            id INTEGER PRIMARY KEY,
            titlu TEXT,
            fisier TEXT,
            descriere TEXT, 
            autor TEXT
)

''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS comentarii (
        id INTEGER PRIMARY KEY,
        proiect_id INTEGER,
        autor TEXT,
        continut TEXT,
        FOREIGN KEY (proiect_id) REFERENCES proiecte(id)
    )
''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS taskuri (
            id INTEGER PRIMARY KEY,
            titlu TEXT,
            descriere TEXT,
            creator TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS rezolvari (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            autor TEXT,
            fisier TEXT,
            comentariu TEXT,
            FOREIGN KEY (task_id) REFERENCES taskuri(id)
        )
    ''')
    


    conn.commit()
    conn.close()

@app.route("/")
def index():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if session.get("role") == "admin":
        c.execute("SELECT * FROM proiecte")
    elif session.get("user"):
        c.execute("SELECT * FROM proiecte WHERE autor = ?", (session["user"],))
    else:
        conn.close()
        return render_template("index.html", proiecte=[], comentarii={})

    proiecte = c.fetchall()

    c.execute("SELECT proiect_id, autor, continut FROM comentarii")
    comentarii_raw = c.fetchall()
    conn.close()

    comentarii = {}
    for proiect_id, autor, continut in comentarii_raw:
        comentarii.setdefault(proiect_id, []).append((autor, continut))

    return render_template("index.html", proiecte=proiecte, comentarii=comentarii)


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"].strip()
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()

    if user and check_password_hash(user[2], password):  # user[2] este coloana cu parola
        session["user"] = username
        session["role"] = user[3]
    else:
        print("Autentificare eșuată")

    conn.close()

    if user:
        print("S-a autentificat:", user)
        session["user"] = username
        session["role"] = user[3]
    else:
        print("Autentificare eșuată")
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"].strip()
    password = generate_password_hash(request.form["password"].strip())

    role = request.form.get("role", "user")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing_user = c.fetchone()

    if existing_user:
        conn.close()
        return redirect("/?modal=login&error=Numele+de+utilizator+este+deja+folosit")

    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  (username, password, role))
        conn.commit()
    except:
        conn.close()
        return redirect("/?modal=login&error=Eroare+la+înregistrare")

    conn.close()
    return redirect("/?modal=login&success=Contul+a+fost+creat+cu+succes")


@app.route("/adauga-proiect", methods=["POST"])
def adauga_proiect():
    if session.get("role") != "user":
        return redirect("/")

    titlu = request.form["titlu"]
    descriere = request.form["descriere"]
    fisier = request.files["fisier"]
    autor = session.get("user")

    if fisier and allowed_file(fisier.filename):
        filename = secure_filename(fisier.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        fisier.save(path)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO proiecte (titlu, fisier, descriere, autor) VALUES (?, ?, ?, ?)",
                  (titlu, filename, descriere, autor))
        conn.commit()
        conn.close()

    return redirect("/")

@app.route("/adauga-comentariu/<int:proiect_id>", methods=["POST"])
def adauga_comentariu(proiect_id):
    if session.get("role") != "admin":
        return redirect("/")

    continut = request.form["continut"]
    autor = session.get("user")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO comentarii (proiect_id, autor, continut) VALUES (?, ?, ?)",
              (proiect_id, autor, continut))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/editeaza-proiect/<int:id>", methods=["GET", "POST"])
def editeaza_proiect(id):
    if session.get("role") != "user":
        return redirect("/")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT id, titlu, fisier, descriere, autor FROM proiecte WHERE id = ?", (id,))
    proiect = c.fetchone()

    if not proiect or proiect[4] != session.get("user"):
        conn.close()
        return redirect("/")

    if request.method == "POST":
        titlu = request.form["titlu"]
        descriere = request.form["descriere"]
        fisier = request.files.get("fisier", None)

        filename = proiect[2]  

        if fisier and fisier.filename and allowed_file(fisier.filename):
            filename = secure_filename(fisier.filename)
            fisier.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        c.execute("UPDATE proiecte SET titlu=?, fisier=?, descriere=? WHERE id=?",
                  (titlu, filename, descriere, id))
        conn.commit()
        conn.close()
        return redirect("/")

    conn.close()
    return render_template("editeaza.html", proiect=proiect)

@app.route("/taskuri")
def taskuri():
    if not session.get("user"):
        return redirect("/")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Oricine vede toate taskurile
    c.execute("SELECT id, titlu, descriere, creator FROM taskuri")
    taskuri = c.fetchall()

    conn.close()
    return render_template("taskuri.html", taskuri=taskuri)



@app.route("/adauga-task", methods=["GET", "POST"])
def adauga_task():
    if session.get("role") != "admin":
        return redirect("/taskuri")

    if request.method == "POST":
        titlu = request.form["titlu"]
        descriere = request.form["descriere"]
        creator = session.get("user")

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO taskuri (titlu, descriere, creator) VALUES (?, ?, ?)", (titlu, descriere, creator))
        conn.commit()
        conn.close()

        return redirect("/taskuri")

    return render_template("adauga_task.html")



@app.route("/rezolva-task/<int:task_id>", methods=["GET", "POST"])
def rezolva_task(task_id):
    if session.get("role") != "user":
        return redirect("/taskuri")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, titlu, descriere FROM taskuri WHERE id = ?", (task_id,))
    task = c.fetchone()
    conn.close()

    if not task:
        return redirect("/taskuri")

    if request.method == "POST":
        fisier = request.files.get("fisier")
        comentariu = request.form["comentariu"]
        autor = session.get("user")

        if fisier and fisier.filename and allowed_file(fisier.filename):
            filename = secure_filename(fisier.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            fisier.save(save_path)

            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("INSERT INTO rezolvari (task_id, autor, fisier, comentariu) VALUES (?, ?, ?, ?)",
                      (task_id, autor, filename, comentariu))
            conn.commit()
            conn.close()

        return redirect("/taskuri")

    return render_template("rezolva_task.html", task=task)


@app.route("/rezolvari/<int:task_id>")
def vezi_rezolvari(task_id):
    if session.get("role") != "admin":
        return redirect("/taskuri")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT titlu FROM taskuri WHERE id = ?", (task_id,))
    task = c.fetchone()

    if not task:
        conn.close()
        return redirect("/taskuri")

    c.execute("SELECT autor, fisier, comentariu FROM rezolvari WHERE task_id = ?", (task_id,))
    rezolvari = c.fetchall()
    conn.close()

    return render_template("rezolvari.html", task=task, rezolvari=rezolvari)

@app.route("/preview/<int:id>")
def preview(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT fisier FROM proiecte WHERE id = ?", (id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return "Proiect inexistent", 404

    filename = row[0]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return f"Nu s-a putut citi fișierul: {str(e)}"

    return render_template("preview.html", filename=filename, content=content)

@app.route("/taskurile-mele")
def taskurile_mele():
    if not session.get("user"):
        return redirect("/")

    username = session["user"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''
        SELECT t.id, t.titlu, t.descriere, t.creator
        FROM taskuri t
        JOIN task_asignments ta ON t.id = ta.task_id
        WHERE ta.username = ?
    ''', (username,))
    
    taskuri = c.fetchall()
    conn.close()

    return render_template("taskurile_mele.html", taskuri=taskuri)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

