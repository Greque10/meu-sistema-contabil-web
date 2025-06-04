from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
from datetime import datetime, timedelta
import os
import uuid # Para gerar IDs únicos para empresas

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_multi_empresa' # Mude para uma chave secreta forte

# --- Constantes para nomes de arquivos e diretórios ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data') # Novo diretório para dados das empresas
ARQUIVO_EMPRESAS = os.path.join(BASE_DIR, 'empresas.json') # Global, lista de empresas

# Nomes de ficheiro dentro da pasta de cada empresa
NOME_ARQUIVO_LANCAMENTOS = 'lancamentos.json'
NOME_ARQUIVO_USUARIOS = 'usuarios.json'
NOME_ARQUIVO_CONTAS = 'contas.json'

# --- Funções Auxiliares Globais ---
def carregar_empresas():
    if not os.path.exists(ARQUIVO_EMPRESAS):
        return {} # { "id_empresa": {"nome": "Nome Empresa", "admin_user": "admin_da_empresa"} }
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
    """Retorna o caminho completo para um ficheiro de dados de uma empresa."""
    return os.path.join(DATA_DIR, str(id_empresa), nome_arquivo)

def carregar_dados_empresa(id_empresa, nome_arquivo_base):
    """Carrega dados de um ficheiro JSON específico da empresa."""
    arquivo = obter_caminho_arquivo_empresa(id_empresa, nome_arquivo_base)
    if not os.path.exists(arquivo):
        return [] if nome_arquivo_base == NOME_ARQUIVO_LANCAMENTOS else {}
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return [] if nome_arquivo_base == NOME_ARQUIVO_LANCAMENTOS else {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return [] if nome_arquivo_base == NOME_ARQUIVO_LANCAMENTOS else {}

def salvar_dados_empresa(id_empresa, dados, nome_arquivo_base):
    """Salva dados em um ficheiro JSON específico da empresa."""
    caminho_pasta_empresa = os.path.join(DATA_DIR, str(id_empresa))
    if not os.path.exists(caminho_pasta_empresa):
        os.makedirs(caminho_pasta_empresa) # Cria a pasta da empresa se não existir
    
    arquivo = obter_caminho_arquivo_empresa(id_empresa, nome_arquivo_base)
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# Funções específicas para carregar/salvar tipos de dados
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
            "10101": "Caixa Geral", "10102": "Bancos Conta Movimento",
            "20101": "Fornecedores Nacionais", "20102": "Salários a Pagar",
            "30101": "Receita Bruta de Vendas", "30102": "Receita de Serviços",
            "40101": "Custo das Mercadorias Vendidas", "40102": "Despesas com Aluguel",
            "40103": "Despesas com Salários"
        }
        salvar_dados_empresa(id_empresa, plano_de_contas_inicial, NOME_ARQUIVO_CONTAS)
        return plano_de_contas_inicial
    return contas


# --- Rotas da Aplicação ---

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
            return render_template('registrar_empresa.html')

        empresas = carregar_empresas()

        # Verificar se o nome da empresa já existe
        if any(emp['nome'].lower() == nome_empresa.lower() for emp in empresas.values()):
            flash('Já existe uma empresa registada com este nome.', 'warning')
            return render_template('registrar_empresa.html', nome_empresa=nome_empresa, admin_usuario=admin_usuario)

        # Verificar se o nome de utilizador do admin já está em uso em alguma empresa (simplificado)
        # Uma verificação mais robusta poderia ser necessária se utilizadores pudessem pertencer a múltiplas empresas
        for id_emp_existente in empresas:
            usuarios_existentes = carregar_usuarios_empresa(id_emp_existente)
            if admin_usuario in usuarios_existentes:
                flash(f'O nome de utilizador "{admin_usuario}" já está em uso. Escolha outro.', 'warning')
                return render_template('registrar_empresa.html', nome_empresa=nome_empresa, admin_usuario=admin_usuario)

        id_nova_empresa = str(uuid.uuid4()) # Gera um ID único para a empresa
        
        # Criar pasta e ficheiros para a nova empresa
        caminho_pasta_nova_empresa = os.path.join(DATA_DIR, id_nova_empresa)
        os.makedirs(caminho_pasta_nova_empresa, exist_ok=True)

        # Criar utilizador admin para a nova empresa
        usuarios_nova_empresa = {admin_usuario: admin_senha} # Idealmente, hashear a senha
        salvar_usuarios_empresa(id_nova_empresa, usuarios_nova_empresa)

        # Criar ficheiros de lançamentos e contas vazios/padrão
        salvar_lancamentos_empresa(id_nova_empresa, [])
        carregar_contas_empresa(id_nova_empresa) # Isto cria o plano de contas padrão se não existir

        # Adicionar nova empresa ao ficheiro global de empresas
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

