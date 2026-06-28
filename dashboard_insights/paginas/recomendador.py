"""
Página: Recomendador de Praias (em construção).

Placeholder — o módulo será desenvolvido pelo time. Esta página é o ponto de
entrada já reservado no menu.

Contrato sugerido pra quem for implementar:
  - Entrada: preferências do usuário (aspectos que importam, origem, época).
  - Base: reaproveitar `data.py` (avaliacoes_praias_final.csv) e o ABSA
    (`praia_aspecto_scores_gemini.csv` / `avaliacoes_aspectos_gemini.csv`),
    rankeando as praias pela aderência às preferências.
  - Saída: lista de praias recomendadas + justificativa (notas por aspecto).
Para importar o módulo de dados aqui, use o mesmo padrão das outras páginas:
    import sys; from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    import data as dados
"""
import streamlit as st

st.title("🎯 Recomendador de Praias")
st.info("🚧 Módulo em construção. Esta página já está reservada no menu lateral.")

st.markdown(
    "Aqui o usuário vai informar o que procura (ex.: praia tranquila, boa para "
    "crianças, com boa infraestrutura) e receber praias recomendadas, com base "
    "nas avaliações e nas notas por aspecto do ABSA."
)

# Mock só pra ilustrar o layout — não recomenda nada ainda.
with st.form("mock_recomendador"):
    st.multiselect(
        "O que é mais importante pra você?",
        ["Beleza natural", "Mar / banho", "Tranquilidade", "Família / crianças",
         "Infraestrutura", "Limpeza", "Acesso / estacionamento", "Comércio / serviços",
         "Custo-benefício", "Segurança"],
        default=["Beleza natural", "Tranquilidade"],
    )
    st.form_submit_button("Recomendar (em breve)", disabled=True)
