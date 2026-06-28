"""
Página: Assistente / Chatbot RAG (Gabriel).

Expõe, em página própria, o render_chatbot() definido em chatbot_tab.py
(o módulo do Gabriel fica intacto, só ganhou um parâmetro opcional de altura).

Importante: o chat é renderizado no nível da página (NÃO dentro de st.columns),
porque dentro de coluna o st.chat_input perde a fixação no rodapé e a gente
precisa rolar pra digitar. Para deixar estreito/centralizado sem perder isso,
limitamos a largura por CSS (.block-container) e reduzimos o espaço do topo.
"""
import sys
from pathlib import Path

# garante que `import chatbot_tab` (na pasta de cima) funcione ao rodar como página
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

from chatbot_tab import render_chatbot

# Página mais estreita e com menos espaço em cima; o st.chat_input continua fixo no rodapé.
st.markdown(
    """
    <style>
    .block-container, [data-testid="stMainBlockContainer"] {
        max-width: 860px;
        margin: 0 auto;
        padding-top: 2.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💬 Assistente de Praias")
st.caption("Chatbot com RAG · busca semântica nas avaliações + notas por aspecto do ABSA")

render_chatbot(altura=340)
