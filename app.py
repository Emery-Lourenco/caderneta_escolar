import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB_FILE = os.path.join(os.path.dirname(__file__), 'data', 'database.json')

def carregar_dados():
    if not os.path.exists(DB_FILE):
        return {"alunos": [], "professores": [], "disciplinas": [], "notas": [], "ocorrencias": []}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        dados = json.load(f)
        dados.setdefault("disciplinas", [])
        dados.setdefault("notas", [])
        return dados

def salvar_dados(dados):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def gerar_novo_id(lista):
    if not lista:
        return 1
    return max(item['id'] for item in lista) + 1

# --- Dashboard ---
@app.route('/')
def index():
    db = carregar_dados()
    resumo = {
        "total_alunos": len(db["alunos"]),
        "total_professores": len(db["professores"]),
        "total_disciplinas": len(db["disciplinas"]),
        "total_ocorrencias": len([o for o in db["ocorrencias"] if o.get('tipo') != 'Elogio / Mérito']),
        "total_elogios": len([o for o in db["ocorrencias"] if o.get('tipo') == 'Elogio / Mérito'])
    }
    return render_template('index.html', resumo=resumo)

# --- Gestão de Alunos e Professores ---
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

@app.route('/professores', methods=['GET', 'POST'])
def professores():
    db = carregar_dados()
    if request.method == 'POST':
        novo_prof = {
            "id": gerar_novo_id(db["professores"]),
            "nome": request.form.get('nome').strip(),
            "email": request.form.get('email').strip()
        }
        db["professores"].append(novo_prof)
        salvar_dados(db)
        return redirect(url_for('professores'))
    return render_template('professores.html', professores=db["professores"])

# --- NOVO: Gestão de Disciplinas ---
@app.route('/disciplinas', methods=['GET', 'POST'])
def disciplinas():
    db = carregar_dados()
    if request.method == 'POST':
        nova_disc = {
            "id": gerar_novo_id(db["disciplinas"]),
            "nome": request.form.get('nome').strip(),
            "professor_id": int(request.form.get('professor_id'))
        }
        db["disciplinas"].append(nova_disc)
        salvar_dados(db)
        return redirect(url_for('disciplinas'))

    professores_map = {p['id']: p['nome'] for p in db['professores']}
    lista_disciplinas = [
        {**d, "professor_nome": professores_map.get(d['professor_id'], 'Sem Professor')}
        for d in db["disciplinas"]
    ]
    return render_template('disciplinas.html', disciplinas=lista_disciplinas, professores=db["professores"])

# --- NOVO: Gestão de Notas ---
@app.route('/notas', methods=['GET', 'POST'])
def notas():
    db = carregar_dados()
    if request.method == 'POST':
        nota1 = float(request.form.get('nota1', 0))
        nota2 = float(request.form.get('nota2', 0))
        media = round((nota1 + nota2) / 2.0, 1)
        situacao = "Aprovado" if media >= 10.0 else "Em Risco"

        nova_nota = {
            "id": gerar_novo_id(db["notas"]),
            "aluno_id": int(request.form.get('aluno_id')),
            "disciplina_id": int(request.form.get('disciplina_id')),
            "trimestre": request.form.get('trimestre'),
            "nota1": nota1,
            "nota2": nota2,
            "media": media,
            "situacao": situacao
        }
        db["notas"].append(nova_nota)
        salvar_dados(db)
        return redirect(url_for('notas'))

    alunos_map = {a['id']: a['nome'] for a in db['alunos']}
    disciplinas_map = {d['id']: d['nome'] for d in db['disciplinas']}

    lista_notas = [
        {
            **n,
            "aluno_nome": alunos_map.get(n['aluno_id'], 'Desconhecido'),
            "disciplina_nome": disciplinas_map.get(n['disciplina_id'], 'Desconhecida')
        }
        for n in db["notas"]
    ]

    return render_template('notas.html', 
                           notas=lista_notas, 
                           alunos=db['alunos'], 
                           disciplinas=db['disciplinas'])

# --- Gestão de Ocorrências com a Regra do Elogio ---
@app.route('/ocorrencias', methods=['GET', 'POST'])
def ocorrencias():
    db = carregar_dados()
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        # Regra de negócio: Se for Elogio / Mérito, não tem gravidade!
        gravidade = "N/A" if tipo == "Elogio / Mérito" else request.form.get('gravidade')

        nova_ocorrencia = {
            "id": gerar_novo_id(db["ocorrencias"]),
            "aluno_id": int(request.form.get('aluno_id')),
            "professor_id": int(request.form.get('professor_id')),
            "data": request.form.get('data') or datetime.now().strftime('%Y-%m-%d'),
            "tipo": tipo,
            "gravidade": gravidade,
            "descricao": request.form.get('descricao').strip()
        }
        db["ocorrencias"].append(nova_ocorrencia)
        salvar_dados(db)
        return redirect(url_for('ocorrencias'))
    
    alunos_map = {a['id']: a['nome'] for a in db['alunos']}
    professores_map = {p['id']: p['nome'] for p in db['professores']}
    
    lista_ocorrencias = [
        {
            **oc,
            "aluno_nome": alunos_map.get(oc['aluno_id'], 'Aluno Desconhecido'),
            "professor_nome": professores_map.get(oc['professor_id'], 'Prof. Desconhecido')
        }
        for oc in db['ocorrencias']
    ]

    return render_template('ocorrencias.html', 
                           ocorrencias=lista_ocorrencias, 
                           alunos=db['alunos'], 
                           professores=db['professores'])

# --- Relatório da Caderneta (Boletim Completo) ---
@app.route('/relatorio')
def relatorio():
    db = carregar_dados()
    aluno_id = request.args.get('aluno_id', type=int)
    
    aluno_selecionado = None
    ocorrencias_aluno = []
    notas_aluno = []
    totais = {"Leve": 0, "Média": 0, "Grave": 0, "Elogios": 0}
    
    if aluno_id:
        aluno_selecionado = next((a for a in db['alunos'] if a['id'] == aluno_id), None)
        professores_map = {p['id']: p['nome'] for p in db['professores']}
        disciplinas_map = {d['id']: d['nome'] for d in db['disciplinas']}
        
        # Ocorrências e Elogios
        for oc in db['ocorrencias']:
            if oc['aluno_id'] == aluno_id:
                oc_copia = dict(oc)
                oc_copia['professor_nome'] = professores_map.get(oc['professor_id'], 'Prof. Desconhecido')
                ocorrencias_aluno.append(oc_copia)
                
                if oc['tipo'] == "Elogio / Mérito":
                    totais["Elogios"] += 1
                elif oc['gravidade'] in totais:
                    totais[oc['gravidade']] += 1

        # Notas do aluno
        for n in db['notas']:
            if n['aluno_id'] == aluno_id:
                n_copia = dict(n)
                n_copia['disciplina_nome'] = disciplinas_map.get(n['disciplina_id'], 'Desconhecida')
                notas_aluno.append(n_copia)

    return render_template('relatorio.html', 
                           alunos=db['alunos'], 
                           aluno=aluno_selecionado, 
                           ocorrencias=ocorrencias_aluno, 
                           notas=notas_aluno,
                           totais=totais)

if __name__ == '__main__':
    app.run(debug=True, port=5000)