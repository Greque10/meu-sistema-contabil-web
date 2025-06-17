from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import json
from datetime import datetime, timedelta
import os
import uuid
import io
import csv

# Para PDF com ReportLab
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_multi_empresa_muito_forte' 

# --- Constantes para nomes de ficheiros e diretórios ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ARQUIVO_EMPRESAS = os.path.join(BASE_DIR, 'empresas.json')

NOME_ARQUIVO_LANCAMENTOS = 'lancamentos.json'
NOME_ARQUIVO_USUARIOS = 'usuarios.json'
NOME_ARQUIVO_CONTAS = 'contas.json'
NOME_ARQUIVO_HISTORICO = 'historico_lancamentos.json'

# --- Funções Auxiliares (Completas) ---
def carregar_empresas():
    if not os.path.exists(ARQUIVO_EMPRESAS): return {}
    try:
        with open(ARQUIVO_EMPRESAS, 'r', encoding='utf-8') as f:
            content = f.read()
            return json.loads(content) if content else {}
    except (json.JSONDecodeError, FileNotFoundError): return {}

def salvar_empresas(empresas):
    with open(ARQUIVO_EMPRESAS, 'w', encoding='utf-8') as f:
        json.dump(empresas, f, indent=4, ensure_ascii=False)

def obter_caminho_arquivo_empresa(id_empresa, nome_arquivo):
    return os.path.join(DATA_DIR, str(id_empresa), nome_arquivo)

