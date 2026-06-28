"""
chatbot_tab.py — Módulo de ChatBot com RAG para recomendação de praias.

Fluxo:
  1. Usuário digita uma pergunta em linguagem natural
  2. Busca semântica via TF-IDF nos reviews (avaliacoes_praias_final.csv)
  3. Recupera notas por aspecto do ABSA (praia_aspecto_scores_gemini.csv)
  4. Envia contexto + pergunta para Gemini (gemini-2.5-flash-lite)
  5. Exibe resposta com citações reais das avaliações

Uso:
    from chatbot_tab import render_chatbot
    render_chatbot()
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


_BASE = Path(__file__).parent
_REVIEWS_CSV = _BASE / "avaliacoes_praias_final.csv"
_SCORES_CSV  = _BASE / "praia_aspecto_scores_gemini.csv"
_ABSA_CSV    = _BASE / "avaliacoes_aspectos_gemini.csv"

@st.cache_resource(show_spinner="Indexando reviews para busca semântica…")
def _carregar_rag():
    """
    Carrega os CSVs e treina o vetorizador TF-IDF.
    Retorna (chunks_df, vetorizador, X_sparse, scores_df).
    """
    import nltk
    from sklearn.feature_extraction.text import TfidfVectorizer

    #  Reviews principais 
    df = pd.read_csv(_REVIEWS_CSV, encoding="utf-8-sig")
    df = df.dropna(subset=["text"]).reset_index(drop=True)
    df["doc_id"] = df.index

    # Montando chunks
    def _chunk(row):
        titulo = str(row.get("title", "") or "").strip()
        texto  = str(row.get("text",  "") or "").strip()
        return f"{titulo}. {texto}" if titulo else texto

    chunks_df = pd.DataFrame({
        "chunk_id": [f"review-{i}" for i in df["doc_id"]],
        "doc_id":   df["doc_id"].values,
        "praia":    df["praia"].values,
        "rating":   df["rating"].values,
        "title":    df["title"].values,
        "date":     df["date"].values,
        "chunk":    df.apply(_chunk, axis=1).values,
    })

    # Stopwords português
    try:
        stopwords_pt = nltk.corpus.stopwords.words("portuguese")
    except LookupError:
        nltk.download("stopwords", quiet=True)
        stopwords_pt = nltk.corpus.stopwords.words("portuguese")

    sw = sorted({re.sub(r"\s+", " ", w.lower()).strip() for w in stopwords_pt if w.strip()})

    vetorizador = TfidfVectorizer(
        lowercase=True,
        strip_accents=None,
        stop_words=sw,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.92,
    )
    X = vetorizador.fit_transform(chunks_df["chunk"])

    scores_df = pd.DataFrame()
    if _SCORES_CSV.exists():
        scores_df = pd.read_csv(_SCORES_CSV, encoding="utf-8-sig")

    return chunks_df, vetorizador, X, scores_df


def _recuperar_contextos(pergunta: str, top_k: int = 5) -> pd.DataFrame:
    """Retorna os top-k chunks mais similares à pergunta."""
    from sklearn.metrics.pairwise import cosine_similarity

    chunks_df, vetorizador, X, _ = _carregar_rag()

    pergunta = re.sub(r"\s+", " ", pergunta).strip()
    vetor    = vetorizador.transform([pergunta])
    sims     = cosine_similarity(vetor, X).ravel()
    indices  = np.argsort(sims)[::-1][:top_k]

    resultados = []
    for idx in indices:
        score = float(sims[idx])
        if score < 0.01:
            continue
        item = chunks_df.iloc[idx].to_dict()
        item["score"] = score
        resultados.append(item)

    if not resultados:
        return pd.DataFrame(columns=list(chunks_df.columns) + ["score"])
    return pd.DataFrame(resultados).reset_index(drop=True)


def _resumo_aspectos(praias: list[str]) -> str:
    """Formata uma tabela de notas por aspecto para as praias recuperadas."""
    _, _, _, scores_df = _carregar_rag()
    if scores_df.empty or not praias:
        return ""

    filtro = scores_df[scores_df["praia"].isin(praias)]
    if filtro.empty:
        return ""

    pivot = (
        filtro.pivot_table(
            index="praia",
            columns="aspecto_nome",
            values="nota_media",
            aggfunc="mean",
        )
        .round(1)
    )
    linhas = ["Notas ABSA por aspecto (escala 1-5):"]
    for praia, row in pivot.iterrows():
        nome_exibir = str(praia).replace("praia_", "").replace("_", " ").title()
        notas = " | ".join(
            f"{asp}: {val:.1f}" for asp, val in row.items() if not np.isnan(val)
        )
        linhas.append(f"  {nome_exibir} → {notas}")

    return "\n".join(linhas)


def _recortar(texto: str, limite: int = 600) -> str:
    texto = re.sub(r"\s+", " ", str(texto)).strip()
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0] + "…"


def _montar_prompt(pergunta: str, contextos: pd.DataFrame, resumo_absa: str) -> str:
    blocos = []
    for i, row in contextos.reset_index(drop=True).iterrows():
        praia = str(row["praia"]).replace("_", " ").title()
        titulo = str(row['title']).replace('"', "'")
        meta  = f'{praia} | nota={row["rating"]} | {row["date"]} | "{titulo}"'
        blocos.append(f"[C{i+1}] {meta}\n{_recortar(row['chunk'])}")

    contexto_str = "\n\n".join(blocos)

    prompt = f"""Você é um assistente especialista em praias de Santa Catarina, Brasil.
