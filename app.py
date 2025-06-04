from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
from datetime import datetime
import os # Adicionado para verificar se arquivos existem

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_pode_mudar_depois' # Mude para uma chave secreta forte e única

# --- Constantes para nomes de arquivos ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # Pega o diretório do app.py
ARQUIVO_LANCAMENTOS = os.path.join(BASE_DIR, 'lancamentos.json')
ARQUIVO_USUARIOS = os.path.join(BASE_DIR, 'usuarios.json')
ARQUIVO_CONTAS = os.path.join(BASE_DIR, 'contas.json')

# --- Funções Auxiliares para Manipulação de Dados ---
def carregar_dados(arquivo):
    """Carrega dados de um arquivo JSON."""
    if not os.path.exists(arquivo): # Verifica se o arquivo existe
        return [] if arquivo == ARQUIVO_LANCAMENTOS else {} # Retorna lista vazia para lançamentos, dict para outros
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            # Retorna lista vazia ou dict se o arquivo estiver vazio mas existir
            content = f.read()
            if not content:
                return [] if arquivo == ARQUIVO_LANCAMENTOS else {}
            return json.loads(content)
    except json.JSONDecodeError:
        # Se o arquivo existir mas estiver corrompido/mal formatado
        return [] if arquivo == ARQUIVO_LANCAMENTOS else {}
    except FileNotFoundError: # Redundante devido ao os.path.exists, mas bom ter
        return [] if arquivo == ARQUIVO_LANCAMENTOS else {}

def salvar_dados(dados, arquivo):
    """Salva dados em um arquivo JSON."""
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False) # indent=4 para melhor leitura

def carregar_contas():
    """Carrega o plano de contas."""
    return carregar_dados(ARQUIVO_CONTAS)

def carregar_usuarios():
    """Carrega os dados dos usuários."""
    return carregar_dados(ARQUIVO_USUARIOS)

def salvar_usuarios(usuarios):
    """Salva os dados dos usuários."""
    salvar_dados(usuarios, ARQUIVO_USUARIOS)

# --- Rotas da Aplicação ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        usuarios = carregar_usuarios()
        if usuario in usuarios and usuarios[usuario] == senha:
            session['usuario'] = usuario
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    contas = carregar_contas()
    lancamentos = carregar_dados(ARQUIVO_LANCAMENTOS)

    if request.method == 'POST':
        # Lógica para registrar novo lançamento
        conta_selecionada_cod = request.form['conta']
        tipo = request.form['tipo']
        valor_str = request.form['valor']
        historico = request.form['historico']
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Validação do valor
        try:
            valor = float(valor_str)
            if valor <= 0:
                flash('O valor do lançamento deve ser positivo.', 'warning')
                # Recarrega os dados para o gráfico e formulário
                total_d = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
                total_c = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
                return render_template('dashboard.html', usuario=session['usuario'], contas=contas, total_d=total_d, total_c=total_c)
        except ValueError:
            flash('Valor inválido inserido.', 'danger')
            total_d = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
            total_c = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
            return render_template('dashboard.html', usuario=session['usuario'], contas=contas, total_d=total_d, total_c=total_c)


        novo_lancamento = {
            'id': len(lancamentos) + 1, # Simples ID, pode ser melhorado
            'data': data_atual,
            'conta_cod': conta_selecionada_cod,
            'conta_nome': contas.get(conta_selecionada_cod, "Conta Desconhecida"), # Pega o nome da conta
            'tipo': tipo,
            'valor': valor,
            'historico': historico,
            'usuario': session['usuario']
        }
        lancamentos.append(novo_lancamento)
        salvar_dados(lancamentos, ARQUIVO_LANCAMENTOS)
        flash('Lançamento registrado com sucesso!', 'success')
        return redirect(url_for('dashboard')) # Redireciona para limpar o formulário

    # Cálculo dos totais para o gráfico do dashboard
    total_d = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
    total_c = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')

    return render_template('dashboard.html', usuario=session['usuario'], contas=contas, total_d=total_d, total_c=total_c)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if 'usuario' not in session or session['usuario'] != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        novo_usuario = request.form['usuario']
        nova_senha = request.form['senha']
        usuarios = carregar_usuarios()
        if novo_usuario in usuarios:
            flash('Este nome de usuário já existe.', 'warning')
        elif not novo_usuario or not nova_senha:
            flash('Nome de usuário e senha não podem estar vazios.', 'warning')
        else:
            usuarios[novo_usuario] = nova_senha
            salvar_usuarios(usuarios)
            flash(f'Usuário {novo_usuario} cadastrado com sucesso!', 'success')
            return redirect(url_for('dashboard')) # Ou para uma página de gerenciamento de usuários
    return render_template('cadastro.html', usuario=session['usuario'])


