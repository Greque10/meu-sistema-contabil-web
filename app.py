from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
from datetime import datetime, timedelta # <--- CORREÇÃO AQUI: timedelta foi adicionado
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_pode_mudar_depois'

# --- Constantes para nomes de arquivos ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_LANCAMENTOS = os.path.join(BASE_DIR, 'lancamentos.json')
ARQUIVO_USUARIOS = os.path.join(BASE_DIR, 'usuarios.json')
ARQUIVO_CONTAS = os.path.join(BASE_DIR, 'contas.json')

# --- Funções Auxiliares para Manipulação de Dados ---
def carregar_dados(arquivo):
    if not os.path.exists(arquivo):
        return [] if arquivo == ARQUIVO_LANCAMENTOS else {}
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return [] if arquivo == ARQUIVO_LANCAMENTOS else {}
            return json.loads(content)
    except json.JSONDecodeError:
        return [] if arquivo == ARQUIVO_LANCAMENTOS else {}
    except FileNotFoundError:
        return [] if arquivo == ARQUIVO_LANCAMENTOS else {}

def salvar_dados(dados, arquivo):
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_contas():
    return carregar_dados(ARQUIVO_CONTAS)

def carregar_usuarios():
    return carregar_dados(ARQUIVO_USUARIOS)

def salvar_usuarios(usuarios):
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
        conta_selecionada_cod = request.form['conta']
        tipo = request.form['tipo']
        valor_str = request.form['valor']
        historico = request.form['historico']
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            valor = float(valor_str)
            if valor <= 0:
                flash('O valor do lançamento deve ser positivo.', 'warning')
                # Recarrega dados para o template em caso de erro
                total_d_erro = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
                total_c_erro = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
                return render_template('dashboard.html', usuario=session.get('usuario'), contas=contas, total_d=total_d_erro, total_c=total_c_erro)
        except ValueError:
            flash('Valor inválido inserido.', 'danger')
            total_d_erro = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
            total_c_erro = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')
            return render_template('dashboard.html', usuario=session.get('usuario'), contas=contas, total_d=total_d_erro, total_c=total_c_erro)

        novo_lancamento = {
            'id': len(lancamentos) + 1,
            'data': data_atual,
            'conta_cod': conta_selecionada_cod,
            'conta_nome': contas.get(conta_selecionada_cod, "Conta Desconhecida"),
            'tipo': tipo,
            'valor': valor,
            'historico': historico,
            'usuario': session.get('usuario')
        }
        lancamentos.append(novo_lancamento)
        salvar_dados(lancamentos, ARQUIVO_LANCAMENTOS)
        flash('Lançamento registrado com sucesso!', 'success')
        return redirect(url_for('dashboard'))

    total_d = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'D')
    total_c = sum(float(l.get('valor', 0)) for l in lancamentos if l.get('tipo') == 'C')

    return render_template('dashboard.html', usuario=session.get('usuario'), contas=contas, total_d=total_d, total_c=total_c)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if 'usuario' not in session or session.get('usuario') != 'admin':
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
            return redirect(url_for('dashboard'))
    return render_template('cadastro.html', usuario=session.get('usuario'))

@app.route('/diario')
def diario():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    lancamentos = carregar_dados(ARQUIVO_LANCAMENTOS)
    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x['data'], '%Y-%m-%d %H:%M:%S'))
    return render_template('diario.html', lancamentos=lancamentos_ordenados, usuario=session.get('usuario'))

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
            'saldo_final': 0.0 # Será calculado com base na natureza da conta para um balancete mais preciso
        }

    lancamentos_ordenados = sorted(lancamentos, key=lambda x: datetime.strptime(x['data'], '%Y-%m-%d %H:%M:%S'))

    for lanc in lancamentos_ordenados:
        cod_conta_lanc = lanc.get('conta_cod')
        if cod_conta_lanc in razao_por_conta:
            try:
                valor = float(lanc.get('valor', 0))
            except ValueError:
                valor = 0.0 # Ignora valor não numérico

            razao_por_conta[cod_conta_lanc]['lancamentos'].append(lanc)
            if lanc.get('tipo') == 'D':
                razao_por_conta[cod_conta_lanc]['saldo_devedor'] += valor
            elif lanc.get('tipo') == 'C':
                razao_por_conta[cod_conta_lanc]['saldo_credor'] += valor
    
    for cod_conta in razao_por_conta:
        # Lógica simplificada do saldo. Para contabilidade correta, a natureza da conta é crucial.
        # Saldo Devedor = Débitos > Créditos
        # Saldo Credor = Créditos > Débitos
        saldo_calc = razao_por_conta[cod_conta]['saldo_devedor'] - razao_por_conta[cod_conta]['saldo_credor']
        razao_por_conta[cod_conta]['saldo_final'] = saldo_calc # Pode ser positivo (devedor) ou negativo (credor)

    return render_template('razao.html', razao_contas=razao_por_conta, usuario=session.get('usuario'))

