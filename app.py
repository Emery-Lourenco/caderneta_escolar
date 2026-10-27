import io
import csv
import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, Response, flash

app = Flask(__name__)
app.secret_key = 'caderneta_escolar_super_secret_key'
DB_FILE = os.path.join(os.path.dirname(__file__), 'data', 'database.json')

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return {
            "alunos": [],
            "professores": [],
            "disciplinas": [],
            "notas": [],
            "ocorrencias": [],
            "frequencias": []
        }
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        dados = json.load(f)
        for chave in ["alunos", "professores", "disciplinas", "notas", "ocorrencias", "frequencias"]:
            dados.setdefault(chave, [])
        return dados

def salvar_dados(dados):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def gerar_novo_id(lista):
    if not lista:
        return 1
    return max(item['id'] for item in lista) + 1

# ==========================================
# DASHBOARD ANALÍTICO & GESTÃO DE BACKUP
# ==========================================
@app.route('/')
def index():
    db = carregar_dados()
    
    # Métricas de Conduta
    elogios = len([o for o in db["ocorrencias"] if o.get('tipo') == 'Elogio / Mérito'])
    leves = len([o for o in db["ocorrencias"] if o.get('gravidade') == 'Leve'])
    medias = len([o for o in db["ocorrencias"] if o.get('gravidade') in ['Média', 'Media']])
    graves = len([o for o in db["ocorrencias"] if o.get('gravidade') == 'Grave'])
    
    # Métricas de Rendimento
    aprovados = len([n for n in db["notas"] if n.get('situacao') == 'Aprovado'])
    em_risco = len([n for n in db["notas"] if n.get('situacao') == 'Em Risco'])
    
    # Métricas de Frequência
    faltas_just = len([f for f in db["frequencias"] if f.get('tipo') == 'Justificada'])
    faltas_injust = len([f for f in db["frequencias"] if f.get('tipo') == 'Injustificada'])

    resumo = {
        "total_alunos": len(db["alunos"]),
        "total_professores": len(db["professores"]),
        "total_disciplinas": len(db["disciplinas"]),
        "total_notas": len(db["notas"]),
        "total_ocorrencias": leves + medias + graves,
        "total_elogios": elogios,
        "total_faltas": len(db["frequencias"])
    }

    dados_graficos = {
        "conduta": [elogios, leves, medias, graves],
        "rendimento": [aprovados, em_risco],
        "faltas": [faltas_just, faltas_injust]
    }

    return render_template('index.html', resumo=resumo, graficos=dados_graficos)

@app.route('/backup/download')
def backup_download():
    """Descarrega o ficheiro JSON como cópia de segurança."""
    nome_ficheiro = f"backup_caderneta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return send_file(DB_FILE, as_attachment=True, download_name=nome_ficheiro, mimetype='application/json')

@app.route('/backup/restaurar', methods=['POST'])
def backup_restaurar():
    """Restaura a base de dados a partir de um ficheiro JSON submetido."""
    ficheiro = request.files.get('backup_file')
    if not ficheiro or ficheiro.filename == '':
        flash('Nenhum ficheiro selecionado.', 'erro')
        return redirect(url_for('index'))
    
    try:
        conteudo = json.load(ficheiro)
        chaves_obrigatorias = ["alunos", "professores", "disciplinas", "notas", "ocorrencias", "frequencias"]
        if not all(chave in conteudo for chave in chaves_obrigatorias):
            flash('Ficheiro de backup inválido: faltam entidades estruturais.', 'erro')
            return redirect(url_for('index'))
        
        salvar_dados(conteudo)
        flash('Base de dados restaurada com sucesso!', 'sucesso')
    except Exception as e:
        flash(f'Erro ao ler o ficheiro de backup: {str(e)}', 'erro')

    return redirect(url_for('index'))