Responda em português, de forma objetiva e amigável (máximo 3 parágrafos).
Use APENAS as informações dos contextos abaixo. Cite as fontes como [C1], [C2]…
Se os contextos não forem suficientes, diga isso claramente.

{resumo_absa}

Avaliações recuperadas:
{contexto_str}

Pergunta do usuário: {pergunta}
Resposta:"""
    return prompt


def _chamar_gemini(prompt: str, api_key: str) -> str:
    """Chama a API Gemini e retorna o texto gerado."""
    import google.generativeai as genai  # type: ignore

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    resp  = model.generate_content(prompt)
    return resp.text.strip()


def _executar_rag(pergunta: str, api_key: str) -> dict:
    """Orquestra todo o pipeline e devolve um dict com resposta + metadados."""
    contextos = _recuperar_contextos(pergunta, top_k=5)

    if contextos.empty:
        return {
            "resposta": (
                "Não encontrei avaliações suficientes na base para responder. "
                "Tente reformular com outros termos (ex.: 'praia calma', 'boa para família')."
            ),
            "praias": [],
            "fontes": [],
        }

    praias = contextos["praia"].dropna().unique().tolist()
    resumo_absa = _resumo_aspectos(praias)
    prompt      = _montar_prompt(pergunta, contextos, resumo_absa)

    try:
        resposta = _chamar_gemini(prompt, api_key)
    except Exception as exc:
        resposta = f"⚠️ Erro ao chamar o Gemini: {exc}"

    fontes = []
    for i, row in contextos.reset_index(drop=True).iterrows():
        nome = str(row["praia"]).replace("praia_", "").replace("_", " ").title()
        fontes.append(f"[C{i+1}] {nome} · nota {row['rating']} · {_recortar(row['title'], 60)}")

    return {"resposta": resposta, "praias": praias, "fontes": fontes}


def render_chatbot(altura: int = 600) -> None:
    """Renderiza a aba completa do chatbot. Chamar dentro de um st.tab ou diretamente.

    altura: altura (px) do box do histórico, que rola internamente. Padrão 600
    (comportamento anterior); a página Assistente passa um valor menor.
    """

    try:
        api_key: str = st.secrets.get("GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    except Exception:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        api_key = st.text_input(
            "🔑 Chave Gemini API",
            type="password",
            placeholder="Cole sua GEMINI_API_KEY aqui",
            help="Obtenha em https://aistudio.google.com/app/apikey",
        )
    if not api_key:
        st.info("Informe a chave Gemini API acima para ativar o assistente.")
        return

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    @st.fragment
    def _chat_fragment(api_key: str) -> None:
        if st.button("Limpar conversa", use_container_width=True, key="chat_clear"):
            st.session_state.chat_messages = []
            st.rerun(scope="fragment")

        with st.container(height=altura, border=True):
            if not st.session_state.chat_messages:
                st.caption("👋 Olá! Pergunte algo como: *quero praia tranquila para família*")
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant" and msg.get("fontes"):
                        with st.expander("📌 Fontes", expanded=False):
                            for f in msg["fontes"]:
                                st.caption(f)

        pergunta = st.chat_input("Ex.: quero uma praia tranquila para família…", key="chat_input")

        if pergunta:
            st.session_state.chat_messages.append({"role": "user", "content": pergunta})
            st.session_state._chat_pending = pergunta
            st.rerun(scope="fragment")

        if st.session_state.get("_chat_pending"):
            pergunta_pendente = st.session_state.pop("_chat_pending")
            with st.spinner("Buscando praias e analisando reviews…"):
                resultado = _executar_rag(pergunta_pendente, api_key)
            st.session_state.chat_messages.append({
                "role":   "assistant",
                "content": resultado["resposta"],
                "fontes":  resultado.get("fontes", []),
            })
            st.rerun(scope="fragment")

    _chat_fragment(api_key)