def carregar_dados_empresa(id_empresa, nome_arquivo_base):
    arquivo = obter_caminho_arquivo_empresa(id_empresa, nome_arquivo_base)
    if not os.path.exists(arquivo):
        return [] if nome_arquivo_base in [NOME_ARQUIVO_LANCAMENTOS, NOME_ARQUIVO_HISTORICO] else {}
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return [] if nome_arquivo_base in [NOME_ARQUIVO_LANCAMENTOS, NOME_ARQUIVO_HISTORICO] else {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return [] if nome_arquivo_base in [NOME_ARQUIVO_LANCAMENTOS, NOME_ARQUIVO_HISTORICO] else {}

def salvar_dados_empresa(id_empresa, dados, nome_arquivo_base):
    caminho_pasta_empresa = os.path.join(DATA_DIR, str(id_empresa))
    if not os.path.exists(caminho_pasta_empresa):
        os.makedirs(caminho_pasta_empresa)
    
    arquivo = obter_caminho_arquivo_empresa(id_empresa, nome_arquivo_base)
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_lancamentos_empresa(id_empresa):
    return carregar_dados_empresa(id_empresa, NOME_ARQUIVO_LANCAMENTOS)

def salvar_lancamentos_empresa(id_empresa, lancamentos):
    salvar_dados_empresa(id_empresa, lancamentos, NOME_ARQUIVO_LANCAMENTOS)

def carregar_usuarios_empresa(id_empresa):
    return carregar_dados_empresa(id_empresa, NOME_ARQUIVO_USUARIOS)

def salvar_usuarios_empresa(id_empresa, usuarios):
    salvar_dados_empresa(id_empresa, usuarios, NOME_ARQUIVO_USUARIOS)

def carregar_contas_empresa(id_empresa):
    contas = carregar_dados_empresa(id_empresa, NOME_ARQUIVO_CONTAS)
    if not contas:
        plano_de_contas_inicial = {
            "10101": {"nome": "Caixa Geral", "natureza": "D"}, "10102": {"nome": "Bancos Conta Movimento", "natureza": "D"},
            "20101": {"nome": "Fornecedores Nacionais", "natureza": "C"}, "20102": {"nome": "Salários a Pagar", "natureza": "C"},
            "30101": {"nome": "Receita Bruta de Vendas", "natureza": "C"}, "30102": {"nome": "Receita de Serviços", "natureza": "C"},
            "40101": {"nome": "Custo das Mercadorias Vendidas (CMV)", "natureza": "D"},
            "40102": {"nome": "Despesas com Aluguel", "natureza": "D"}, "40103": {"nome": "Despesas com Salários", "natureza": "D"}
        }
        salvar_dados_empresa(id_empresa, plano_de_contas_inicial, NOME_ARQUIVO_CONTAS)
        return plano_de_contas_inicial
    return contas

def carregar_historico_empresa(id_empresa):
    return carregar_dados_empresa(id_empresa, NOME_ARQUIVO_HISTORICO)

def salvar_historico_empresa(id_empresa, historico):
    salvar_dados_empresa(id_empresa, historico, NOME_ARQUIVO_HISTORICO)

def registrar_no_historico(id_empresa, usuario, acao, lancamento_id, dados_anteriores=None, dados_novos=None):
    historico = carregar_historico_empresa(id_empresa)
    entrada_log = {
        "log_id": len(historico) + 1, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "usuario": usuario, "acao": acao, "lancamento_id": lancamento_id,
        "dados_anteriores": dados_anteriores, "dados_novos": dados_novos
    }
    historico.append(entrada_log)
    salvar_historico_empresa(id_empresa, historico)

def verificar_sessao_empresa():
    if 'usuario' not in session or 'id_empresa' not in session:
        flash('Sessão inválida ou expirada. Por favor, faça login novamente.', 'warning')
        return False
    return True

def _rodape_pdf_simples(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(doc.width / 2.0 + doc.leftMargin, 1*cm, f"Página {doc.page}")
    canvas.restoreState()

def _cabecalho_relatorio_pdf(story, styles, nome_empresa, titulo_relatorio):
    style_titulo_empresa = ParagraphStyle('TituloEmpresa', parent=styles['h1'], alignment=TA_CENTER, fontSize=16, spaceAfter=0.1*cm, leading=20)
    style_titulo_relatorio = ParagraphStyle('TituloRelatorio', parent=styles['h2'], alignment=TA_CENTER, fontSize=14, spaceBefore=0, spaceAfter=0.4*cm, leading=18)
    style_info_geral = ParagraphStyle('InfoGeral', parent=styles['Normal'], alignment=TA_LEFT, fontSize=9, spaceBefore=0.1*cm, spaceAfter=0.1*cm, leading=12)
    story.append(Paragraph(nome_empresa, style_titulo_empresa))
    story.append(Paragraph(titulo_relatorio, style_titulo_relatorio))
    story.append(Paragraph(f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} por: {session.get('usuario', 'N/A')}", style_info_geral))
    story.append(Spacer(1, 0.8*cm))

# --- ROTAS DA APLICAÇÃO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario_form = request.form['usuario']
        senha_form = request.form['senha']
        empresas = carregar_empresas()
        utilizador_encontrado_empresa_id = None
        for id_emp, dados_emp in empresas.items():
            usuarios_empresa = carregar_usuarios_empresa(id_emp)
            if usuario_form in usuarios_empresa and usuarios_empresa[usuario_form] == senha_form:
                utilizador_encontrado_empresa_id = id_emp
                break
        if utilizador_encontrado_empresa_id:
            session['usuario'] = usuario_form
            session['id_empresa'] = utilizador_encontrado_empresa_id
            session['nome_empresa'] = empresas[utilizador_encontrado_empresa_id]['nome']
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Utilizador, senha ou empresa inválidos.', 'danger')
    return render_template('login.html')

@app.route('/registrar_empresa', methods=['GET', 'POST'])
def registrar_empresa():
    if request.method == 'POST':
        nome_empresa = request.form.get('nome_empresa', '').strip()
        admin_usuario = request.form.get('admin_usuario', '').strip()
        admin_senha = request.form.get('admin_senha', '')
        if not nome_empresa or not admin_usuario or not admin_senha:
            flash('Todos os campos são obrigatórios.', 'warning')
            return render_template('registrar_empresa.html', nome_empresa=nome_empresa, admin_usuario=admin_usuario)
        empresas = carregar_empresas()
        if any(emp['nome'].lower() == nome_empresa.lower() for emp in empresas.values()):
            flash('Já existe uma empresa registada com este nome.', 'warning')
            return render_template('registrar_empresa.html', nome_empresa=nome_empresa, admin_usuario=admin_usuario)
        for id_emp_existente in empresas:
            usuarios_existentes = carregar_usuarios_empresa(id_emp_existente)
            if admin_usuario in usuarios_existentes:
                flash(f'O nome de utilizador "{admin_usuario}" já está em uso. Escolha outro.', 'warning')
                return render_template('registrar_empresa.html', nome_empresa=nome_empresa, admin_usuario=admin_usuario)
        id_nova_empresa = str(uuid.uuid4())
        caminho_pasta_nova_empresa = os.path.join(DATA_DIR, id_nova_empresa)
        os.makedirs(caminho_pasta_nova_empresa, exist_ok=True)
        usuarios_nova_empresa = {admin_usuario: admin_senha}
        salvar_usuarios_empresa(id_nova_empresa, usuarios_nova_empresa)
        salvar_lancamentos_empresa(id_nova_empresa, [])
        carregar_contas_empresa(id_nova_empresa)
        salvar_historico_empresa(id_nova_empresa, [])
        empresas[id_nova_empresa] = {"nome": nome_empresa, "admin_user": admin_usuario}
        salvar_empresas(empresas)
        flash(f'Empresa "{nome_empresa}" e utilizador admin "{admin_usuario}" registados com sucesso! Faça o login.', 'success')
        return redirect(url_for('login'))
    return render_template('registrar_empresa.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('id_empresa', None)
    session.pop('nome_empresa', None)
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    contas = carregar_contas_empresa(id_empresa_atual)
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    empresas = carregar_empresas()
    admin_da_empresa_atual = empresas.get(id_empresa_atual, {}).get('admin_user')

    if request.method == 'POST':
        conta_debito_cod = request.form.get('conta_debito')
        conta_credito_cod = request.form.get('conta_credito')
        valor_str = request.form.get('valor')
        historico = request.form.get('historico', '').strip()
        
        if not all([conta_debito_cod, conta_credito_cod, valor_str, historico]):
            flash('Todos os campos da transação são obrigatórios.', 'warning')
        elif conta_debito_cod == conta_credito_cod:
            flash('A conta de débito e a conta de crédito não podem ser a mesma.', 'warning')
        else:
            try:
                valor = float(valor_str)
                if valor <= 0:
                    flash('O valor da transação deve ser positivo.', 'warning')
                else:
                    data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    transacao_id = str(uuid.uuid4())
                    
                    conta_debito_obj = contas.get(conta_debito_cod, {})
                    nome_conta_debito = conta_debito_obj.get('nome', 'Conta Desconhecida') if isinstance(conta_debito_obj, dict) else conta_debito_obj
                    conta_credito_obj = contas.get(conta_credito_cod, {})
                    nome_conta_credito = conta_credito_obj.get('nome', 'Conta Desconhecida') if isinstance(conta_credito_obj, dict) else conta_credito_obj

                    lancamento_debito = {
                        'id': str(uuid.uuid4()), 'transacao_id': transacao_id, 'data': data_atual,
                        'conta_cod': conta_debito_cod, 'conta_nome': nome_conta_debito,
                        'tipo': 'D', 'valor': valor, 'historico': historico, 'usuario': session.get('usuario')
                    }
                    lancamento_credito = {
                        'id': str(uuid.uuid4()), 'transacao_id': transacao_id, 'data': data_atual,
                        'conta_cod': conta_credito_cod, 'conta_nome': nome_conta_credito,
                        'tipo': 'C', 'valor': valor, 'historico': historico, 'usuario': session.get('usuario')
                    }

                    lancamentos.append(lancamento_debito)
                    lancamentos.append(lancamento_credito)
                    salvar_lancamentos_empresa(id_empresa_atual, lancamentos)
                    
                    registrar_no_historico(id_empresa=id_empresa_atual, usuario=session.get('usuario'), 
                                           acao='CRIACAO_TRANSACAO', lancamento_id=transacao_id, 
                                           dados_novos={"debito": lancamento_debito, "credito": lancamento_credito})
                    
                    flash('Transação registrada com sucesso!', 'success')
                    return redirect(url_for('dashboard'))

            except ValueError:
                flash('Valor inválido inserido.', 'danger')
        
    total_d = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
    total_c = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
    dados_despesas_pizza = preparar_dados_despesas_pizza(lancamentos)
    return render_template('dashboard.html', 
                           usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'), 
                           contas=contas, total_d=total_d, total_c=total_c,
                           admin_da_empresa=admin_da_empresa_atual, dados_despesas_pizza=dados_despesas_pizza)

def preparar_dados_despesas_pizza(lancamentos):
    despesas_por_conta = {}
    for lanc in lancamentos:
        if lanc.get('tipo') == 'D':
            try:
                valor = float(lanc.get('valor', 0))
                nome_conta = lanc.get('conta_nome', 'Desconhecida') 
                despesas_por_conta[nome_conta] = despesas_por_conta.get(nome_conta, 0) + valor
            except ValueError:
                continue
    return {'labels': list(despesas_por_conta.keys()), 'data': list(despesas_por_conta.values())}

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if not verificar_sessao_empresa(): return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    empresas = carregar_empresas()
    dados_empresa_atual = empresas.get(id_empresa_atual)
    if not dados_empresa_atual or session.get('usuario') != dados_empresa_atual.get('admin_user'):
        flash('Apenas o administrador da empresa pode registar novos utilizadores.', 'danger')
        return redirect(url_for('dashboard'))
    usuario_logado_admin = session.get('usuario')
    if request.method == 'POST':
        novo_usuario_form = request.form.get('usuario_novo', '').strip()
        nova_senha_form = request.form.get('senha_nova', '')
        if not novo_usuario_form or not nova_senha_form:
            flash('Nome de utilizador e senha não podem estar vazios.', 'warning')
        else:
            usuarios_empresa = carregar_usuarios_empresa(id_empresa_atual)
            if novo_usuario_form in usuarios_empresa:
                flash(f'O nome de utilizador "{novo_usuario_form}" já existe nesta empresa.', 'warning')
            else:
                usuarios_empresa[novo_usuario_form] = nova_senha_form 
                salvar_usuarios_empresa(id_empresa_atual, usuarios_empresa)
                flash(f'Utilizador "{novo_usuario_form}" registado com sucesso para a empresa!', 'success')
    return render_template('cadastro.html', usuario=usuario_logado_admin, nome_empresa=session.get('nome_empresa'))

@app.route('/diario')
def diario():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x.get('data', '1900-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S'))
    return render_template('diario.html', lancamentos=lancamentos_ordenados, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

# --- ROTAS DE EDIÇÃO/EXCLUSÃO CORRIGIDAS (USANDO ID) ---
@app.route('/diario/editar/<lancamento_id>', methods=['GET', 'POST'])
def editar_lancamento(lancamento_id):
    if not verificar_sessao_empresa(): return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)
    
    lancamento_para_editar = next((l for l in lancamentos if str(l.get('id')) == str(lancamento_id)), None)
    
    if lancamento_para_editar is None:
        flash('Lançamento não encontrado.', 'danger')
        return redirect(url_for('diario'))

    lancamento_original = json.loads(json.dumps(lancamento_para_editar))

    if request.method == 'POST':
        nova_data_str = request.form.get('data_lancamento')
        nova_conta_cod = request.form.get('conta')
        novo_tipo = request.form.get('tipo')
        novo_valor_str = request.form.get('valor')
        novo_historico = request.form.get('historico', '').strip()
        if not all([nova_data_str, nova_conta_cod, novo_tipo, novo_valor_str, novo_historico]):
            flash('Todos os campos são obrigatórios.', 'warning')
        else:
            try:
                novo_valor = float(novo_valor_str)
                if novo_valor <= 0: flash('O valor do lançamento deve ser positivo.', 'warning')
                else:
                    lancamento_idx = next(i for i, l in enumerate(lancamentos) if str(l.get('id')) == str(lancamento_id))
                    data_lanc_original_dt = datetime.strptime(lancamento_original['data'], '%Y-%m-%d %H:%M:%S')
                    nova_data_dt = datetime.strptime(nova_data_str, '%Y-%m-%d')
                    data_final_para_salvar = data_lanc_original_dt.replace(year=nova_data_dt.year, month=nova_data_dt.month, day=nova_data_dt.day).strftime('%Y-%m-%d %H:%M:%S')
                    conta_obj_edit = contas.get(nova_conta_cod)
                    nome_conta_final = conta_obj_edit if isinstance(conta_obj_edit, str) else (conta_obj_edit.get('nome') if isinstance(conta_obj_edit, dict) else "Conta Desconhecida")
                    
                    lancamentos[lancamento_idx]['data'] = data_final_para_salvar
                    lancamentos[lancamento_idx]['conta_cod'] = nova_conta_cod
                    lancamentos[lancamento_idx]['conta_nome'] = nome_conta_final
                    lancamentos[lancamento_idx]['tipo'] = novo_tipo
                    lancamentos[lancamento_idx]['valor'] = novo_valor
                    lancamentos[lancamento_idx]['historico'] = novo_historico
                    salvar_lancamentos_empresa(id_empresa_atual, lancamentos)
                    
                    registrar_no_historico(id_empresa=id_empresa_atual, usuario=session.get('usuario'), acao='EDICAO', lancamento_id=lancamento_id, dados_anteriores=lancamento_original, dados_novos=lancamentos[lancamento_idx])
                    flash('Lançamento atualizado com sucesso!', 'success')
                    return redirect(url_for('diario'))
            except ValueError: flash('Valor ou formato de data inválido.', 'danger')
        
        lanc_form = {'id': lancamento_id, 'data': nova_data_str, 'conta_cod': nova_conta_cod, 'tipo': novo_tipo, 'valor': novo_valor_str, 'historico': novo_historico}
        return render_template('editar_lancamento.html', lancamento=lanc_form, lancamento_original_data_str=nova_data_str, contas=contas, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

    data_para_input = datetime.strptime(lancamento_original['data'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    return render_template('editar_lancamento.html', lancamento=lancamento_original, lancamento_original_data_str=data_para_input, contas=contas, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

@app.route('/diario/excluir/<lancamento_id>', methods=['POST'])
def excluir_lancamento(lancamento_id):
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    
    lancamento_para_excluir = None
    for i, l in enumerate(lancamentos):
        if str(l.get('id')) == str(lancamento_id):
            lancamento_para_excluir = lancamentos.pop(i)
            break
    if lancamento_para_excluir:
        salvar_lancamentos_empresa(id_empresa_atual, lancamentos)
        registrar_no_historico(id_empresa=id_empresa_atual, usuario=session.get('usuario'), acao='EXCLUSAO', lancamento_id=lancamento_id, dados_anteriores=lancamento_para_excluir)
        flash('Lançamento excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir: Lançamento não encontrado.', 'danger')
    return redirect(url_for('diario'))

# --- ROTA DE HISTÓRICO ---
@app.route('/historico')
def historico_alteracoes():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    historico_completo = carregar_historico_empresa(id_empresa_atual)
    historico_ordenado = sorted(historico_completo, key=lambda x: x.get('timestamp', ''), reverse=True)
    return render_template('historico.html', historico=historico_ordenado, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

@app.route('/diario/exportar_csv')
def diario_exportar_csv():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x.get('data', '1900-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S'))
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Data', 'Conta Código', 'Nome da Conta', 'Histórico', 'Débito', 'Crédito'])
    for lanc in lancamentos_ordenados:
        debito = lanc.get('valor') if lanc.get('tipo') == 'D' else ''
        credito = lanc.get('valor') if lanc.get('tipo') == 'C' else ''
        cw.writerow([
            lanc.get('data'), lanc.get('conta_cod'), lanc.get('conta_nome'),
            lanc.get('historico'), debito, credito
        ])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=livro_diario_{session.get('nome_empresa', 'empresa')}_{datetime.now().strftime('%Y%m%d')}.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8-sig"
    return output

@app.route('/diario/exportar_pdf')
def diario_exportar_pdf():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    nome_empresa_atual = session.get('nome_empresa', 'Empresa Desconhecida')
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x.get('data', '1900-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S'))
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []
    styles = getSampleStyleSheet()
    _cabecalho_relatorio_pdf(story, styles, nome_empresa_atual, "Livro Diário")
    style_texto_tabela_normal = ParagraphStyle('TextoTabelaNormal', parent=styles['Normal'], fontSize=8, leading=10)
    style_texto_tabela_direita = ParagraphStyle('TextoTabelaDireita', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, leading=10)
    style_texto_tabela_historico = ParagraphStyle('TextoTabelaHistorico', parent=styles['Normal'], fontSize=8, leading=10)
    dados_tabela = [
        [Paragraph("<b>Data</b>", style_texto_tabela_normal), 
         Paragraph("<b>Conta (Cód.)</b>", style_texto_tabela_normal), 
         Paragraph("<b>Histórico</b>", style_texto_tabela_normal), 
         Paragraph("<b>Débito (R$)</b>", style_texto_tabela_direita), 
         Paragraph("<b>Crédito (R$)</b>", style_texto_tabela_direita)]
    ]
    total_debitos_pdf = 0.0
    total_creditos_pdf = 0.0
    for lanc in lancamentos_ordenados:
        valor_lanc = float(lanc.get('valor', 0.0))
        debito_str = f"{valor_lanc:.2f}" if lanc.get('tipo') == 'D' else ''
        credito_str = f"{valor_lanc:.2f}" if lanc.get('tipo') == 'C' else ''
        if lanc.get('tipo') == 'D': total_debitos_pdf += valor_lanc
        elif lanc.get('tipo') == 'C': total_creditos_pdf += valor_lanc
        data_formatada = datetime.strptime(lanc.get('data', '1900-01-01 00:00:00').split(' ')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
        historico_paragrafo = Paragraph(lanc.get('historico', ''), style_texto_tabela_historico)
        dados_tabela.append([
            Paragraph(data_formatada, style_texto_tabela_normal),
            Paragraph(f"{lanc.get('conta_nome', '')} ({lanc.get('conta_cod', '')})", style_texto_tabela_normal),
            historico_paragrafo, Paragraph(debito_str, style_texto_tabela_direita), Paragraph(credito_str, style_texto_tabela_direita)
        ])
    if len(dados_tabela) > 1:
        dados_tabela.append([
            Paragraph("<b>TOTAIS</b>", style_texto_tabela_direita), '', '',
            Paragraph(f"<b>{total_debitos_pdf:.2f}</b>", style_texto_tabela_direita),
            Paragraph(f"<b>{total_creditos_pdf:.2f}</b>", style_texto_tabela_direita)
        ])
        col_widths = [1.8*cm, 4.5*cm, 6.7*cm, 2.5*cm, 2.5*cm] 
        tabela = Table(dados_tabela, colWidths=col_widths, repeatRows=1)
        estilo_tabela = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('ALIGN', (3,0), (4,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,0), 8), 
            ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,1), (-1,-1), 2),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('ALIGN', (0,-1), (2,-1), 'RIGHT'), ('SPAN', (0,-1), (2,-1)),
        ])
        for i in range(1, len(dados_tabela) -1): 
            if i % 2 == 0: estilo_tabela.add('BACKGROUND', (0,i), (-1,i), colors.HexColor("#DCE6F1"))
        tabela.setStyle(estilo_tabela)
        story.append(tabela)
    else:
        story.append(Paragraph("Nenhum lançamento encontrado para o período.", styles['Normal']))
    doc.build(story, onFirstPage=_rodape_pdf_simples, onLaterPages=_rodape_pdf_simples)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=livro_diario_{id_empresa_atual}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    return response

@app.route('/razao')
def razao():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)
    razao_por_conta = {}
    for cod_conta, nome_conta_obj_ou_str in contas.items():
        nome_conta_str = nome_conta_obj_ou_str if isinstance(nome_conta_obj_ou_str, str) else nome_conta_obj_ou_str.get('nome', 'Desconhecida')
        razao_por_conta[cod_conta] = {
            'nome': nome_conta_str, 'lancamentos': [],
            'saldo_devedor': 0.0, 'saldo_credor': 0.0, 'saldo_final': 0.0
        }
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x.get('data', '1900-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S'))
    for lanc in lancamentos_ordenados:
        cod_conta_lanc = lanc.get('conta_cod')
        if cod_conta_lanc in razao_por_conta:
            try:
                valor = float(lanc.get('valor', 0))
            except ValueError: valor = 0.0
            razao_por_conta[cod_conta_lanc]['lancamentos'].append(lanc)
            if lanc.get('tipo') == 'D': razao_por_conta[cod_conta_lanc]['saldo_devedor'] += valor
            elif lanc.get('tipo') == 'C': razao_por_conta[cod_conta_lanc]['saldo_credor'] += valor
    for cod_conta in razao_por_conta:
        razao_por_conta[cod_conta]['saldo_final'] = razao_por_conta[cod_conta]['saldo_devedor'] - razao_por_conta[cod_conta]['saldo_credor']
    return render_template('razao.html', razao_contas=razao_por_conta, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

@app.route('/razao/exportar_pdf')
def razao_exportar_pdf():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    nome_empresa_atual = session.get('nome_empresa', 'Empresa Desconhecida')
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)
    razao_por_conta_dados = {} 
    for cod_conta, nome_conta_obj_ou_str in contas.items():
        nome_conta_str = nome_conta_obj_ou_str if isinstance(nome_conta_obj_ou_str, str) else nome_conta_obj_ou_str.get('nome', 'Desconhecida')
        razao_por_conta_dados[cod_conta] = {
            'nome': nome_conta_str, 'lancamentos': [],
            'saldo_devedor': 0.0, 'saldo_credor': 0.0, 'saldo_final': 0.0
        }
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x.get('data', '1900-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S'))
    for lanc in lancamentos_ordenados:
        cod_conta_lanc = lanc.get('conta_cod')
        if cod_conta_lanc in razao_por_conta_dados:
            try:
                valor = float(lanc.get('valor', 0))
            except ValueError: valor = 0.0
            razao_por_conta_dados[cod_conta_lanc]['lancamentos'].append(lanc)
            if lanc.get('tipo') == 'D': razao_por_conta_dados[cod_conta_lanc]['saldo_devedor'] += valor
            elif lanc.get('tipo') == 'C': razao_por_conta_dados[cod_conta_lanc]['saldo_credor'] += valor
    for cod_conta_calc_final in razao_por_conta_dados:
        razao_por_conta_dados[cod_conta_calc_final]['saldo_final'] = razao_por_conta_dados[cod_conta_calc_final]['saldo_devedor'] - razao_por_conta_dados[cod_conta_calc_final]['saldo_credor']

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []
    styles = getSampleStyleSheet()
    _cabecalho_relatorio_pdf(story, styles, nome_empresa_atual, "Livro Razão")

    style_conta_titulo = ParagraphStyle('ContaTitulo', parent=styles['h3'], fontSize=12, spaceBefore=0.8*cm, spaceAfter=0.3*cm, alignment=TA_LEFT, leading=14)
    style_texto_tabela_normal = ParagraphStyle('TextoTabelaNormal', parent=styles['Normal'], fontSize=8, leading=10)
    style_texto_tabela_direita = ParagraphStyle('TextoTabelaDireita', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, leading=10)
    style_texto_tabela_historico = ParagraphStyle('TextoTabelaHistorico', parent=styles['Normal'], fontSize=8, leading=10)
    style_rodape_conta = ParagraphStyle('RodapeConta', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT, spaceBefore=0.2*cm, leading=12)

    alguma_conta_com_lancamento = False
    for conta_cod_pdf in sorted(razao_por_conta_dados.keys()):
        dados_conta_pdf = razao_por_conta_dados[conta_cod_pdf]
        if not dados_conta_pdf.get('lancamentos'):
            continue
        alguma_conta_com_lancamento = True
        story.append(Paragraph(f"Conta: {dados_conta_pdf['nome']} ({conta_cod_pdf})", style_conta_titulo))
        dados_tabela_conta = [[
            Paragraph("<b>Data</b>", style_texto_tabela_normal), 
            Paragraph("<b>Histórico</b>", style_texto_tabela_normal), 
            Paragraph("<b>Débito (R$)</b>", style_texto_tabela_direita), 
            Paragraph("<b>Crédito (R$)</b>", style_texto_tabela_direita),
            Paragraph("<b>Saldo (R$)</b>", style_texto_tabela_direita)
        ]]
        saldo_corrente_pdf = 0.0
        for lanc_pdf in dados_conta_pdf['lancamentos']: 
            valor_lanc_pdf = float(lanc_pdf.get('valor', 0.0))
            debito_str = f"{valor_lanc_pdf:.2f}" if lanc_pdf.get('tipo') == 'D' else ''
            credito_str = f"{valor_lanc_pdf:.2f}" if lanc_pdf.get('tipo') == 'C' else ''
            if lanc_pdf.get('tipo') == 'D':
                saldo_corrente_pdf += valor_lanc_pdf
            elif lanc_pdf.get('tipo') == 'C':
                saldo_corrente_pdf -= valor_lanc_pdf 
            data_formatada = datetime.strptime(lanc_pdf.get('data', '1900-01-01 00:00:00').split(' ')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
            historico_paragrafo = Paragraph(lanc_pdf.get('historico', ''), style_texto_tabela_historico)
            dados_tabela_conta.append([
                Paragraph(data_formatada, style_texto_tabela_normal),
                historico_paragrafo,
                Paragraph(debito_str, style_texto_tabela_direita),
                Paragraph(credito_str, style_texto_tabela_direita),
                Paragraph(f"{saldo_corrente_pdf:.2f}", style_texto_tabela_direita)
            ])
        col_widths_razao = [1.8*cm, 7.2*cm, 2.5*cm, 2.5*cm, 2.5*cm]
        tabela_conta = Table(dados_tabela_conta, colWidths=col_widths_razao, repeatRows=1)
        estilo_tabela_conta = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('ALIGN', (2,0), (4,-1), 'RIGHT'), 
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ])
        for i in range(1, len(dados_tabela_conta)): 
            if i % 2 == 0: estilo_tabela_conta.add('BACKGROUND', (0,i), (-1,i), colors.HexColor("#DCE6F1"))
        tabela_conta.setStyle(estilo_tabela_conta)
        story.append(tabela_conta)
        saldo_final_conta_val = dados_conta_pdf['saldo_final']
        natureza_conta_atual = contas.get(conta_cod_pdf, {}).get('natureza', 'D') 
        if natureza_conta_atual == 'D':
            saldo_final_str = f"Devedor {saldo_final_conta_val:.2f}" if saldo_final_conta_val >= 0 else f"Credor {abs(saldo_final_conta_val):.2f} (Natureza Invertida)"
        else:
             saldo_final_str = f"Credor {abs(saldo_final_conta_val):.2f}" if saldo_final_conta_val <= 0 else f"Devedor {saldo_final_conta_val:.2f} (Natureza Invertida)"
        story.append(Paragraph(f"<b>Saldo Final da Conta: R$ {saldo_final_str}</b>", style_rodape_conta))
        story.append(PageBreak()) 
    if not alguma_conta_com_lancamento:
        story.append(Paragraph("Nenhum lançamento encontrado para as contas neste período.", styles['Normal']))
    doc.build(story, onFirstPage=_rodape_pdf_simples, onLaterPages=_rodape_pdf_simples)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=livro_razao_{id_empresa_atual}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    return response