@app.route('/diario')
def diario():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    lancamentos = carregar_dados(ARQUIVO_LANCAMENTOS)
    # Ordenar lançamentos por data para o livro diário (do mais antigo para o mais novo)
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x['data'], '%Y-%m-%d %H:%M:%S'))
    return render_template('diario.html', lancamentos=lancamentos_ordenados, usuario=session['usuario'])

@app.route('/razao')
def razao():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    lancamentos = carregar_dados(ARQUIVO_LANCAMENTOS)
    contas = carregar_contas()
    razao_por_conta = {}

    for cod_conta, nome_conta in contas.items():
        razao_por_conta[cod_conta] = {
            'nome': nome_conta,
            'lancamentos': [],
            'saldo_devedor': 0.0,
            'saldo_credor': 0.0,
            'saldo_final': 0.0
        }

    # Ordenar lançamentos por data antes de processar o razão
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
        # Saldo = Credor - Devedor (convenção comum, mas depende da natureza da conta)
        # Para contas de Ativo e Despesa: Saldo Devedor (Débitos > Créditos)
        # Para contas de Passivo, PL e Receita: Saldo Credor (Créditos > Débitos)
        # A lógica abaixo é um saldo genérico. Para um balancete correto, a natureza da conta importa.
        razao_por_conta[cod_conta]['saldo_final'] = razao_por_conta[cod_conta]['saldo_devedor'] - razao_por_conta[cod_conta]['saldo_credor']


    return render_template('razao.html', razao_contas=razao_por_conta, usuario=session['usuario'])

@app.route('/balancete')
def balancete():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    lancamentos = carregar_dados(ARQUIVO_LANCAMENTOS)
    contas = carregar_contas() # Assume que contas.json tem { "cod": "Nome da Conta", "natureza": "D/C" }
    
    saldos_contas = {}
    for cod, nome in contas.items():
        saldos_contas[cod] = {'nome': nome, 'debito': 0.0, 'credito': 0.0, 'saldo_devedor': 0.0, 'saldo_credor': 0.0}

    for lanc in lancamentos:
        cod_conta = lanc.get('conta_cod')
        if cod_conta in saldos_contas:
            valor = float(lanc.get('valor', 0))
            if lanc.get('tipo') == 'D':
                saldos_contas[cod_conta]['debito'] += valor
            elif lanc.get('tipo') == 'C':
                saldos_contas[cod_conta]['credito'] += valor
    
    total_debito_geral = 0
    total_credito_geral = 0

    for cod, dados_conta in saldos_contas.items():
        saldo = dados_conta['debito'] - dados_conta['credito']
        # A natureza da conta (devedora ou credora) determinaria onde o saldo final aparece.
        # Exemplo simples: se saldo > 0 é devedor, se saldo < 0 é credor (invertido).
        # Para um balancete correto, você precisaria da natureza da conta (Ativo/Passivo/PL/Receita/Despesa)
        # e se o saldo normal dela é Devedor ou Credor.
        # Este é um cálculo simplificado:
        if saldo > 0:
            dados_conta['saldo_devedor'] = saldo
            total_debito_geral += saldo
        elif saldo < 0:
            dados_conta['saldo_credor'] = abs(saldo) # Saldo credor é positivo
            total_credito_geral += abs(saldo)
        # Se saldo == 0, ambos os saldos finais são 0

    return render_template('balancete.html', 
                           saldos_contas=saldos_contas, 
                           total_debitos=total_debito_geral, 
                           total_creditos=total_credito_geral, 
                           usuario=session['usuario'])

