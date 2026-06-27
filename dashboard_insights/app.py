"""
Dashboard de Insights — Módulo 3 (PLN / FURB)
Avaliações de praias de Santa Catarina (TripAdvisor).

Como rodar:
    pip install -r requirements.txt
    streamlit run app.py

Requer o arquivo `avaliacoes_praias_final.csv` na mesma pasta
(ou envie pela barra lateral quando o app abrir).
"""
from pathlib import Path

import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from wordcloud import WordCloud

import data as dados
from chatbot_tab import render_chatbot

st.set_page_config(page_title="Insights — Praias de SC", page_icon="🏖️", layout="wide")


@st.cache_data(show_spinner="Carregando e processando as avaliações...")
def _carregar(fonte):
    return dados.carregar_dados(fonte)


@st.cache_data(show_spinner=False)
def _geojson_brasil():
    import json
    import urllib.request
    url = ("https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
           "master/public/data/brazil-states.geojson")
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def obter_dados():
    """Resolve a fonte do CSV: arquivo local padrão ou upload na barra lateral."""
    caminho = Path(dados.ARQUIVO_PADRAO)
    if caminho.exists():
        return _carregar(str(caminho))
    arquivo = st.sidebar.file_uploader("Envie o avaliacoes_praias_final.csv", type="csv")
    if arquivo is None:
        st.info("📁 Coloque **avaliacoes_praias_final.csv** na pasta do app "
                "ou envie pela barra lateral para começar.")
        st.stop()
    return _carregar(arquivo)


df = obter_dados()

st.sidebar.header("Filtros")

anos = df["ano"].dropna()
ano_min, ano_max = int(anos.min()), int(anos.max())
faixa = st.sidebar.slider("Período (ano)", ano_min, ano_max, (ano_min, ano_max))

praias = sorted(df["praia"].unique())
if st.sidebar.checkbox("Todas as praias", True):
    sel_praias = praias
else:
    sel_praias = st.sidebar.multiselect("Praias", praias, default=praias[:5]) or praias

notas = st.sidebar.multiselect("Notas (rating)", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])

