from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import json
from datetime import datetime, timedelta
import os
import uuid
import io
import csv

# Para PDF com ReportLab
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_multi_empresa_muito_forte'

# --- Constantes e Funções Auxiliares (MANTENHA TODAS AS SUAS FUNÇÕES AUXILIARES COMO ESTÃO) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ARQUIVO_EMPRESAS = os.path.join(BASE_DIR, 'empresas.json')

NOME_ARQUIVO_LANCAMENTOS = 'lancamentos.json'
NOME_ARQUIVO_USUARIOS = 'usuarios.json'
NOME_ARQUIVO_CONTAS = 'contas.json'

# (COLE AQUI TODAS AS SUAS FUNÇÕES AUXILIARES: carregar_empresas, salvar_empresas, ...)
# (obter_caminho_arquivo_empresa, carregar_dados_empresa, salvar_dados_empresa, ...)
# (carregar_lancamentos_empresa, salvar_lancamentos_empresa, carregar_usuarios_empresa, ...)
# (salvar_usuarios_empresa, carregar_contas_empresa)
# --- Funções Auxiliares Globais ---
def carregar_empresas():
    if not os.path.exists(ARQUIVO_EMPRESAS):
        return {}
    try:
        with open(ARQUIVO_EMPRESAS, 'r', encoding='utf-8') as f:
            content = f.read()
            return json.loads(content) if content else {}
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def salvar_empresas(empresas):
    with open(ARQUIVO_EMPRESAS, 'w', encoding='utf-8') as f:
        json.dump(empresas, f, indent=4, ensure_ascii=False)

# --- Funções Auxiliares Específicas da Empresa ---
def obter_caminho_arquivo_empresa(id_empresa, nome_arquivo):
    return os.path.join(DATA_DIR, str(id_empresa), nome_arquivo)

def carregar_dados_empresa(id_empresa, nome_arquivo_base):
    arquivo = obter_caminho_arquivo_empresa(id_empresa, nome_arquivo_base)
    if not os.path.exists(arquivo):
        return [] if nome_arquivo_base == NOME_ARQUIVO_LANCAMENTOS else {}
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content: # Ficheiro existe mas está vazio
                return [] if nome_arquivo_base == NOME_ARQUIVO_LANCAMENTOS else {}
            return json.loads(content)
    except json.JSONDecodeError: # Ficheiro existe mas JSON é inválido
        return [] if nome_arquivo_base == NOME_ARQUIVO_LANCAMENTOS else {}
    except FileNotFoundError: # Desnecessário por causa do os.path.exists, mas seguro ter
        return [] if nome_arquivo_base == NOME_ARQUIVO_LANCAMENTOS else {}

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
    if not contas: # Se o plano de contas estiver vazio ou não existir, cria um padrão
        plano_de_contas_inicial = {
            "10101": {"nome": "Caixa Geral", "natureza": "D"},
            "10102": {"nome": "Bancos Conta Movimento", "natureza": "D"},
            "20101": {"nome": "Fornecedores Nacionais", "natureza": "C"},
            "20102": {"nome": "Salários a Pagar", "natureza": "C"},
            "30101": {"nome": "Receita Bruta de Vendas", "natureza": "C"},
            "30102": {"nome": "Receita de Serviços", "natureza": "C"},
            "40101": {"nome": "Custo das Mercadorias Vendidas (CMV)", "natureza": "D"},
            "40102": {"nome": "Despesas com Aluguel", "natureza": "D"},
            "40103": {"nome": "Despesas com Salários", "natureza": "D"}
        }
        salvar_dados_empresa(id_empresa, plano_de_contas_inicial, NOME_ARQUIVO_CONTAS)
        return plano_de_contas_inicial
    return contas

def verificar_sessao_empresa():
    if 'usuario' not in session or 'id_empresa' not in session:
        flash('Sessão inválida ou expirada. Por favor, faça login novamente.', 'warning')
        return False
    return True