# --- Rotas que precisam do contexto da empresa ---
def verificar_sessao_empresa():
    """Verifica se o utilizador está logado e tem uma empresa associada."""
    if 'usuario' not in session or 'id_empresa' not in session:
        flash('Sessão inválida ou expirada. Por favor, faça login novamente.', 'warning')
        return False
    return True

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if not verificar_sessao_empresa(): # Função auxiliar que já criamos
        return redirect(url_for('login'))
    
    id_empresa_atual = session['id_empresa']
    contas = carregar_contas_empresa(id_empresa_atual)
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)

    admin_da_empresa_atual = None
    empresas = carregar_empresas()
    if id_empresa_atual in empresas:
        admin_da_empresa_atual = empresas[id_empresa_atual].get('admin_user')

    if request.method == 'POST':
        # ... (sua lógica de registro de lançamento - mantenha como está) ...
        # Certifique-se de que, ao renderizar em caso de erro no POST, também passa 'admin_da_empresa_atual'
        # e os dados para os gráficos, se aplicável, ou inicialize-os como vazios.
        conta_selecionada_cod = request.form['conta']
        tipo = request.form['tipo']
        valor_str = request.form['valor']
        historico = request.form['historico']
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            valor = float(valor_str)
            if valor <= 0:
                flash('O valor do lançamento deve ser positivo.', 'warning')
                # Recarregar dados para o template em caso de erro
                # (Lógica para dados dos gráficos precisa ser repetida ou encapsulada)
                total_d_erro = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
                total_c_erro = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
                # Dados para gráfico de pizza (despesas)
                dados_despesas_pizza_erro = preparar_dados_despesas_pizza(lancamentos)
                return render_template('dashboard.html', 
                                       usuario=session.get('usuario'), 
                                       nome_empresa=session.get('nome_empresa'), 
                                       contas=contas, 
                                       total_d=total_d_erro, 
                                       total_c=total_c_erro,
                                       admin_da_empresa=admin_da_empresa_atual,
                                       dados_despesas_pizza=dados_despesas_pizza_erro)
        except ValueError:
            flash('Valor inválido inserido.', 'danger')
            total_d_erro = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
            total_c_erro = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
            dados_despesas_pizza_erro = preparar_dados_despesas_pizza(lancamentos)
            return render_template('dashboard.html', 
                                   usuario=session.get('usuario'), 
                                   nome_empresa=session.get('nome_empresa'), 
                                   contas=contas, 
                                   total_d=total_d_erro, 
                                   total_c=total_c_erro,
                                   admin_da_empresa=admin_da_empresa_atual,
                                   dados_despesas_pizza=dados_despesas_pizza_erro)

        novo_lancamento = {
            'id': len(lancamentos) + 1,
            'data': data_atual,
            'conta_cod': conta_selecionada_cod,
            'conta_nome': contas.get(conta_selecionada_cod, "Conta Desconhecida") if isinstance(contas.get(conta_selecionada_cod), str) else contas.get(conta_selecionada_cod, {}).get('nome', "Conta Desconhecida"),
            'tipo': tipo,
            'valor': valor,
            'historico': historico,
            'usuario': session.get('usuario')
        }
        lancamentos.append(novo_lancamento)
        salvar_lancamentos_empresa(id_empresa_atual, lancamentos)
        flash('Lançamento registrado com sucesso!', 'success')
        return redirect(url_for('dashboard'))

    # Cálculo dos totais para o gráfico de barras do dashboard
    total_d = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
    total_c = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')

    # --- PREPARAR DADOS PARA O GRÁFICO DE PIZZA (DESPESAS POR CONTA) ---
    dados_despesas_pizza = preparar_dados_despesas_pizza(lancamentos)
    # --- FIM DA PREPARAÇÃO PARA GRÁFICO DE PIZZA ---

    return render_template('dashboard.html', 
                           usuario=session.get('usuario'), 
                           nome_empresa=session.get('nome_empresa'), 
                           contas=contas, 
                           total_d=total_d, 
                           total_c=total_c,
                           admin_da_empresa=admin_da_empresa_atual,
                           dados_despesas_pizza=dados_despesas_pizza) # Passa os novos dados