with st.sidebar:
    st.divider()
    st.markdown("### 🏖️ Assistente de Praias")
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] .chat-container {
            height: 420px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 8px;
            background: #fafafa;
        }
        /* Impede que o chat_input empurre o layout da sidebar */
        [data-testid="stSidebar"] [data-testid="stChatInput"] {
            position: sticky;
            bottom: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_chatbot()

dff = df[
    df["ano"].between(faixa[0], faixa[1])
    & df["praia"].isin(sel_praias)
    & df["rating"].isin(notas)
].copy()


st.title("🏖️ Dashboard de Insights — Praias de Santa Catarina")
st.caption("Módulo 3 · avaliações do TripAdvisor · proxy de aspectos até o ABSA")

if dff.empty:
    st.warning("Nenhuma avaliação para os filtros selecionados.")
    st.stop()

origem = dff[dff["origem_preenchida"]]
fora_sc = (origem["uf"] != "SC").mean() * 100 if len(origem) else float("nan")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Avaliações", f"{len(dff):,}".replace(",", "."))
c2.metric("Praias", dff["praia"].nunique())
c3.metric("Nota média", f"{dff['rating'].mean():.2f}")
c4.metric("Turistas de fora de SC", "—" if origem.empty else f"{fora_sc:.0f}%")


aba_origem, aba_tempo, aba_aspectos, aba_nuvem = st.tabs(
    ["🗺️ Origem", "📈 Evolução temporal", "⭐ Aspectos", "☁️ Nuvem de palavras"]
)

# ---- 1. Origem ----
with aba_origem:
    st.subheader("De onde vêm os turistas")
    st.caption(f"Origem informada em {dff['origem_preenchida'].mean() * 100:.1f}% "
               "das avaliações filtradas.")
    if origem.empty:
        st.info("Sem dados de origem para os filtros atuais.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            ufs = origem["uf"].value_counts().head(15).sort_values()
            fig = px.bar(ufs, orientation="h", title="Top UFs de origem",
                         labels={"value": "avaliações", "index": "UF"})
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width="stretch")
        with col2:
            try:
                geo = _geojson_brasil()
                mapa = (origem.loc[origem["uf"].isin(dados.UF), "uf"]
                        .map(dados.NOME_POR_UF).value_counts()
                        .rename_axis("estado").reset_index(name="avaliacoes"))
                fig = px.choropleth(mapa, geojson=geo, locations="estado",
                                    featureidkey="properties.name", color="avaliacoes",
                                    color_continuous_scale="Blues",
                                    title="Origem por estado")
                fig.update_geos(fitbounds="locations", visible=False)
                st.plotly_chart(fig, width="stretch")
            except Exception:
                st.info("Mapa por estado indisponível (sem internet para o GeoJSON).")

        st.markdown("**Top cidades de origem**")
        cidades = origem["cidade_origem"].value_counts().head(15).sort_values()
        fig = px.bar(cidades, orientation="h",
                     labels={"value": "avaliações", "index": "cidade"})
        fig.update_layout(showlegend=False, height=450)
        st.plotly_chart(fig, width="stretch")

# ---- 2. Evolução temporal ----
with aba_tempo:
    st.subheader("Evolução ao longo do tempo")
    ts = dff.dropna(subset=["dt"])
    media = dff["rating"].mean()

    col1, col2 = st.columns(2)
    with col1:
        vol = ts.groupby("ano").size()
        fig = px.line(vol, markers=True, title="Avaliações por ano",
                      labels={"value": "avaliações", "ano": "ano"})
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")
    with col2:
        nota_ano = ts.groupby("ano")["rating"].mean()
        fig = px.line(nota_ano, markers=True, title="Nota média por ano",
                      labels={"value": "nota média", "ano": "ano"})
        fig.update_yaxes(range=[1, 5])
        fig.add_hline(y=media, line_dash="dot", annotation_text=f"média ({media:.2f})")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")

    saz = ts.groupby("mes").size()
    fig = px.bar(saz, title="Sazonalidade — avaliações por mês do ano",
                 labels={"value": "avaliações", "mes": "mês"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")

    top = dff["praia"].value_counts().head(5).index
    serie = (ts[ts["praia"].isin(top)]
             .groupby(["ano", "praia"])["rating"].mean().reset_index())
    fig = px.line(serie, x="ano", y="rating", color="praia", markers=True,
                  title="Nota média por ano — praias mais avaliadas")
    fig.update_yaxes(range=[1, 5])
    st.plotly_chart(fig, width="stretch")

# ---- 3. Aspectos ----
with aba_aspectos:
    st.subheader("Ranking de praias e aspectos")
    st.caption("Proxy por palavras-chave até a matriz praia × aspecto do ABSA ficar pronta.")

    MIN_AVAL = 30
    rank = (dff.groupby("praia")["rating"].agg(media="mean", n="count")
            .sort_values("media", ascending=False).round(2))
    r = rank.sort_values("media").reset_index()
    fig = px.bar(r, x="media", y="praia", orientation="h", text="n",
                 color="n", color_continuous_scale="Blues",
                 title="Ranking por nota média (rótulo/cor = nº de avaliações)",
                 labels={"media": "nota média", "praia": "", "n": "nº avaliações"})
    fig.add_vline(x=dff["rating"].mean(), line_dash="dot", annotation_text="média geral")
    fig.update_layout(height=650)
    st.plotly_chart(fig, width="stretch")
    ruidosas = list(rank[rank["n"] < MIN_AVAL].index)
    if ruidosas:
        st.caption(f"⚠️ Médias pouco confiáveis (< {MIN_AVAL} avaliações): "
                   + ", ".join(ruidosas))

    st.markdown("**Aspectos mais comentados e satisfação**")
    st.dataframe(dados.resumo_aspectos(dff), width="stretch", hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        freq = dados.matriz_frequencia(dff)
        fig = px.imshow(freq, text_auto=".0f", aspect="auto",
                        color_continuous_scale="Blues",
                        title="Frequência de menção por praia (%)")
        fig.update_layout(height=600)
        st.plotly_chart(fig, width="stretch")
    with col2:
        lift = dados.matriz_lift(dff)
        fig = px.imshow(lift, text_auto=".2f", aspect="auto",
                        color_continuous_scale="RdBu", color_continuous_midpoint=0,
                        title="Satisfação vs. média da praia (vermelho = ponto fraco)")
        fig.update_layout(height=600)
        st.plotly_chart(fig, width="stretch")

# ---- 4. Nuvem de palavras ----
with aba_nuvem:
    st.subheader("Nuvem de palavras por praia")
    praia = st.selectbox("Praia", sorted(dff["praia"].unique()))
    sentimento = st.radio("Avaliações", ["Todas", "Positivas (4-5)", "Negativas (1-2)"],
                          horizontal=True)

    base = dff[dff["praia"] == praia]
    if sentimento.startswith("Positivas"):
        base = base[base["rating"] >= 4]
    elif sentimento.startswith("Negativas"):
        base = base[base["rating"] <= 2]

    stop = dados.stopwords_dominio(df)
    toks = []
    for t in base["text_lemmatized"]:
        toks += [w for w in t if w.lower() not in stop and len(w) > 2]
    texto = " ".join(toks)

    if not texto.strip():
        st.info("Sem palavras suficientes para essa combinação de praia/sentimento.")
    else:
        wc = WordCloud(width=1000, height=450, background_color="white",
                       colormap="viridis").generate(texto)
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.imshow(wc)
        ax.axis("off")
        st.pyplot(fig)
        st.caption(f"{len(base)} avaliações · {praia}")

st.divider()
st.caption("Quando o ABSA (matriz praia × aspecto) ficar pronto, basta trocar o proxy "
           "em `data.py` (resumo/freq/lift) pela saída real.")