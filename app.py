# app.py completo com exportar PDF, editar e excluir lançamentos, e id em cada registro

from flask import Flask, render_template, request, redirect, session, url_for
import json
from datetime import date, datetime
from uuid import uuid4
from fpdf import FPDF
import os

app = Flask(__name__)
app.secret_key = 'segredo123'

usuarios = {"admin": "12345", "contador": "senha123"}

plano_contas = {
    "1.1.1": "Caixa",
    "1.2.1": "Clientes",
    "2.1.1": "Fornecedores",
    "3.1.1": "Receita de Vendas",
    "4.1.1": "Despesas com Salários"
}

def caminho_usuario():
    return f"lancamentos_{session['usuario']}.json"

def carregar_lancamentos():
    try:
        with open(caminho_usuario(), "r") as f:
            return json.load(f)
    except:
        return []

def salvar_lancamentos(lancamentos):
    with open(caminho_usuario(), "w") as f:
        json.dump(lancamentos, f, indent=4)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["usuario"]
        senha = request.form["senha"]
        if usuarios.get(user) == senha:
            session["usuario"] = user
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", erro="Credenciais inválidas.")
    return render_template("login.html")

@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if "usuario" not in session or session["usuario"] != "admin":
        return redirect(url_for("login"))

    msg = ""
    if request.method == "POST":
        novo_user = request.form["novo_usuario"]
        nova_senha = request.form["nova_senha"]
        if novo_user in usuarios:
            msg = "Usuário já existe!"
        else:
            usuarios[novo_user] = nova_senha
            msg = "Usuário cadastrado com sucesso."
    return render_template("cadastro.html", mensagem=msg)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        data = str(date.today())
        conta = request.form["conta"]
        tipo = request.form["tipo"]
        valor = float(request.form["valor"])
        historico = request.form["historico"]

        lancamentos = carregar_lancamentos()
        lancamentos.append({
            "id": str(uuid4()),
            "data": data,
            "conta": conta,
            "tipo": tipo,
            "valor": valor,
            "historico": historico
        })
        salvar_lancamentos(lancamentos)
        return redirect(url_for("dashboard"))

    lancamentos = carregar_lancamentos()
    total_d = sum(l["valor"] for l in lancamentos if l["tipo"] == "D")
    total_c = sum(l["valor"] for l in lancamentos if l["tipo"] == "C")

    return render_template("dashboard.html", usuario=session["usuario"], contas=plano_contas,
                           total_d=total_d, total_c=total_c)

@app.route("/diario", methods=["GET", "POST"])
def diario():
    if "usuario" not in session:
        return redirect(url_for("login"))

    lancamentos = carregar_lancamentos()
    data_inicio = request.form.get("data_inicio")
    data_fim = request.form.get("data_fim")
    filtrados = lancamentos

    if request.method == "POST" and data_inicio and data_fim:
        try:
            d_ini = datetime.strptime(data_inicio, "%Y-%m-%d").date()
            d_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
            filtrados = [l for l in lancamentos if d_ini <= datetime.strptime(l['data'], "%Y-%m-%d").date() <= d_fim]
        except:
            pass

    return render_template("diario.html", lancamentos=filtrados, plano=plano_contas, data_inicio=data_inicio, data_fim=data_fim)

@app.route("/editar/<id>", methods=["GET", "POST"])
def editar(id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    lancamentos = carregar_lancamentos()
    lancamento = next((l for l in lancamentos if l["id"] == id), None)

    if not lancamento:
        return "Lançamento não encontrado."

    if request.method == "POST":
        lancamento["conta"] = request.form["conta"]
        lancamento["tipo"] = request.form["tipo"]
        lancamento["valor"] = float(request.form["valor"])
        lancamento["historico"] = request.form["historico"]
        salvar_lancamentos(lancamentos)
        return redirect(url_for("diario"))

    return render_template("editar.html", lancamento=lancamento, plano=plano_contas)

@app.route("/excluir/<id>")
def excluir(id):
    if "usuario" not in session:
        return redirect(url_for("login"))
    lancamentos = carregar_lancamentos()
    lancamentos = [l for l in lancamentos if l["id"] != id]
    salvar_lancamentos(lancamentos)
    return redirect(url_for("diario"))

@app.route("/razao")
def razao():
    if "usuario" not in session:
        return redirect(url_for("login"))
    lancamentos = carregar_lancamentos()
    contas = {}
    for l in lancamentos:
        contas.setdefault(l['conta'], []).append(l)
    return render_template("razao.html", contas=contas, plano=plano_contas)

@app.route("/balancete")
def balancete():
    if "usuario" not in session:
        return redirect(url_for("login"))
    lancamentos = carregar_lancamentos()
    saldos = {}
    for l in lancamentos:
        cod = l["conta"]
        if cod not in saldos:
            saldos[cod] = {"D": 0, "C": 0}
        saldos[cod][l["tipo"]] += l["valor"]
    return render_template("balancete.html", saldos=saldos, plano=plano_contas)

@app.route("/exportar_diario")
def exportar_diario():
    if "usuario" not in session:
        return redirect(url_for("login"))

    lancamentos = carregar_lancamentos()
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Livro Diário", ln=1, align="C")

    for l in lancamentos:
        linha = f"{l['data']} | {plano_contas.get(l['conta'], l['conta'])} ({l['conta']}) | {'D' if l['tipo'] == 'D' else 'C'} | R$ {l['valor']:.2f} | {l['historico']}"
        pdf.multi_cell(0, 10, txt=linha)

    nome_arquivo = f"livro_diario_{session['usuario']}.pdf"
    pdf.output(nome_arquivo)
    return f"PDF gerado com sucesso: {nome_arquivo}"

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