# --- NOVA ROTA PARA O GRÁFICO POR DATA ---
@app.route('/grafico_data', methods=['GET', 'POST'])
def grafico_data():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    lancamentos_todos = carregar_dados(ARQUIVO_LANCAMENTOS)
    dados_grafico = {
        'labels': [],    # Dias (ex: '01/06/2025')
        'debitos': [],   # Total de débitos por dia
        'creditos': [],  # Total de créditos por dia
        'saldos': []     # Saldo acumulado por dia
    }
    data_inicio_selecionada = ""
    data_fim_selecionada = ""

    if request.method == 'POST':
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        data_inicio_selecionada = data_inicio_str # Para reenviar ao template
        data_fim_selecionada = data_fim_str   # Para reenviar ao template

        if data_inicio_str and data_fim_str:
            try:
                data_inicio_obj = datetime.strptime(data_inicio_str, '%Y-%m-%d').date() # Pega só a data
                data_fim_obj = datetime.strptime(data_fim_str, '%Y-%m-%d').date()     # Pega só a data

                if data_inicio_obj > data_fim_obj:
                    flash('A data de início não pode ser posterior à data de fim.', 'warning')
                else:
                    lancamentos_filtrados_periodo = []
                    for lanc in lancamentos_todos:
                        data_lanc_str_completa = lanc.get('data', '')
                        if data_lanc_str_completa:
                            try:
                                # Converte a data/hora do lançamento para apenas data
                                data_lanc_obj = datetime.strptime(data_lanc_str_completa, '%Y-%m-%d %H:%M:%S').date()
                                if data_inicio_obj <= data_lanc_obj <= data_fim_obj:
                                    lancamentos_filtrados_periodo.append(lanc)
                            except ValueError:
                                print(f"Aviso: Lançamento com data em formato inválido ignorado: {lanc}")
                                continue # Ignora lançamentos com formato de data/hora inválido
                    
                    # Agrupar dados por dia para o gráfico
                    dados_por_dia = {} # Chave: 'YYYY-MM-DD', Valor: {'debitos': 0, 'creditos': 0}
                    
                    # Ordenar por data para processamento cronológico (importante para saldo acumulado)
                    lancamentos_filtrados_periodo.sort(key=lambda x: datetime.strptime(x.get('data'), '%Y-%m-%d %H:%M:%S').date())

                    # Gerar um range de todas as datas no período para garantir que todos os dias apareçam no gráfico
                    # mesmo que não tenham lançamentos.
                    current_date = data_inicio_obj
                    while current_date <= data_fim_obj:
                        dia_str_chave = current_date.strftime('%Y-%m-%d')
                        dados_por_dia[dia_str_chave] = {'debitos': 0, 'creditos': 0}
                        current_date += timedelta(days=1)


                    for lanc in lancamentos_filtrados_periodo:
                        dia_str_chave = datetime.strptime(lanc.get('data'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        
                        valor_lanc = 0
                        try:
                            valor_lanc = float(lanc.get('valor', 0))
                        except ValueError:
                            pass # Ignora valor inválido

                        if lanc.get('tipo') == 'D':
                            dados_por_dia[dia_str_chave]['debitos'] += valor_lanc
                        elif lanc.get('tipo') == 'C':
                            dados_por_dia[dia_str_chave]['creditos'] += valor_lanc
                    
                    # Preparar dados para Chart.js, ordenando pelos dias
                    saldo_acumulado_grafico = 0
                    dias_ordenados_grafico = sorted(dados_por_dia.keys())

                    for dia_str_grafico in dias_ordenados_grafico:
                        dados_grafico['labels'].append(datetime.strptime(dia_str_grafico, '%Y-%m-%d').strftime('%d/%m')) # Formato DD/MM
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
                           usuario=session['usuario'], 
                           dados_grafico=dados_grafico,
                           data_inicio=data_inicio_selecionada, # Para preencher o formulário
                           data_fim=data_fim_selecionada)   # Para preencher o formulário


if __name__ == '__main__':
    # Cria os arquivos JSON se não existirem, para evitar erros na primeira execução
    if not os.path.exists(ARQUIVO_USUARIOS):
        salvar_dados({'admin': 'admin'}, ARQUIVO_USUARIOS) # Usuário admin padrão
    if not os.path.exists(ARQUIVO_LANCAMENTOS):
        salvar_dados([], ARQUIVO_LANCAMENTOS)
    if not os.path.exists(ARQUIVO_CONTAS):
        # Exemplo de plano de contas inicial
        plano_de_contas_inicial = {
            "101": "Caixa",
            "102": "Bancos Conta Movimento",
            "201": "Fornecedores",
            "301": "Receita de Vendas",
            "401": "Despesas com Aluguel"
        }
        salvar_dados(plano_de_contas_inicial, ARQUIVO_CONTAS)

    app.run(debug=True, host='0.0.0.0')