@app.route('/balancete')
def balancete():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)
    saldos_contas_dict = {}
    for cod, nome_conta_obj_ou_str in contas.items():
        nome_conta_str = nome_conta_obj_ou_str if isinstance(nome_conta_obj_ou_str, str) else nome_conta_obj_ou_str.get('nome', 'Desconhecida')
        saldos_contas_dict[cod] = {'nome': nome_conta_str, 'debito': 0.0, 'credito': 0.0, 'saldo_devedor': 0.0, 'saldo_credor': 0.0, 'natureza': nome_conta_obj_ou_str.get('natureza', 'D') if isinstance(nome_conta_obj_ou_str, dict) else 'D'}
    for lanc in lancamentos:
        cod_conta = lanc.get('conta_cod')
        if cod_conta in saldos_contas_dict:
            try:
                valor = float(lanc.get('valor', 0))
            except ValueError: valor = 0.0
            if lanc.get('tipo') == 'D': saldos_contas_dict[cod_conta]['debito'] += valor
            elif lanc.get('tipo') == 'C': saldos_contas_dict[cod_conta]['credito'] += valor
    total_saldo_devedor_geral = 0.0
    total_saldo_credor_geral = 0.0
    for cod, dados_conta in saldos_contas_dict.items():
        saldo_calculado = dados_conta['debito'] - dados_conta['credito']
        natureza_conta = dados_conta.get('natureza', 'D') 
        dados_conta['saldo_devedor'] = 0.0
        dados_conta['saldo_credor'] = 0.0
        if natureza_conta == 'D':
            if saldo_calculado >= 0: dados_conta['saldo_devedor'] = saldo_calculado
            else: dados_conta['saldo_credor'] = abs(saldo_calculado)
        elif natureza_conta == 'C':
            if saldo_calculado <= 0: dados_conta['saldo_credor'] = abs(saldo_calculado)
            else: dados_conta['saldo_devedor'] = saldo_calculado
        total_saldo_devedor_geral += dados_conta['saldo_devedor']
        total_saldo_credor_geral += dados_conta['saldo_credor']
    return render_template('balancete.html', saldos_contas=saldos_contas_dict, 
                           total_debitos=total_saldo_devedor_geral, 
                           total_creditos=total_saldo_credor_geral, 
                           usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

@app.route('/balancete/exportar_pdf')
def balancete_exportar_pdf():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    nome_empresa_atual = session.get('nome_empresa', 'Empresa Desconhecida')
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)
    saldos_contas_dict = {}
    for cod, nome_conta_obj_ou_str in contas.items():
        nome_conta_str = nome_conta_obj_ou_str if isinstance(nome_conta_obj_ou_str, str) else nome_conta_obj_ou_str.get('nome', 'Desconhecida')
        saldos_contas_dict[cod] = {'nome': nome_conta_str, 'debito': 0.0, 'credito': 0.0, 'saldo_devedor': 0.0, 'saldo_credor': 0.0, 'natureza': nome_conta_obj_ou_str.get('natureza', 'D') if isinstance(nome_conta_obj_ou_str, dict) else 'D'}
    for lanc in lancamentos:
        cod_conta = lanc.get('conta_cod')
        if cod_conta in saldos_contas_dict:
            try:
                valor = float(lanc.get('valor', 0))
            except ValueError: valor = 0.0
            if lanc.get('tipo') == 'D': saldos_contas_dict[cod_conta]['debito'] += valor
            elif lanc.get('tipo') == 'C': saldos_contas_dict[cod_conta]['credito'] += valor
    total_saldo_devedor_geral_pdf = 0.0
    total_saldo_credor_geral_pdf = 0.0
    contas_para_pdf = []
    for cod_conta_ordenada in sorted(saldos_contas_dict.keys()):
        dados_conta = saldos_contas_dict[cod_conta_ordenada]
        saldo_calculado = dados_conta['debito'] - dados_conta['credito']
        natureza_conta = dados_conta.get('natureza', 'D')
        dados_conta['saldo_devedor'] = 0.0
        dados_conta['saldo_credor'] = 0.0
        if natureza_conta == 'D':
            if saldo_calculado >= 0: dados_conta['saldo_devedor'] = saldo_calculado
            else: dados_conta['saldo_credor'] = abs(saldo_calculado)
        elif natureza_conta == 'C':
            if saldo_calculado <= 0: dados_conta['saldo_credor'] = abs(saldo_calculado)
            else: dados_conta['saldo_devedor'] = saldo_calculado
        total_saldo_devedor_geral_pdf += dados_conta['saldo_devedor']
        total_saldo_credor_geral_pdf += dados_conta['saldo_credor']
        if dados_conta['debito'] != 0 or dados_conta['credito'] != 0 or dados_conta['saldo_devedor'] != 0 or dados_conta['saldo_credor'] != 0:
            contas_para_pdf.append({'codigo': cod_conta_ordenada, **dados_conta})

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []
    styles = getSampleStyleSheet()
    _cabecalho_relatorio_pdf(story, styles, nome_empresa_atual, "Balancete de Verificação")

    style_texto_tabela_normal = ParagraphStyle('TextoTabelaNormal', parent=styles['Normal'], fontSize=8, leading=10)
    style_texto_tabela_direita = ParagraphStyle('TextoTabelaDireita', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, leading=10)

    dados_tabela_pdf_balancete = [[
        Paragraph("<b>Conta (Cód.)</b>", style_texto_tabela_normal), 
        Paragraph("<b>Saldo Devedor (R$)</b>", style_texto_tabela_direita),
        Paragraph("<b>Saldo Credor (R$)</b>", style_texto_tabela_direita)
    ]]
    total_geral_sd_pdf = 0.0 
    total_geral_sc_pdf = 0.0
    for dados_conta_item_pdf in contas_para_pdf:
        sd = dados_conta_item_pdf['saldo_devedor']
        sc = dados_conta_item_pdf['saldo_credor']
        if sd > 0 or sc > 0 :
            dados_tabela_pdf_balancete.append([
                Paragraph(f"{dados_conta_item_pdf['nome']} ({dados_conta_item_pdf['codigo']})", style_texto_tabela_normal),
                Paragraph(f"{sd:.2f}" if sd > 0 else "0.00", style_texto_tabela_direita),
                Paragraph(f"{sc:.2f}" if sc > 0 else "0.00", style_texto_tabela_direita)
            ])
            total_geral_sd_pdf += sd
            total_geral_sc_pdf += sc
    if len(contas_para_pdf) > 0:
        dados_tabela_pdf_balancete.append([
            Paragraph("<b>TOTAIS GERAIS</b>", style_texto_tabela_normal), 
            Paragraph(f"<b>{total_geral_sd_pdf:.2f}</b>", style_texto_tabela_direita),
            Paragraph(f"<b>{total_geral_sc_pdf:.2f}</b>", style_texto_tabela_direita)
        ])
        col_widths_balancete = [10*cm, 4*cm, 4*cm] 
        tabela = Table(dados_tabela_pdf_balancete, colWidths=col_widths_balancete, repeatRows=1)
        estilo_tabela = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#333A40")), 
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (0,-1), 'LEFT'), 
            ('ALIGN', (1,0), (2,-1), 'RIGHT'), 
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.darkgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey), 
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ])
        for i in range(1, len(dados_tabela_pdf_balancete) -1): 
            if i % 2 == 0: estilo_tabela.add('BACKGROUND', (0,i), (-1,i), colors.HexColor("#EFEFEF"))
        tabela.setStyle(estilo_tabela)
        story.append(tabela)
    else:
        story.append(Paragraph("Nenhuma conta com movimento ou saldo para exibir no balancete.", styles['Normal']))

    doc.build(story, onFirstPage=_rodape_pdf_simples, onLaterPages=_rodape_pdf_simples)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=balancete_{id_empresa_atual}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    return response