# --- NOVA FUNÇÃO AUXILIAR PARA PREPARAR DADOS DO GRÁFICO DE PIZZA ---
def preparar_dados_despesas_pizza(lancamentos):
    """Prepara dados para o gráfico de pizza de despesas por conta."""
    despesas_por_conta = {} # Ex: {"Aluguel": 1200, "Material Escritório": 300}
    for lanc in lancamentos:
        if lanc.get('tipo') == 'D': # Considera apenas Débitos como despesas
            try:
                valor = float(lanc.get('valor', 0))
                nome_conta = lanc.get('conta_nome', 'Desconhecida')
                if nome_conta in despesas_por_conta:
                    despesas_por_conta[nome_conta] += valor
                else:
                    despesas_por_conta[nome_conta] = valor
            except ValueError:
                continue # Ignora lançamentos com valor inválido

    # Limitar o número de fatias para não poluir o gráfico (opcional)
    # Por exemplo, mostrar as Top N despesas e agrupar o resto em "Outros"
    # Para simplificar, vamos mostrar todas por enquanto.

    labels_pizza = list(despesas_por_conta.keys())
    data_pizza = list(despesas_por_conta.values())
    
    return {'labels': labels_pizza, 'data': data_pizza}

@app.route('/cadastro', methods=['GET', 'POST']) # Cadastro de utilizadores DENTRO de uma empresa
def cadastro():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    
    # Apenas o admin da empresa pode registar novos utilizadores para ESSA empresa
    # Precisamos de saber quem é o admin da empresa atual.
    # Por simplicidade, vamos assumir que o primeiro utilizador registado para uma empresa é o admin dela.
    # Ou podemos verificar se session.get('usuario') é o admin_user guardado em empresas.json
    
    empresas = carregar_empresas()
    id_empresa_atual = session['id_empresa']
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
                usuarios_empresa[novo_usuario_form] = nova_senha_form # Idealmente, hashear
                salvar_usuarios_empresa(id_empresa_atual, usuarios_empresa)
                flash(f'Utilizador "{novo_usuario_form}" registado com sucesso para a empresa!', 'success')
    
    return render_template('cadastro.html', usuario=usuario_logado_admin, nome_empresa=session.get('nome_empresa'))


