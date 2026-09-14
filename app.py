
# ============================================================
#  MerendaNaMedida
#  Developed by @alvelin0
# ============================================================

import sys
import traceback
from pathlib import Path


def _crash_handler(exc_type, exc_value, exc_tb):
    """Se QUALQUER erro não tratado acontecer (mesmo ao carregar o
    programa, antes do Flask iniciar), isso evita que a janela do .exe
    simplesmente feche sozinha sem explicação. Grava o erro num arquivo
    e espera o usuário apertar Enter antes de fechar."""
    traceback.print_exception(exc_type, exc_value, exc_tb)
    if getattr(sys, "frozen", False):
        try:
            base = Path(sys.executable).resolve().parent
            erro_path = base / "erro.txt"
            with open(erro_path, "w", encoding="utf-8") as f:
                f.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
            print(f"\nOcorreu um erro ao iniciar o MerendaNaMedida.")
            print(f"Detalhes foram salvos em: {erro_path}")
        except Exception:
            pass
        input("\nPressione Enter para sair...")


sys.excepthook = _crash_handler

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
import threading
import webbrowser
from datetime import date

def resource_path(relative):
    """Caminho para arquivos empacotados (templates/static): funciona tanto
    rodando 'python app.py' normalmente quanto dentro do .exe gerado pelo
    PyInstaller (que extrai tudo numa pasta temporária, sys._MEIPASS)."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return base / relative

def data_path(filename):
    """Caminho para arquivos que precisam ser GRAVADOS (o banco de dados).
    Sempre fica ao lado do executável/script, nunca dentro da pasta
    temporária do PyInstaller (que é apagada quando o programa fecha)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent
    return base / filename

BASE = Path(__file__).resolve().parent
DB = data_path("merenda.db")