@app.route('/grafico_data', methods=['GET', 'POST'])
def grafico_data():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos_todos = carregar_lancamentos_empresa(id_empresa_atual)
    dados_grafico = {'labels': [], 'debitos': [], 'creditos': [], 'saldos': []}
    data_inicio_selecionada = request.form.get('data_inicio', '') if request.method == 'POST' else ''
    data_fim_selecionada = request.form.get('data_fim', '') if request.method == 'POST' else ''
    if request.method == 'POST':
        if data_inicio_selecionada and data_fim_selecionada:
            try:
                data_inicio_obj = datetime.strptime(data_inicio_selecionada, '%Y-%m-%d').date()
                data_fim_obj = datetime.strptime(data_fim_selecionada, '%Y-%m-%d').date()
                if data_inicio_obj > data_fim_obj:
                    flash('A data de início não pode ser posterior à data de fim.', 'warning')
                else:
                    lancamentos_filtrados_periodo = []
                    for lanc in lancamentos_todos:
                        data_lanc_str_completa = lanc.get('data', '')
                        if data_lanc_str_completa:
                            try:
                                data_lanc_obj = datetime.strptime(data_lanc_str_completa, '%Y-%m-%d %H:%M:%S').date()
                                if data_inicio_obj <= data_lanc_obj <= data_fim_obj:
                                    lancamentos_filtrados_periodo.append(lanc)
                            except ValueError:
                                continue
                    dados_por_dia = {}
                    lancamentos_filtrados_periodo.sort(key=lambda x: datetime.strptime(x.get('data', '1900-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S').date())
                    current_date_iter = data_inicio_obj
                    while current_date_iter <= data_fim_obj:
                        dia_str_chave = current_date_iter.strftime('%Y-%m-%d')
                        dados_por_dia[dia_str_chave] = {'debitos': 0, 'creditos': 0}
                        current_date_iter += timedelta(days=1)
                    for lanc in lancamentos_filtrados_periodo:
                        dia_str_chave = datetime.strptime(lanc.get('data', '1900-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        valor_lanc = 0.0
                        try:
                            valor_lanc = float(lanc.get('valor', 0))
                        except ValueError:
                            pass
                        if dia_str_chave in dados_por_dia:
                            if lanc.get('tipo') == 'D':
                                dados_por_dia[dia_str_chave]['debitos'] += valor_lanc
                            elif lanc.get('tipo') == 'C':
                                dados_por_dia[dia_str_chave]['creditos'] += valor_lanc
                    saldo_acumulado_grafico = 0.0
                    dias_ordenados_grafico = sorted(dados_por_dia.keys())
                    for dia_str_grafico in dias_ordenados_grafico:
                        dados_grafico['labels'].append(datetime.strptime(dia_str_grafico, '%Y-%m-%d').strftime('%d/%m'))
                        dados_grafico['debitos'].append(dados_por_dia[dia_str_grafico]['debitos'])
                        dados_grafico['creditos'].append(dados_por_dia[dia_str_grafico]['creditos'])
                        saldo_dia_atual = dados_por_dia[dia_str_grafico]['creditos'] - dados_por_dia[dia_str_grafico]['debitos']
                        saldo_acumulado_grafico += saldo_dia_atual
                        dados_grafico['saldos'].append(round(saldo_acumulado_grafico, 2))
            except ValueError:
                flash('Formato de data inválido. Use o formato AAAA-MM-DD.', 'danger')
        else:
            flash('Por favor, selecione a data de início e a data de fim.', 'warning')
    return render_template('grafico_data.html', 
                           usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'),
                           dados_grafico=dados_grafico,
                           data_inicio=data_inicio_selecionada,
                           data_fim=data_fim_selecionada)

if __name__ == '__main__':
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(ARQUIVO_EMPRESAS):
        salvar_empresas({})
    app.run(debug=True, host='0.0.0.0')