# As rotas de relatórios também precisam de usar o id_empresa_atual
@app.route('/diario')
def diario():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x['data'], '%Y-%m-%d %H:%M:%S'))
    return render_template('diario.html', lancamentos=lancamentos_ordenados, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

@app.route('/razao')
def razao():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)
    razao_por_conta = {}

    for cod_conta, nome_conta_obj in contas.items(): # contas agora pode ser um dict de dicts
        nome_conta_str = nome_conta_obj if isinstance(nome_conta_obj, str) else nome_conta_obj.get('nome', 'Desconhecida')
        razao_por_conta[cod_conta] = {
            'nome': nome_conta_str, 'lancamentos': [],
            'saldo_devedor': 0.0, 'saldo_credor': 0.0, 'saldo_final': 0.0
        }
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x['data'], '%Y-%m-%d %H:%M:%S'))
    for lanc in lancamentos_ordenados:
        cod_conta_lanc = lanc.get('conta_cod')
        if cod_conta_lanc in razao_por_conta:
            valor = float(lanc.get('valor', 0))
            razao_por_conta[cod_conta_lanc]['lancamentos'].append(lanc)
            if lanc.get('tipo') == 'D':
                razao_por_conta[cod_conta_lanc]['saldo_devedor'] += valor
            elif lanc.get('tipo') == 'C':
                razao_por_conta[cod_conta_lanc]['saldo_credor'] += valor
    for cod_conta in razao_por_conta:
        razao_por_conta[cod_conta]['saldo_final'] = razao_por_conta[cod_conta]['saldo_devedor'] - razao_por_conta[cod_conta]['saldo_credor']
    return render_template('razao.html', razao_contas=razao_por_conta, usuario=session.get('usuario'), nome_empresa=session.get('nome_empresa'))

@app.route('/balancete')
def balancete():
    if not verificar_sessao_empresa():
        return redirect(url_for('login'))
    id_empresa_atual = session['id_empresa']
    lancamentos = carregar_lancamentos_empresa(id_empresa_atual)
    contas = carregar_contas_empresa(id_empresa_atual)
    saldos_contas = {}
    for cod, nome_conta_obj in contas.items():
        nome_conta_str = nome_conta_obj if isinstance(nome_conta_obj, str) else nome_conta_obj.get('nome', 'Desconhecida')
        saldos_contas[cod] = {'nome': nome_conta_str, 'debito': 0.0, 'credito': 0.0, 'saldo_devedor': 0.0, 'saldo_credor': 0.0}
    for lanc in lancamentos:
        cod_conta = lanc.get('conta_cod')
        if cod_conta in saldos_contas:
            valor = float(lanc.get('valor', 0))
            if lanc.get('tipo') == 'D':
                saldos_contas[cod_conta]['debito'] += valor
            elif lanc.get('tipo') == 'C':
                saldos_contas[cod_conta]['credito'] += valor
    total_saldo_devedor_geral = 0
    total_saldo_credor_geral = 0
    for cod, dados_conta in saldos_contas.items():
        saldo = dados_conta['debito'] - dados_conta['credito']
        if saldo > 0:
            dados_conta['saldo_devedor'] = saldo
            total_saldo_devedor_geral += saldo
        elif saldo < 0:
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
    data_inicio_selecionada = ""
    data_fim_selecionada = ""

    if request.method == 'POST':
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        data_inicio_selecionada = data_inicio_str
        data_fim_selecionada = data_fim_str
        if data_inicio_str and data_fim_str:
            try:
                data_inicio_obj = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                data_fim_obj = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
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
                    lancamentos_filtrados_periodo.sort(key=lambda x: datetime.strptime(x.get('data'), '%Y-%m-%d %H:%M:%S').date())
                    current_date_iter = data_inicio_obj
                    while current_date_iter <= data_fim_obj:
                        dia_str_chave = current_date_iter.strftime('%Y-%m-%d')
                        dados_por_dia[dia_str_chave] = {'debitos': 0, 'creditos': 0}
                        current_date_iter += timedelta(days=1)
                    for lanc in lancamentos_filtrados_periodo:
                        dia_str_chave = datetime.strptime(lanc.get('data'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        valor_lanc = float(lanc.get('valor', 0))
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
    # Cria o diretório 'data' se não existir
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    # Cria o ficheiro de empresas se não existir
    if not os.path.exists(ARQUIVO_EMPRESAS):
        salvar_empresas({}) # Começa com nenhuma empresa

    app.run(debug=True, host='0.0.0.0')