# --- ROTAS (Login, Registrar Empresa, Logout, Dashboard, Preparar Pizza, Cadastro Usuário - MANTENHA COMO ESTÃO) ---
# (COLE AQUI AS SUAS ROTAS: login, registrar_empresa, logout, dashboard, preparar_dados_despesas_pizza, cadastro)
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
        admin_senha = request.form.get('admin_senha', '') # Idealmente, hashear esta senha
        if not nome_empresa or not admin_usuario or not admin_senha:
            flash('Todos os campos são obrigatórios.', 'warning')
            return render_template('registrar_empresa.html', nome_empresa=nome_empresa, admin_usuario=admin_usuario)
        empresas = carregar_empresas()
        if any(emp['nome'].lower() == nome_empresa.lower() for emp in empresas.values()):
            flash('Já existe uma empresa registada com este nome.', 'warning')
            return render_template('registrar_empresa.html', nome_empresa=nome_empresa, admin_usuario=admin_usuario)
        for id_emp_existente in empresas: # Verifica se o nome de utilizador admin já existe noutra empresa
            usuarios_existentes = carregar_usuarios_empresa(id_emp_existente)
            if admin_usuario in usuarios_existentes: # Simplificado: não permite mesmo admin_user em empresas diferentes
                flash(f'O nome de utilizador "{admin_usuario}" já está em uso. Escolha outro.', 'warning')
                return render_template('registrar_empresa.html', nome_empresa=nome_empresa, admin_usuario=admin_usuario)

        id_nova_empresa = str(uuid.uuid4())
        caminho_pasta_nova_empresa = os.path.join(DATA_DIR, id_nova_empresa)
        os.makedirs(caminho_pasta_nova_empresa, exist_ok=True)
        usuarios_nova_empresa = {admin_usuario: admin_senha}
        salvar_usuarios_empresa(id_nova_empresa, usuarios_nova_empresa)
        salvar_lancamentos_empresa(id_nova_empresa, [])
        carregar_contas_empresa(id_nova_empresa) # Cria o plano de contas padrão
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
        conta_selecionada_cod = request.form.get('conta')
        tipo = request.form.get('tipo')
        valor_str = request.form.get('valor')
        historico = request.form.get('historico', '').strip()
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not conta_selecionada_cod or not tipo or not valor_str or not historico:
            flash('Todos os campos do lançamento são obrigatórios.', 'warning')
        else:
            try:
                valor = float(valor_str)
                if valor <= 0:
                    flash('O valor do lançamento deve ser positivo.', 'warning')
                else:
                    conta_obj = contas.get(conta_selecionada_cod)
                    nome_conta_final = conta_obj if isinstance(conta_obj, str) else (conta_obj.get('nome') if isinstance(conta_obj, dict) else "Conta Desconhecida")
                    
                    novo_lancamento = {
                        'id': len(lancamentos) + 1, 'data': data_atual,
                        'conta_cod': conta_selecionada_cod, 'conta_nome': nome_conta_final,
                        'tipo': tipo, 'valor': valor, 'historico': historico, 'usuario': session.get('usuario')
                    }
                    lancamentos.append(novo_lancamento)
                    salvar_lancamentos_empresa(id_empresa_atual, lancamentos)
                    flash('Lançamento registrado com sucesso!', 'success')
                    return redirect(url_for('dashboard')) 
            except ValueError:
                flash('Valor inválido inserido.', 'danger')
        
        total_d = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
        total_c = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
        dados_despesas_pizza = preparar_dados_despesas_pizza(lancamentos)
        return render_template('dashboard.html', usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'), contas=contas, total_d=total_d, total_c=total_c, admin_da_empresa=admin_da_empresa_atual, dados_despesas_pizza=dados_despesas_pizza)

    total_d = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
    total_c = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
    dados_despesas_pizza = preparar_dados_despesas_pizza(lancamentos)
    return render_template('dashboard.html', usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'), contas=contas, total_d=total_d, total_c=total_c, admin_da_empresa=admin_da_empresa_atual, dados_despesas_pizza=dados_despesas_pizza)

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
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
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

# --- ROTA DO LIVRO DIÁRIO (HTML) ---
@app.route('/diario')
def diario():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    # Adicionar o ID original do lançamento (índice na lista) para facilitar edição/exclusão
    # Se o seu 'id' já é único e persistente, pode usá-lo diretamente.
    # Se 'id' é apenas len(lancamentos)+1, ele muda se algo for deletado.
    # Para este exemplo, vamos assumir que 'id' é um campo no seu dicionário de lançamento
    # e que ele é suficientemente único para identificar o lançamento.
    lancamentos_com_id_para_template = []
    for i, lanc in enumerate(lancamentos):
        lanc_copy = lanc.copy()
        lanc_copy['idx_original'] = i # Usaremos o índice da lista como ID temporário para edição/exclusão
                                      # Se 'id' já for único e confiável, use lanc_copy['id_lancamento'] = lanc['id']
        lancamentos_com_id_para_template.append(lanc_copy)

    lancamentos_ordenados = sorted(lancamentos_com_id_para_template, key=lambda x: datetime.strptime(x.get('data', '1900-01-01 00:00:00'), '%Y-%m-%d %H:%M:%S'))
    return render_template('diario.html', lancamentos=lancamentos_ordenados, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

# --- NOVAS ROTAS PARA EDITAR E EXCLUIR LANÇAMENTOS ---
@app.route('/diario/editar/<int:lancamento_idx>', methods=['GET', 'POST'])
def editar_lancamento(lancamento_idx):
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)

    lancamento_para_editar = None
    # Encontra o lançamento pelo índice (idx_original que adicionamos)
    # Se você tem um campo 'id' único e confiável nos seus lançamentos, use-o para buscar.
    # Ex: lancamento_para_editar = next((l for l in lancamentos if l.get('id') == lancamento_id_param), None)
    if 0 <= lancamento_idx < len(lancamentos):
        lancamento_para_editar = lancamentos[lancamento_idx]
    
    if lancamento_para_editar is None:
        flash('Lançamento não encontrado.', 'danger')
        return redirect(url_for('diario'))

    if request.method == 'POST':
        # Pegar dados do formulário
        nova_data_str = request.form.get('data_lancamento') # Assume que o input date envia AAAA-MM-DD
        nova_conta_cod = request.form.get('conta')
        novo_tipo = request.form.get('tipo')
        novo_valor_str = request.form.get('valor')
        novo_historico = request.form.get('historico', '').strip()

        # Validações (similares ao do dashboard)
        if not nova_data_str or not nova_conta_cod or not novo_tipo or not novo_valor_str or not novo_historico:
            flash('Todos os campos são obrigatórios.', 'warning')
        else:
            try:
                novo_valor = float(novo_valor_str)
                if novo_valor <= 0:
                    flash('O valor do lançamento deve ser positivo.', 'warning')
                else:
                    # Formatar a data para incluir hora (ou manter apenas data se preferir)
                    # Se o input date só envia AAAA-MM-DD, e o formato original tem hora, precisa decidir.
                    # Vamos manter o formato original se possível, ou atualizar apenas a data.
                    data_lanc_original_dt = datetime.strptime(lancamento_para_editar['data'], '%Y-%m-%d %H:%M:%S')
                    nova_data_dt = datetime.strptime(nova_data_str, '%Y-%m-%d')
                    data_final_para_salvar = data_lanc_original_dt.replace(year=nova_data_dt.year, month=nova_data_dt.month, day=nova_data_dt.day).strftime('%Y-%m-%d %H:%M:%S')


                    # Atualizar o lançamento na lista
                    lancamentos[lancamento_idx]['data'] = data_final_para_salvar
                    lancamentos[lancamento_idx]['conta_cod'] = nova_conta_cod
                    conta_obj_edit = contas.get(nova_conta_cod)
                    lancamentos[lancamento_idx]['conta_nome'] = conta_obj_edit if isinstance(conta_obj_edit, str) else (conta_obj_edit.get('nome') if isinstance(conta_obj_edit, dict) else "Conta Desconhecida")
                    lancamentos[lancamento_idx]['tipo'] = novo_tipo
                    lancamentos[lancamento_idx]['valor'] = novo_valor
                    lancamentos[lancamento_idx]['historico'] = novo_historico
                    # Poderia adicionar um campo 'data_modificacao' e 'usuario_modificacao'
                    
                    salvar_lancamentos_empresa(id_empresa_atual, lancamentos)
                    flash('Lançamento atualizado com sucesso!', 'success')
                    return redirect(url_for('diario'))
            except ValueError:
                flash('Valor ou formato de data inválido.', 'danger')
        
        # Se houve erro, re-renderiza o formulário com os dados que o usuário tentou submeter
        # e o lançamento original para referência (ou os dados atuais do formulário)
        lanc_form = {
            'data': nova_data_str, 'conta_cod': nova_conta_cod, 'tipo': novo_tipo,
            'valor': novo_valor_str, 'historico': novo_historico
        }
        return render_template('editar_lancamento.html', 
                               lancamento=lanc_form, # Usa os dados do form para repopular
                               lancamento_original_data_str=nova_data_str, # Para o input date
                               contas=contas, 
                               usuario=session.get('usuario'), 
                               nome_empresa=session.get('nome_empresa'),
                               lancamento_idx=lancamento_idx)


    # Para método GET, formata a data para o input type="date" (AAAA-MM-DD)
    data_para_input = ''
    if lancamento_para_editar.get('data'):
        try:
            data_para_input = datetime.strptime(lancamento_para_editar['data'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        except ValueError:
            pass # Deixa vazio se o formato for inesperado

    return render_template('editar_lancamento.html', 
                           lancamento=lancamento_para_editar, 
                           lancamento_original_data_str=data_para_input,
                           contas=contas, 
                           usuario=session.get('usuario'), 
                           nome_empresa=session.get('nome_empresa'),
                           lancamento_idx=lancamento_idx)


@app.route('/diario/excluir/<int:lancamento_idx>', methods=['POST']) # Usar POST para exclusão
def excluir_lancamento(lancamento_idx):
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)

    if 0 <= lancamento_idx < len(lancamentos):
        del lancamentos[lancamento_idx]
        salvar_lancamentos_empresa(id_empresa_atual, lancamentos)
        flash('Lançamento excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir: Lançamento não encontrado.', 'danger')
    
    return redirect(url_for('diario'))

# --- ROTAS DE EXPORTAÇÃO (MANTENHA COMO ESTÃO) ---
# (COLE AQUI AS SUAS ROTAS: diario_exportar_csv, diario_exportar_pdf)
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

    style_titulo_empresa = ParagraphStyle('TituloEmpresa', parent=styles['h1'], alignment=TA_CENTER, fontSize=16, spaceAfter=0.1*cm, leading=20)
    style_titulo_relatorio = ParagraphStyle('TituloRelatorio', parent=styles['h2'], alignment=TA_CENTER, fontSize=14, spaceBefore=0, spaceAfter=0.4*cm, leading=18)
    style_info_geral = ParagraphStyle('InfoGeral', parent=styles['Normal'], alignment=TA_LEFT, fontSize=9, spaceBefore=0.1*cm, spaceAfter=0.1*cm, leading=12)
    style_texto_tabela_normal = ParagraphStyle('TextoTabelaNormal', parent=styles['Normal'], fontSize=8, leading=10)
    style_texto_tabela_direita = ParagraphStyle('TextoTabelaDireita', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, leading=10)
    style_texto_tabela_historico = ParagraphStyle('TextoTabelaHistorico', parent=styles['Normal'], fontSize=8, leading=10)


    story.append(Paragraph(nome_empresa_atual, style_titulo_empresa))
    story.append(Paragraph("Livro Diário", style_titulo_relatorio))
    story.append(Paragraph(f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} por: {session.get('usuario', 'N/A')}", style_info_geral))
    story.append(Spacer(1, 0.8*cm))

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
        if lanc.get('tipo') == 'D':
            total_debitos_pdf += valor_lanc
        elif lanc.get('tipo') == 'C':
            total_creditos_pdf += valor_lanc
        data_formatada = datetime.strptime(lanc.get('data', '1900-01-01 00:00:00').split(' ')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
        
        historico_paragrafo = Paragraph(lanc.get('historico', ''), style_texto_tabela_historico)
        
        dados_tabela.append([
            Paragraph(data_formatada, style_texto_tabela_normal),
            Paragraph(f"{lanc.get('conta_nome', '')} ({lanc.get('conta_cod', '')})", style_texto_tabela_normal),
            historico_paragrafo,
            Paragraph(debito_str, style_texto_tabela_direita),
            Paragraph(credito_str, style_texto_tabela_direita)
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
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ALIGN', (3,0), (4,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 8), 
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,1), (-1,-1), 2),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('ALIGN', (0,-1), (2,-1), 'RIGHT'),
            ('SPAN', (0,-1), (2,-1)),
        ])
        for i in range(1, len(dados_tabela) -1): 
            if i % 2 == 0:
                estilo_tabela.add('BACKGROUND', (0,i), (-1,i), colors.HexColor("#DCE6F1"))
        tabela.setStyle(estilo_tabela)
        story.append(tabela)
    else:
        story.append(Paragraph("Nenhum lançamento encontrado para o período.", style_info_geral))
    
    def rodape_simples(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(A4[0]/2.0, 1*cm, f"Página {doc.page}") 
        canvas.restoreState()

    doc.build(story, onFirstPage=rodape_simples, onLaterPages=rodape_simples)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=livro_diario_{id_empresa_atual}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    return response

# --- ROTAS DE RELATÓRIOS RESTANTES (Razão, Balancete, Gráfico por Data - MANTENHA COMO ESTÃO) ---
# (COLE AQUI AS SUAS ROTAS: razao, balancete, grafico_data)
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
            except ValueError:
                valor = 0.0
            razao_por_conta[cod_conta_lanc]['lancamentos'].append(lanc)
            if lanc.get('tipo') == 'D':
                razao_por_conta[cod_conta_lanc]['saldo_devedor'] += valor
            elif lanc.get('tipo') == 'C':
                razao_por_conta[cod_conta_lanc]['saldo_credor'] += valor
    
    for cod_conta in razao_por_conta:
        razao_por_conta[cod_conta]['saldo_final'] = razao_por_conta[cod_conta_lanc]['saldo_devedor'] - razao_por_conta[cod_conta_lanc]['saldo_credor']
    
    return render_template('razao.html', razao_contas=razao_por_conta, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

@app.route('/balancete')
def balancete():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)
    saldos_contas = {}

    for cod, nome_conta_obj_ou_str in contas.items():
        nome_conta_str = nome_conta_obj_ou_str if isinstance(nome_conta_obj_ou_str, str) else nome_conta_obj_ou_str.get('nome', 'Desconhecida')
        saldos_contas[cod] = {'nome': nome_conta_str, 'debito': 0.0, 'credito': 0.0, 'saldo_devedor': 0.0, 'saldo_credor': 0.0}

    for lanc in lancamentos:
        cod_conta = lanc.get('conta_cod')
        if cod_conta in saldos_contas:
            try:
                valor = float(lanc.get('valor', 0))
            except ValueError:
                valor = 0.0
            if lanc.get('tipo') == 'D':
                saldos_contas[cod_conta]['debito'] += valor
            elif lanc.get('tipo') == 'C':
                saldos_contas[cod_conta]['credito'] += valor
    
    total_saldo_devedor_geral = 0.0
    total_saldo_credor_geral = 0.0
    for cod, dados_conta in saldos_contas.items():
        saldo = dados_conta['debito'] - dados_conta['credito']
        if saldo > 0: # Saldo Devedor
            dados_conta['saldo_devedor'] = saldo
            total_saldo_devedor_geral += saldo
        elif saldo < 0: # Saldo Credor
            dados_conta['saldo_credor'] = abs(saldo)
            total_saldo_credor_geral += abs(saldo)
            
    return render_template('balancete.html', saldos_contas=saldos_contas, 
                           total_debitos=total_saldo_devedor_geral, 
                           total_creditos=total_saldo_credor_geral, 
                           usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

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