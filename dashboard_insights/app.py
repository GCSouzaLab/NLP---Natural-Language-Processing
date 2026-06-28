"""
App principal — Praias de Santa Catarina (PLN / FURB).

Reúne os 3 módulos do projeto em um app multipage (st.navigation):
    📊 Dashboard de Insights  (Mayara)   -> página inicial
    🎯 Recomendador de Praias (em construção)
    💬 Assistente / Chatbot RAG (Gabriel)

O menu lateral troca de página; cada página é dona dos próprios controles
(os filtros de ano/praia/nota vivem só no Dashboard).

Como rodar (Windows):
    pip install -r requirements.txt
    python -m streamlit run app.py
"""
import streamlit as st

# set_page_config é chamado UMA vez, aqui no ponto de entrada (vale pra todas as páginas).
st.set_page_config(page_title="Praias de SC — PLN", page_icon="🏖️", layout="wide")

# Cada página é um arquivo em paginas/. Assim cada integrante do grupo é dono do seu.
paginas = [
    st.Page("paginas/dashboard.py",    title="Dashboard de Insights", icon="📊", default=True),
    st.Page("paginas/recomendador.py", title="Recomendador",          icon="🎯"),
    st.Page("paginas/assistente.py",   title="Assistente (Chatbot)",  icon="💬"),
]

st.navigation(paginas).run()