@app.route('/balancete')
def balancete():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    lancamentos = carregar_dados(ARQUIVO_LANCAMENTOS)
    contas = carregar_contas()
    
    saldos_contas = {}
    for cod, nome in contas.items():
        # Inicializa com a estrutura esperada pelo template
        saldos_contas[cod] = {'nome': nome, 'debito': 0.0, 'credito': 0.0, 'saldo_devedor': 0.0, 'saldo_credor': 0.0}

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
        # Se saldo == 0, ambos os saldos finais são 0, já inicializados

    return render_template('balancete.html', 
                           saldos_contas=saldos_contas, 
                           total_debitos=total_saldo_devedor_geral, # Nome da variável no template
                           total_creditos=total_saldo_credor_geral, # Nome da variável no template
                           usuario=session.get('usuario'))

# --- NOVA ROTA PARA O GRÁFICO POR DATA (COM DEBUG PRINTS) ---
@app.route('/grafico_data', methods=['GET', 'POST'])
def grafico_data():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    lancamentos_todos = carregar_dados(ARQUIVO_LANCAMENTOS)
    dados_grafico = {
        'labels': [],
        'debitos': [],
        'creditos': [],
        'saldos': []
    }
    data_inicio_selecionada = "" # Para manter o valor no formulário
    data_fim_selecionada = ""    # Para manter o valor no formulário

    if request.method == 'POST':
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')
        data_inicio_selecionada = data_inicio_str
        data_fim_selecionada = data_fim_str

        print(f"--- DEBUG: Recebido data_inicio: {data_inicio_str}, data_fim: {data_fim_str} ---") # DEBUG

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
                                print(f"AVISO: Lançamento com data em formato inválido ignorado: {lanc.get('id', 'ID Desconhecido')}")
                                continue
                    
                    # print(f"--- DEBUG: Lançamentos filtrados: {lancamentos_filtrados_periodo} ---") # DEBUG (pode ser muito longo)

                    dados_por_dia = {}
                    lancamentos_filtrados_periodo.sort(key=lambda x: datetime.strptime(x.get('data'), '%Y-%m-%d %H:%M:%S').date())

                    current_date_iter = data_inicio_obj
                    while current_date_iter <= data_fim_obj:
                        dia_str_chave = current_date_iter.strftime('%Y-%m-%d')
                        dados_por_dia[dia_str_chave] = {'debitos': 0, 'creditos': 0}
                        current_date_iter += timedelta(days=1) # timedelta agora está importado

                    for lanc in lancamentos_filtrados_periodo:
                        dia_str_chave = datetime.strptime(lanc.get('data'), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        valor_lanc = 0.0
                        try:
                            valor_lanc = float(lanc.get('valor', 0))
                        except ValueError:
                             print(f"AVISO: Valor de lançamento inválido ignorado: {lanc.get('id', 'ID Desconhecido')}")
                        
                        if dia_str_chave in dados_por_dia: # Garante que o dia existe no dict
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
                    
                    print(f"--- DEBUG: Dados para o gráfico (final): {dados_grafico} ---") # DEBUG

            except ValueError as e:
                flash('Formato de data inválido. Use o formato AAAA-MM-DD.', 'danger')
                print(f"ERRO: ValueError ao processar datas - {e}") # DEBUG
        else:
            flash('Por favor, selecione a data de início e a data de fim.', 'warning')
            print("AVISO: Datas não fornecidas no POST.") # DEBUG

    return render_template('grafico_data.html', 
                           usuario=session.get('usuario'), 
                           dados_grafico=dados_grafico,
                           data_inicio=data_inicio_selecionada,
                           data_fim=data_fim_selecionada)

if __name__ == '__main__':
    if not os.path.exists(ARQUIVO_USUARIOS):
        salvar_dados({'admin': 'admin'}, ARQUIVO_USUARIOS)
    if not os.path.exists(ARQUIVO_LANCAMENTOS):
        salvar_dados([], ARQUIVO_LANCAMENTOS)
    if not os.path.exists(ARQUIVO_CONTAS):
        plano_de_contas_inicial = {
            "101": "Caixa", "102": "Bancos Conta Movimento", "201": "Fornecedores",
            "301": "Receita de Vendas", "401": "Despesas com Aluguel"
        }
        salvar_dados(plano_de_contas_inicial, ARQUIVO_CONTAS)

    app.run(debug=True, host='0.0.0.0')