app = Flask(
    __name__,
    template_folder=str(resource_path("templates")),
    static_folder=str(resource_path("static")),
)
app.secret_key = "troque-esta-chave-em-producao"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS escola (
        id INTEGER PRIMARY KEY CHECK (id=1),
        nome TEXT NOT NULL DEFAULT 'Escola Municipal Exemplo',
        margem REAL NOT NULL DEFAULT 0.03
    );

    CREATE TABLE IF NOT EXISTS turmas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        serie TEXT NOT NULL,
        ativo INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        turma_id INTEGER NOT NULL,
        ativo INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(turma_id) REFERENCES turmas(id)
    );

    CREATE TABLE IF NOT EXISTS professores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        ativo INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS ingredientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        quantidade_por_refeicao REAL NOT NULL,
        unidade TEXT NOT NULL DEFAULT 'g',
        ativo INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS cardapios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL,
        refeicao TEXT NOT NULL,
        nome TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS presencas_alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL,
        aluno_id INTEGER NOT NULL,
        presente INTEGER NOT NULL DEFAULT 0,
        UNIQUE(data, aluno_id),
        FOREIGN KEY(aluno_id) REFERENCES alunos(id)
    );

    CREATE TABLE IF NOT EXISTS presencas_professores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL,
        professor_id INTEGER NOT NULL,
        presente INTEGER NOT NULL DEFAULT 0,
        UNIQUE(data, professor_id),
        FOREIGN KEY(professor_id) REFERENCES professores(id)
    );

    CREATE TABLE IF NOT EXISTS consumo_merenda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL UNIQUE,
        refeicoes_previstas INTEGER NOT NULL,
        refeicoes_preparadas INTEGER,
        sobra_kg REAL DEFAULT 0,
        descarte_kg REAL DEFAULT 0
    );

    INSERT OR IGNORE INTO escola(id, nome, margem) VALUES(1, 'Escola Municipal Exemplo', 0.03);
    """)
    # Dados iniciais apenas para o sistema abrir já demonstrável.
    if conn.execute("SELECT COUNT(*) FROM turmas").fetchone()[0] == 0:
        turmas = [
            ("1º Ano A","1º Ano"),("1º Ano B","1º Ano"),
            ("2º Ano A","2º Ano"),("2º Ano B","2º Ano"),
            ("3º Ano A","3º Ano"),("3º Ano B","3º Ano")
        ]
        conn.executemany("INSERT INTO turmas(nome,serie) VALUES(?,?)", turmas)

    if conn.execute("SELECT COUNT(*) FROM ingredientes").fetchone()[0] == 0:
        ing = [
            ("Arroz",80,"g"),("Feijão",50,"g"),("Carne bovina",100,"g"),
            ("Cenoura",30,"g"),("Batata",40,"g"),("Alface",20,"g"),
            ("Tomate",15,"g"),("Banana",100,"g")
        ]
        conn.executemany(
            "INSERT INTO ingredientes(nome,quantidade_por_refeicao,unidade) VALUES(?,?,?)", ing
        )
    conn.commit()
    conn.close()

def people_counts(d):
    conn = get_db()
    alunos = conn.execute(
        "SELECT COUNT(*) FROM presencas_alunos WHERE data=? AND presente=1", (d,)
    ).fetchone()[0]
    professores = conn.execute(
        "SELECT COUNT(*) FROM presencas_professores WHERE data=? AND presente=1", (d,)
    ).fetchone()[0]
    conn.close()
    return alunos, professores

@app.route("/")
def index():
    d = request.args.get("data") or date.today().isoformat()
    alunos, professores = people_counts(d)
    conn = get_db()
    escola = conn.execute("SELECT * FROM escola WHERE id=1").fetchone()
    ingredientes = conn.execute(
        "SELECT * FROM ingredientes WHERE ativo=1 ORDER BY nome"
    ).fetchall()
    turmas = conn.execute(
        "SELECT t.*, COUNT(a.id) AS qtd FROM turmas t LEFT JOIN alunos a ON a.turma_id=t.id AND a.ativo=1 GROUP BY t.id ORDER BY t.nome"
    ).fetchall()
    conn.close()
    base = alunos + professores
    total = round(base * (1 + escola["margem"]))
    return render_template(
        "index.html", data=d, alunos=alunos, professores=professores,
        base=base, total=total, escola=escola, ingredientes=ingredientes, turmas=turmas
    )

@app.route("/turmas", methods=["GET","POST"])
def turmas():
    conn = get_db()
    if request.method == "POST":
        nome = request.form["nome"].strip()
        serie = request.form["serie"].strip()
        try:
            conn.execute("INSERT INTO turmas(nome,serie) VALUES(?,?)", (nome,serie))
            conn.commit()
            flash("Turma adicionada.")
        except sqlite3.IntegrityError:
            flash("Essa turma já existe.")
        conn.close()
        return redirect(url_for("turmas"))
    rows = conn.execute("SELECT * FROM turmas ORDER BY nome").fetchall()
    conn.close()
    return render_template("crud.html", title="Turmas", kind="turmas", rows=rows)

@app.route("/turmas/<int:id>/excluir", methods=["POST"])
def excluir_turma(id):
    conn = get_db()
    conn.execute("UPDATE turmas SET ativo=0 WHERE id=?", (id,))
    conn.commit(); conn.close()
    return redirect(url_for("turmas"))

@app.route("/alunos", methods=["GET","POST"])
def alunos():
    conn = get_db()
    if request.method == "POST":
        conn.execute("INSERT INTO alunos(nome,turma_id) VALUES(?,?)",
                     (request.form["nome"].strip(), request.form["turma_id"]))
        conn.commit()
        flash("Aluno adicionado.")
        conn.close()
        return redirect(url_for("alunos"))
    rows = conn.execute("""
        SELECT a.id,a.nome,t.nome turma FROM alunos a
        JOIN turmas t ON t.id=a.turma_id
        WHERE a.ativo=1 ORDER BY t.nome,a.nome
    """).fetchall()
    classes = conn.execute("SELECT * FROM turmas WHERE ativo=1 ORDER BY nome").fetchall()
    conn.close()
    return render_template("crud.html", title="Alunos", kind="alunos", rows=rows, classes=classes)

@app.route("/alunos/<int:id>/excluir", methods=["POST"])
def excluir_aluno(id):
    conn = get_db(); conn.execute("UPDATE alunos SET ativo=0 WHERE id=?", (id,)); conn.commit(); conn.close()
    return redirect(url_for("alunos"))

@app.route("/alunos/<int:id>/apagar", methods=["POST"])
def apagar_aluno(id):
    conn = get_db()
    conn.execute("DELETE FROM presencas_alunos WHERE aluno_id=?", (id,))
    conn.execute("DELETE FROM alunos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Aluno apagado permanentemente.")
    return redirect(url_for("alunos"))

@app.route("/professores", methods=["GET","POST"])
def professores():
    conn = get_db()
    if request.method == "POST":
        conn.execute("INSERT INTO professores(nome) VALUES(?)", (request.form["nome"].strip(),))
        conn.commit(); flash("Professor adicionado."); conn.close()
        return redirect(url_for("professores"))
    rows = conn.execute("SELECT * FROM professores WHERE ativo=1 ORDER BY nome").fetchall()
    conn.close()
    return render_template("crud.html", title="Professores", kind="professores", rows=rows)

@app.route("/professores/<int:id>/excluir", methods=["POST"])
def excluir_professor(id):
    conn = get_db(); conn.execute("UPDATE professores SET ativo=0 WHERE id=?", (id,)); conn.commit(); conn.close()
    return redirect(url_for("professores"))

@app.route("/professores/<int:id>/apagar", methods=["POST"])
def apagar_professor(id):
    conn = get_db()
    conn.execute("DELETE FROM presencas_professores WHERE professor_id=?", (id,))
    conn.execute("DELETE FROM professores WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Professor apagado permanentemente.")
    return redirect(url_for("professores"))

@app.route("/ingredientes", methods=["GET","POST"])
def ingredientes():
    conn = get_db()
    if request.method == "POST":
        try:
            conn.execute(
                "INSERT INTO ingredientes(nome,quantidade_por_refeicao,unidade) VALUES(?,?,?)",
                (request.form["nome"].strip(), float(request.form["quantidade"]), request.form["unidade"])
            )
            conn.commit(); flash("Ingrediente adicionado.")
        except (sqlite3.IntegrityError, ValueError):
            flash("Não foi possível adicionar o ingrediente.")
        conn.close()
        return redirect(url_for("ingredientes"))
    rows = conn.execute("SELECT * FROM ingredientes WHERE ativo=1 ORDER BY nome").fetchall()
    conn.close()
    return render_template("crud.html", title="Ingredientes", kind="ingredientes", rows=rows)

@app.route("/ingredientes/<int:id>/excluir", methods=["POST"])
def excluir_ingrediente(id):
    conn = get_db(); conn.execute("UPDATE ingredientes SET ativo=0 WHERE id=?", (id,)); conn.commit(); conn.close()
    return redirect(url_for("ingredientes"))

@app.route("/presenca", methods=["GET","POST"])
def presenca():
    d = request.args.get("data") or request.form.get("data") or date.today().isoformat()
    conn = get_db()
    if request.method == "POST":
        conn.execute("DELETE FROM presencas_alunos WHERE data=?", (d,))
        conn.execute("DELETE FROM presencas_professores WHERE data=?", (d,))
        for aid in request.form.getlist("aluno_presente"):
            conn.execute("INSERT INTO presencas_alunos(data,aluno_id,presente) VALUES(?,?,1)", (d,aid))
        for pid in request.form.getlist("professor_presente"):
            conn.execute("INSERT INTO presencas_professores(data,professor_id,presente) VALUES(?,?,1)", (d,pid))
        conn.commit(); flash("Presença salva.")
    alunos_rows = conn.execute("""
        SELECT a.*, t.nome turma,
        COALESCE((SELECT presente FROM presencas_alunos p WHERE p.data=? AND p.aluno_id=a.id),0) presente
        FROM alunos a JOIN turmas t ON t.id=a.turma_id
        WHERE a.ativo=1 ORDER BY t.nome,a.nome
    """,(d,)).fetchall()
    prof_rows = conn.execute("""
        SELECT p.*,
        COALESCE((SELECT presente FROM presencas_professores x WHERE x.data=? AND x.professor_id=p.id),0) presente
        FROM professores p WHERE p.ativo=1 ORDER BY p.nome
    """,(d,)).fetchall()
    conn.close()
    return render_template("presenca.html", data=d, alunos=alunos_rows, professores=prof_rows)

@app.route("/cardapio", methods=["GET","POST"])
def cardapio():
    conn = get_db()
    if request.method == "POST":
        conn.execute("INSERT INTO cardapios(data,refeicao,nome) VALUES(?,?,?)",
                     (request.form["data"],request.form["refeicao"],request.form["nome"].strip()))
        conn.commit(); flash("Cardápio adicionado.")
    rows = conn.execute("SELECT * FROM cardapios ORDER BY data DESC").fetchall()
    conn.close()
    return render_template("cardapio.html", rows=rows)

@app.route("/relatorios")
def relatorios():
    conn = get_db()
    rows = conn.execute("""
      SELECT data,refeicoes_previstas,refeicoes_preparadas,sobra_kg,descarte_kg
      FROM consumo_merenda ORDER BY data DESC LIMIT 60
    """).fetchall()
    conn.close()
    return render_template("relatorios.html", rows=rows)

@app.route("/config", methods=["GET","POST"])
def config():
    conn = get_db()
    if request.method == "POST":
        conn.execute("UPDATE escola SET nome=?, margem=? WHERE id=1",
                     (request.form["nome"], float(request.form["margem"])/100))
        conn.commit(); flash("Configurações salvas.")
    escola = conn.execute("SELECT * FROM escola WHERE id=1").fetchone()
    conn.close()
    return render_template("config.html", escola=escola)

@app.route("/limpar", methods=["GET", "POST"])
def limpar():
    if request.method == "POST":
        confirmacao = request.form.get("confirmacao", "").strip().upper()
        itens = request.form.getlist("itens")

        if not itens:
            flash("Selecione ao menos um item para apagar.")
            return redirect(url_for("limpar"))

        if confirmacao != "APAGAR":
            flash('Digite a palavra APAGAR (em maiúsculas) para confirmar.')
            return redirect(url_for("limpar"))

        conn = get_db()

        if "turmas" in itens or "alunos" in itens:
            conn.execute("DELETE FROM presencas_alunos")
            conn.execute("DELETE FROM alunos")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='alunos'")

        if "turmas" in itens:
            conn.execute("DELETE FROM turmas")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='turmas'")

        if "professores" in itens:
            conn.execute("DELETE FROM presencas_professores")
            conn.execute("DELETE FROM professores")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='professores'")

        if "ingredientes" in itens:
            conn.execute("DELETE FROM ingredientes")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='ingredientes'")

        if "cardapios" in itens:
            conn.execute("DELETE FROM cardapios")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='cardapios'")

        if "relatorios" in itens:
            conn.execute("DELETE FROM consumo_merenda")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='consumo_merenda'")

        conn.commit()
        conn.close()
        flash("Dados apagados com sucesso.")
        return redirect(url_for("limpar"))

    return render_template("limpar.html")

@app.route("/api/calculo")
def api_calculo():
    d = request.args.get("data") or date.today().isoformat()
    alunos, professores = people_counts(d)
    conn = get_db()
    escola = conn.execute("SELECT margem FROM escola WHERE id=1").fetchone()
    ings = conn.execute("SELECT nome,quantidade_por_refeicao,unidade FROM ingredientes WHERE ativo=1 ORDER BY nome").fetchall()
    conn.close()
    base = alunos + professores
    total = int(base * (1 + escola["margem"]) + 0.9999)
    return jsonify({
        "data": d, "alunos": alunos, "professores": professores,
        "refeicoes_base": base, "refeicoes_com_margem": total,
        "ingredientes": [
            {"nome":x["nome"],"quantidade":x["quantidade_por_refeicao"]*total,"unidade":x["unidade"]}
            for x in ings
        ]
    })

if __name__ == "__main__":
    init_db()
    if getattr(sys, "frozen", False):
        # Rodando como .exe empacotado: abre o navegador sozinho e
        # desliga o modo debug (recomendado para uso fora de desenvolvimento).
        # host="0.0.0.0" permite que outros dispositivos na mesma rede
        # Wi-Fi (celulares, tablets) acessem o sistema também.
        threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
        app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