# ==========================================
# EXPORTAÇÃO CSV PARA EXCEL
# ==========================================
@app.route('/exportar/notas')
def exportar_notas_csv():
    """Exporta a pauta completa de notas para CSV compatível com Excel."""
    db = carregar_dados()
    alunos_map = {a['id']: a for a in db['alunos']}
    disciplinas_map = {d['id']: d['nome'] for d in db['disciplinas']}

    output = io.StringIO()
    # UTF-8 BOM para garantir exibição correta de caracteres especiais no Microsoft Excel
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')

    writer.writerow(['Matrícula', 'Aluno', 'Turma', 'Disciplina', 'Período', 'Nota 1', 'Nota 2', 'Média', 'Situação'])
    for n in db['notas']:
        aluno = alunos_map.get(n['aluno_id'], {})
        writer.writerow([
            aluno.get('matricula', '—'),
            aluno.get('nome', 'Desconhecido'),
            aluno.get('turma', '—'),
            disciplinas_map.get(n['disciplina_id'], '—'),
            n.get('trimestre', '—'),
            n.get('nota1', 0),
            n.get('nota2', 0),
            n.get('media', 0),
            n.get('situacao', '—')
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=pauta_notas_escolar.csv"}
    )

# ==========================================
# ALUNOS (Com Pesquisa Textual e Filtro por Turma)
# ==========================================
@app.route('/alunos', methods=['GET', 'POST'])
def alunos():
    db = carregar_dados()
    editar_id = request.args.get('editar_id', type=int)
    aluno_editando = next((a for a in db['alunos'] if a['id'] == editar_id), None) if editar_id else None

    if request.method == 'POST':
        item_id = request.form.get('id', type=int)
        nome = request.form.get('nome').strip()
        matricula = request.form.get('matricula').strip()
        turma = request.form.get('turma').strip()

        if item_id:
            for a in db['alunos']:
                if a['id'] == item_id:
                    a.update({"nome": nome, "matricula": matricula, "turma": turma})
                    break
        else:
            db["alunos"].append({
                "id": gerar_novo_id(db["alunos"]),
                "nome": nome,
                "matricula": matricula,
                "turma": turma
            })

        salvar_dados(db)
        return redirect(url_for('alunos'))

    # Filtros e Pesquisa
    busca = request.args.get('q', '').strip().lower()
    filtro_turma = request.args.get('turma', '').strip()
    ordem = request.args.get('ordem', 'nome_asc')

    turmas_disponiveis = sorted(list({a['turma'] for a in db['alunos'] if a.get('turma')}))

    lista = list(db["alunos"])
    if busca:
        lista = [a for a in lista if busca in a['nome'].lower() or busca in a['matricula'].lower()]
    if filtro_turma:
        lista = [a for a in lista if a['turma'] == filtro_turma]

    if ordem == 'nome_asc':
        lista.sort(key=lambda x: x['nome'].lower())
    elif ordem == 'nome_desc':
        lista.sort(key=lambda x: x['nome'].lower(), reverse=True)
    elif ordem == 'turma':
        lista.sort(key=lambda x: x['turma'].lower())
    elif ordem == 'matricula':
        lista.sort(key=lambda x: x['matricula'].lower())

    return render_template('alunos.html', 
                           alunos=lista, 
                           editando=aluno_editando, 
                           ordem_atual=ordem, 
                           turmas=turmas_disponiveis,
                           busca_atual=busca,
                           turma_atual=filtro_turma)

@app.route('/alunos/eliminar/<int:id>')
def alunos_eliminar(id):
    db = carregar_dados()
    db['alunos'] = [a for a in db['alunos'] if a['id'] != id]
    salvar_dados(db)
    return redirect(url_for('alunos'))

# ==========================================
# PROFESSORES
# ==========================================
@app.route('/professores', methods=['GET', 'POST'])
def professores():
    db = carregar_dados()
    editar_id = request.args.get('editar_id', type=int)
    prof_editando = next((p for p in db['professores'] if p['id'] == editar_id), None) if editar_id else None

    if request.method == 'POST':
        item_id = request.form.get('id', type=int)
        nome = request.form.get('nome').strip()
        email = request.form.get('email').strip()

        if item_id:
            for p in db['professores']:
                if p['id'] == item_id:
                    p.update({"nome": nome, "email": email})
                    break
        else:
            db["professores"].append({
                "id": gerar_novo_id(db["professores"]),
                "nome": nome,
                "email": email
            })

        salvar_dados(db)
        return redirect(url_for('professores'))

    ordem = request.args.get('ordem', 'nome_asc')
    lista = list(db["professores"])
    if ordem == 'nome_asc':
        lista.sort(key=lambda x: x['nome'].lower())
    elif ordem == 'nome_desc':
        lista.sort(key=lambda x: x['nome'].lower(), reverse=True)
    elif ordem == 'email':
        lista.sort(key=lambda x: x['email'].lower())

    return render_template('professores.html', professores=lista, editando=prof_editando, ordem_atual=ordem)

@app.route('/professores/eliminar/<int:id>')
def professores_eliminar(id):
    db = carregar_dados()
    db['professores'] = [p for p in db['professores'] if p['id'] != id]
    salvar_dados(db)
    return redirect(url_for('professores'))

# ==========================================
# DISCIPLINAS
# ==========================================
@app.route('/disciplinas', methods=['GET', 'POST'])
def disciplinas():
    db = carregar_dados()
    editar_id = request.args.get('editar_id', type=int)
    disc_editando = next((d for d in db['disciplinas'] if d['id'] == editar_id), None) if editar_id else None

    if request.method == 'POST':
        item_id = request.form.get('id', type=int)
        nome = request.form.get('nome').strip()
        professor_id = int(request.form.get('professor_id'))

        if item_id:
            for d in db['disciplinas']:
                if d['id'] == item_id:
                    d.update({"nome": nome, "professor_id": professor_id})
                    break
        else:
            db["disciplinas"].append({
                "id": gerar_novo_id(db["disciplinas"]),
                "nome": nome,
                "professor_id": professor_id
            })

        salvar_dados(db)
        return redirect(url_for('disciplinas'))

    professores_map = {p['id']: p['nome'] for p in db['professores']}
    lista = [
        {**d, "professor_nome": professores_map.get(d['professor_id'], 'Sem Professor')}
        for d in db["disciplinas"]
    ]

    ordem = request.args.get('ordem', 'nome_asc')
    if ordem == 'nome_asc':
        lista.sort(key=lambda x: x['nome'].lower())
    elif ordem == 'nome_desc':
        lista.sort(key=lambda x: x['nome'].lower(), reverse=True)
    elif ordem == 'professor':
        lista.sort(key=lambda x: x['professor_nome'].lower())

    return render_template('disciplinas.html', disciplinas=lista, professores=db["professores"], editando=disc_editando, ordem_atual=ordem)

@app.route('/disciplinas/eliminar/<int:id>')
def disciplinas_eliminar(id):
    db = carregar_dados()
    db['disciplinas'] = [d for d in db['disciplinas'] if d['id'] != id]
    salvar_dados(db)
    return redirect(url_for('disciplinas'))

# ==========================================
# NOTAS (Com Filtro por Turma e Disciplina)
# ==========================================
@app.route('/notas', methods=['GET', 'POST'])
def notas():
    db = carregar_dados()
    editar_id = request.args.get('editar_id', type=int)
    nota_editando = next((n for n in db['notas'] if n['id'] == editar_id), None) if editar_id else None

    if request.method == 'POST':
        item_id = request.form.get('id', type=int)
        aluno_id = int(request.form.get('aluno_id'))
        disciplina_id = int(request.form.get('disciplina_id'))
        trimestre = request.form.get('trimestre')
        nota1 = float(request.form.get('nota1', 0))
        nota2 = float(request.form.get('nota2', 0))
        media = round((nota1 + nota2) / 2.0, 1)
        situacao = "Aprovado" if media >= 10.0 else "Em Risco"

        if item_id:
            for n in db['notas']:
                if n['id'] == item_id:
                    n.update({
                        "aluno_id": aluno_id,
                        "disciplina_id": disciplina_id,
                        "trimestre": trimestre,
                        "nota1": nota1,
                        "nota2": nota2,
                        "media": media,
                        "situacao": situacao
                    })
                    break
        else:
            existente = next(
                (n for n in db['notas'] 
                 if n['aluno_id'] == aluno_id and n['disciplina_id'] == disciplina_id and n['trimestre'] == trimestre),
                None
            )
            if existente:
                existente.update({"nota1": nota1, "nota2": nota2, "media": media, "situacao": situacao})
            else:
                db['notas'].append({
                    "id": gerar_novo_id(db["notas"]),
                    "aluno_id": aluno_id,
                    "disciplina_id": disciplina_id,
                    "trimestre": trimestre,
                    "nota1": nota1,
                    "nota2": nota2,
                    "media": media,
                    "situacao": situacao
                })

        salvar_dados(db)
        return redirect(url_for('notas'))

    alunos_map = {a['id']: a for a in db['alunos']}
    disciplinas_map = {d['id']: d['nome'] for d in db['disciplinas']}

    lista = [
        {
            **n,
            "aluno_nome": alunos_map.get(n['aluno_id'], {}).get('nome', 'Desconhecido'),
            "aluno_turma": alunos_map.get(n['aluno_id'], {}).get('turma', '—'),
            "disciplina_nome": disciplinas_map.get(n['disciplina_id'], 'Desconhecida')
        }
        for n in db["notas"]
    ]

    filtro_turma = request.args.get('turma', '').strip()
    if filtro_turma:
        lista = [n for n in lista if n['aluno_turma'] == filtro_turma]

    ordem = request.args.get('ordem', 'aluno')
    if ordem == 'aluno':
        lista.sort(key=lambda x: x['aluno_nome'].lower())
    elif ordem == 'disciplina':
        lista.sort(key=lambda x: x['disciplina_nome'].lower())
    elif ordem == 'media_desc':
        lista.sort(key=lambda x: x['media'], reverse=True)
    elif ordem == 'media_asc':
        lista.sort(key=lambda x: x['media'])
    elif ordem == 'trimestre':
        lista.sort(key=lambda x: x['trimestre'])

    turmas_disponiveis = sorted(list({a['turma'] for a in db['alunos'] if a.get('turma')}))

    return render_template('notas.html', 
                           notas=lista, 
                           alunos=db['alunos'], 
                           disciplinas=db['disciplinas'],
                           turmas=turmas_disponiveis,
                           turma_atual=filtro_turma,
                           editando=nota_editando,
                           ordem_atual=ordem)

@app.route('/notas/eliminar/<int:id>')
def notas_eliminar(id):
    db = carregar_dados()
    db['notas'] = [n for n in db['notas'] if n['id'] != id]
    salvar_dados(db)
    return redirect(url_for('notas'))

# ==========================================
# OCORRÊNCIAS
# ==========================================
@app.route('/ocorrencias', methods=['GET', 'POST'])
def ocorrencias():
    db = carregar_dados()
    editar_id = request.args.get('editar_id', type=int)
    oc_editando = next((o for o in db['ocorrencias'] if o['id'] == editar_id), None) if editar_id else None

    if request.method == 'POST':
        item_id = request.form.get('id', type=int)
        tipo = request.form.get('tipo')
        gravidade = "N/A" if tipo == "Elogio / Mérito" else request.form.get('gravidade')
        if gravidade in ['Media', 'Média']:
            gravidade = 'Média'

        aluno_id = int(request.form.get('aluno_id'))
        professor_id = int(request.form.get('professor_id'))
        data_oc = request.form.get('data') or datetime.now().strftime('%Y-%m-%d')
        descricao = request.form.get('descricao').strip()

        if item_id:
            for o in db['ocorrencias']:
                if o['id'] == item_id:
                    o.update({
                        "aluno_id": aluno_id,
                        "professor_id": professor_id,
                        "data": data_oc,
                        "tipo": tipo,
                        "gravidade": gravidade,
                        "descricao": descricao
                    })
                    break
        else:
            db["ocorrencias"].append({
                "id": gerar_novo_id(db["ocorrencias"]),
                "aluno_id": aluno_id,
                "professor_id": professor_id,
                "data": data_oc,
                "tipo": tipo,
                "gravidade": gravidade,
                "descricao": descricao
            })

        salvar_dados(db)
        return redirect(url_for('ocorrencias'))
    
    alunos_map = {a['id']: a['nome'] for a in db['alunos']}
    professores_map = {p['id']: p['nome'] for p in db['professores']}
    
    lista = [
        {
            **oc,
            "aluno_nome": alunos_map.get(oc['aluno_id'], 'Aluno Desconhecido'),
            "professor_nome": professores_map.get(oc['professor_id'], 'Prof. Desconhecido')
        }
        for oc in db['ocorrencias']
    ]

    ordem = request.args.get('ordem', 'data_desc')
    grav_peso = {'Grave': 3, 'Média': 2, 'Media': 2, 'Leve': 1, 'N/A': 0}
    if ordem == 'data_desc':
        lista.sort(key=lambda x: x['data'], reverse=True)
    elif ordem == 'data_asc':
        lista.sort(key=lambda x: x['data'])
    elif ordem == 'aluno':
        lista.sort(key=lambda x: x['aluno_nome'].lower())
    elif ordem == 'gravidade':
        lista.sort(key=lambda x: grav_peso.get(x['gravidade'], 0), reverse=True)
    elif ordem == 'tipo':
        lista.sort(key=lambda x: x['tipo'].lower())

    return render_template('ocorrencias.html', 
                           ocorrencias=lista, 
                           alunos=db['alunos'], 
                           professores=db['professores'],
                           editando=oc_editando,
                           ordem_atual=ordem)

@app.route('/ocorrencias/eliminar/<int:id>')
def ocorrencias_eliminar(id):
    db = carregar_dados()
    db['ocorrencias'] = [o for o in db['ocorrencias'] if o['id'] != id]
    salvar_dados(db)
    return redirect(url_for('ocorrencias'))

# ==========================================
# FREQUÊNCIAS
# ==========================================
@app.route('/frequencias', methods=['GET', 'POST'])
def frequencias():
    db = carregar_dados()
    editar_id = request.args.get('editar_id', type=int)
    freq_editando = next((f for f in db['frequencias'] if f['id'] == editar_id), None) if editar_id else None

    if request.method == 'POST':
        item_id = request.form.get('id', type=int)
        aluno_id = int(request.form.get('aluno_id'))
        disciplina_id = int(request.form.get('disciplina_id'))
        data_falta = request.form.get('data') or datetime.now().strftime('%Y-%m-%d')
        tipo = request.form.get('tipo')
        justificativa = request.form.get('justificativa', '').strip()

        if item_id:
            for f in db['frequencias']:
                if f['id'] == item_id:
                    f.update({
                        "aluno_id": aluno_id,
                        "disciplina_id": disciplina_id,
                        "data": data_falta,
                        "tipo": tipo,
                        "justificativa": justificativa
                    })
                    break
        else:
            db["frequencias"].append({
                "id": gerar_novo_id(db["frequencias"]),
                "aluno_id": aluno_id,
                "disciplina_id": disciplina_id,
                "data": data_falta,
                "tipo": tipo,
                "justificativa": justificativa
            })

        salvar_dados(db)
        return redirect(url_for('frequencias'))

    alunos_map = {a['id']: a['nome'] for a in db['alunos']}
    disciplinas_map = {d['id']: d['nome'] for d in db['disciplinas']}

    lista = [
        {
            **f,
            "aluno_nome": alunos_map.get(f['aluno_id'], 'Desconhecido'),
            "disciplina_nome": disciplinas_map.get(f['disciplina_id'], 'Geral')
        }
        for f in db["frequencias"]
    ]

    ordem = request.args.get('ordem', 'data_desc')
    if ordem == 'data_desc':
        lista.sort(key=lambda x: x['data'], reverse=True)
    elif ordem == 'data_asc':
        lista.sort(key=lambda x: x['data'])
    elif ordem == 'aluno':
        lista.sort(key=lambda x: x['aluno_nome'].lower())
    elif ordem == 'tipo':
        lista.sort(key=lambda x: x['tipo'])

    return render_template('frequencias.html', 
                           frequencias=lista, 
                           alunos=db['alunos'], 
                           disciplinas=db['disciplinas'],
                           editando=freq_editando,
                           ordem_atual=ordem)

@app.route('/frequencias/eliminar/<int:id>')
def frequencias_eliminar(id):
    db = carregar_dados()
    db['frequencias'] = [f for f in db['frequencias'] if f['id'] != id]
    salvar_dados(db)
    return redirect(url_for('frequencias'))

# ==========================================
# BOLETIM / RELATÓRIO
# ==========================================
@app.route('/relatorio')
def relatorio():
    db = carregar_dados()
    aluno_id = request.args.get('aluno_id', type=int)
    
    aluno_selecionado = None
    ocorrencias_aluno = []
    notas_aluno = []
    faltas_aluno = []
    totais = {"Leve": 0, "Média": 0, "Grave": 0, "Elogios": 0}
    totais_faltas = {"Justificada": 0, "Injustificada": 0, "Total": 0}
    
    if aluno_id:
        aluno_selecionado = next((a for a in db['alunos'] if a['id'] == aluno_id), None)
        professores_map = {p['id']: p['nome'] for p in db['professores']}
        disciplinas_map = {d['id']: d['nome'] for d in db['disciplinas']}
        
        for oc in db['ocorrencias']:
            if oc['aluno_id'] == aluno_id:
                oc_copia = dict(oc)
                oc_copia['professor_nome'] = professores_map.get(oc['professor_id'], 'Prof. Desconhecido')
                ocorrencias_aluno.append(oc_copia)
                
                grav = oc.get('gravidade')
                if oc.get('tipo') == "Elogio / Mérito":
                    totais["Elogios"] += 1
                elif grav in ['Média', 'Media']:
                    totais["Média"] += 1
                elif grav in totais:
                    totais[grav] += 1

        for n in db['notas']:
            if n['aluno_id'] == aluno_id:
                n_copia = dict(n)
                n_copia['disciplina_nome'] = disciplinas_map.get(n['disciplina_id'], 'Desconhecida')
                notas_aluno.append(n_copia)

        for f in db['frequencias']:
            if f['aluno_id'] == aluno_id:
                f_copia = dict(f)
                f_copia['disciplina_nome'] = disciplinas_map.get(f['disciplina_id'], 'Geral')
                faltas_aluno.append(f_copia)
                totais_faltas["Total"] += 1
                if f['tipo'] in totais_faltas:
                    totais_faltas[f['tipo']] += 1

    return render_template('relatorio.html', 
                           alunos=db['alunos'], 
                           aluno=aluno_selecionado, 
                           ocorrencias=ocorrencias_aluno, 
                           notas=notas_aluno,
                           faltas=faltas_aluno,
                           totais=totais,
                           totais_faltas=totais_faltas)

if __name__ == '__main__':
    app.run(debug=True, port=5000)