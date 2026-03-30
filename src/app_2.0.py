import json
import pandas as pd
import requests
import streamlit as st
from pathlib import Path

# ================= CONFIG =================
OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = "gpt-oss:20b"  # pode usar mistral também

# ================= DADOS =================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / 'data'

perfil_df = pd.read_csv(DATA_DIR / 'profiles.csv')
gabinetes = pd.read_csv(DATA_DIR / 'cases.csv')
compatibilidade = pd.read_csv(DATA_DIR / 'compatibility.csv')

with open(DATA_DIR / 'configuration_weights.json', 'r', encoding='utf-8') as f:
    configuration = json.load(f)

cpus = pd.read_csv(DATA_DIR / 'cpus.csv')
gpus = pd.read_csv(DATA_DIR / 'gpus.csv')
motherboards = pd.read_csv(DATA_DIR / 'motherboards.csv')
fontes = pd.read_csv(DATA_DIR / 'psu.csv')
ram = pd.read_csv(DATA_DIR / 'ram.csv')
storage = pd.read_csv(DATA_DIR / 'storage.csv')

# ================= PREPARAÇÃO =================
def preparar_dados():
    cpus['score_cpu'] = cpus['custo_beneficio'].map({
        'alto': 3,
        'medio': 2,
        'baixo': 1
    })

    gpus['score_gpu'] = gpus['nivel'].map({
        'entrada': 1,
        'medio': 2,
        'alto': 3
    })

preparar_dados()

# ================= ESTADO =================
if "messages" not in st.session_state:
    st.session_state.messages = []

# ================= INTENÇÃO =================
def extrair_intencao(msg):
    msg = msg.lower()

    if "ia" in msg:
        perfil = "ia_dev"
    elif "program" in msg:
        perfil = "programador"
    elif "video" in msg or "edi" in msg:
        perfil = "editor_video"
    elif "office" in msg:
        perfil = "office"
    else:
        perfil = "gamer"

    import re
    match = re.search(r'\d+', msg)
    orcamento = int(match.group()) if match else 5000

    return {"perfil": perfil, "orcamento": orcamento}

# ================= FILTRO =================
def filtrar_por_orcamento(df, limite):
    return df[df['preco_brl'] <= limite]

# ================= COMPATIBILIDADE =================
def escolher_placa_mae(cpu):
    socket = cpu['plataforma']
    mbs = motherboards[motherboards['socket'] == socket]
    return mbs.sort_values(by='preco_brl').iloc[0]

# ================= ENGINE =================
def montar_build(dados):
    perfil = dados['perfil']
    orcamento = dados['orcamento']

    pesos = configuration["pesos_perfil"].get(perfil, {})

    cpus_f = filtrar_por_orcamento(cpus, orcamento * 0.3)
    gpus_f = filtrar_por_orcamento(gpus, orcamento * 0.5)
    ram_f = filtrar_por_orcamento(ram, orcamento * 0.2)
    storage_f = filtrar_por_orcamento(storage, orcamento * 0.2)
    fontes_f = filtrar_por_orcamento(fontes, orcamento * 0.2)
    gabinetes_f = filtrar_por_orcamento(gabinetes, orcamento * 0.15)

    melhor = None
    melhor_score = -1

    for _, cpu in cpus_f.iterrows():
        for _, gpu in gpus_f.iterrows():
            for _, r in ram_f.iterrows():
                for _, s in storage_f.iterrows():

                    mb = escolher_placa_mae(cpu)
                    fonte = fontes_f.iloc[0]
                    gabinete = gabinetes_f.iloc[0]

                    preco_total = (
                        cpu['preco_brl'] + gpu['preco_brl'] + r['preco_brl'] +
                        s['preco_brl'] + mb['preco_brl'] + fonte['preco_brl'] +
                        gabinete['preco_brl']
                    )

                    if preco_total > orcamento:
                        continue

                    score = (
                        pesos.get("cpu", 0) * cpu['score_cpu'] +
                        pesos.get("gpu", 0) * gpu['score_gpu'] +
                        pesos.get("ram", 0) * r['capacidade_gb'] +
                        pesos.get("storage", 0) * s['capacidade_gb']
                    )

                    if score > melhor_score:
                        melhor_score = score
                        melhor = (cpu, gpu, r, s, mb, fonte, gabinete, preco_total)

    return melhor

# ================= IA (SÓ EXPLICAÇÃO) =================
def explicar_build(build, dados):
    cpu, gpu, r, s, mb, fonte, gabinete, preco = build

    prompt = f"""
Explique de forma objetiva a configuração abaixo.

Perfil: {dados['perfil']}
Orçamento: {dados['orcamento']}

CPU: {cpu['modelo']}
GPU: {gpu['modelo']}
RAM: {r['modelo']} {r['capacidade_gb']}GB
Storage: {s['modelo']}
Placa-mãe: {mb['modelo']}
Fonte: {fonte['modelo']}
Gabinete: {gabinete['modelo']}

Explique:
- equilíbrio da build
- escolha da GPU
- escolha da CPU
- possibilidade de upgrade

Resposta curta.
"""

    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODELO,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.4
        }, )

        return r.json().get("response", "")

    except:
        return "Explicação indisponível."

# ================= PIPELINE =================
def responder(msg):
    dados = extrair_intencao(msg)
    build = montar_build(dados)

    if not build:
        return "Não foi possível montar uma configuração dentro do orçamento."

    cpu, gpu, r, s, mb, fonte, gabinete, preco = build

    explicacao = explicar_build(build, dados)

    return f"""
--- CONFIGURAÇÃO RECOMENDADA ---

CPU: {cpu['modelo']}
GPU: {gpu['modelo']}
RAM: {r['modelo']} ({r['capacidade_gb']}GB)
Armazenamento: {s['modelo']}
Placa-mãe: {mb['modelo']}
Fonte: {fonte['modelo']}
Gabinete: {gabinete['modelo']}

Preço total: R$ {preco}

--- JUSTIFICATIVA ---
{explicacao}
"""

# ================= UI =================
st.title("🧠 PC Builder Expert (Engine Profissional)")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if pergunta := st.chat_input("Ex: PC gamer até 5000"):
    st.session_state.messages.append({"role": "user", "content": pergunta})

    with st.chat_message("user"):
        st.write(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Calculando melhor configuração..."):
            resposta = responder(pergunta)
            st.write(resposta)

    st.session_state.messages.append({"role": "assistant", "content": resposta})
