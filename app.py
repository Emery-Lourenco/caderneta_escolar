import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB_FILE = os.path.join(os.path.dirname(__file__), 'data', 'database.json')

# --- Funções Auxiliares de Banco JSON ---
def carregar_dados():
    if not os.path.exists(DB_FILE):
        return {"alunos": [], "professores": [], "ocorrencias": []}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def gerar_novo_id(lista):
    if not lista:
        return 1
    return max(item['id'] for item in lista) + 1

# --- Rotas Principais ---
@app.route('/')
def index():
    db = carregar_dados()
    resumo = {
        "total_alunos": len(db["alunos"]),
        "total_professores": len(db["professores"]),
        "total_ocorrencias": len(db["ocorrencias"])
    }
    return render_template('index.html', resumo=resumo)

# --- Gestão de Alunos ---
@app.route('/alunos', methods=['GET', 'POST'])
def alunos():
    db = carregar_dados()
    if request.method == 'POST':
        novo_aluno = {
            "id": gerar_novo_id(db["alunos"]),
            "nome": request.form.get('nome').strip(),
            "matricula": request.form.get('matricula').strip(),
            "turma": request.form.get('turma').strip()
        }
        db["alunos"].append(novo_aluno)
        salvar_dados(db)
        return redirect(url_for('alunos'))
    
    return render_template('alunos.html', alunos=db["alunos"])

# --- Gestão de Professores ---
@app.route('/professores', methods=['GET', 'POST'])
def professores():
    db = carregar_dados()
    if request.method == 'POST':
        novo_prof = {
            "id": gerar_novo_id(db["professores"]),
            "nome": request.form.get('nome').strip(),
            "disciplina": request.form.get('disciplina').strip(),
            "email": request.form.get('email').strip()
        }
        db["professores"].append(novo_prof)
        salvar_dados(db)
        return redirect(url_for('professores'))
    
    return render_template('professores.html', professores=db["professores"])

# --- Gestão de Ocorrências ---
@app.route('/ocorrencias', methods=['GET', 'POST'])
def ocorrencias():
    db = carregar_dados()
    if request.method == 'POST':
        nova_ocorrencia = {
            "id": gerar_novo_id(db["ocorrencias"]),
            "aluno_id": int(request.form.get('aluno_id')),
            "professor_id": int(request.form.get('professor_id')),
            "data": request.form.get('data') or datetime.now().strftime('%Y-%m-%d'),
            "tipo": request.form.get('tipo'), # Disciplinar, Pedagógica, Elogio
            "gravidade": request.form.get('gravidade'), # Leve, Média, Grave
            "descricao": request.form.get('descricao').strip()
        }
        db["ocorrencias"].append(nova_ocorrencia)
        salvar_dados(db)
        return redirect(url_for('ocorrencias'))
    
    # Mapeia nomes para exibição na lista
    alunos_map = {a['id']: a['nome'] for a in db['alunos']}
    professores_map = {p['id']: p['nome'] for p in db['professores']}
    
    lista_ocorrencias = []
    for oc in db['ocorrencias']:
        lista_ocorrencias.append({
            **oc,
            "aluno_nome": alunos_map.get(oc['aluno_id'], 'Aluno Desconhecido'),
            "professor_nome": professores_map.get(oc['professor_id'], 'Prof. Desconhecido')
        })

    return render_template('ocorrencias.html', 
                           ocorrencias=lista_ocorrencias, 
                           alunos=db['alunos'], 
                           professores=db['professores'])

# --- Relatório da Caderneta ---
@app.route('/relatorio')
def relatorio():
    db = carregar_dados()
    aluno_id = request.args.get('aluno_id', type=int)
    
    aluno_selecionado = None
    ocorrencias_aluno = []
    totais = {"Leve": 0, "Média": 0, "Grave": 0}
    
    if aluno_id:
        aluno_selecionado = next((a for a in db['alunos'] if a['id'] == aluno_id), None)
        professores_map = {p['id']: p['nome'] for p in db['professores']}
        
        for oc in db['ocorrencias']:
            if oc['aluno_id'] == aluno_id:
                oc_copia = dict(oc)
                oc_copia['professor_nome'] = professores_map.get(oc['professor_id'], 'Prof. Desconhecido')
                ocorrencias_aluno.append(oc_copia)
                if oc['gravidade'] in totais:
                    totais[oc['gravidade']] += 1

    return render_template('relatorio.html', 
                           alunos=db['alunos'], 
                           aluno=aluno_selecionado, 
                           ocorrencias=ocorrencias_aluno, 
                           totais=totais)

if __name__ == '__main__':
    app.run(debug=True, port=5000)