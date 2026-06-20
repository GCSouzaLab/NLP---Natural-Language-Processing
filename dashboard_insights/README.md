# Dashboard de Insights — Módulo 3 (PLN / FURB)

Dashboard interativo das avaliações de praias de Santa Catarina (TripAdvisor).
Esqueleto em **Streamlit + Plotly**, construído sobre o arquivo final da pipeline
do grupo (`avaliacoes_praias_final.csv`).

## Componentes
1. **Origem** — de onde vêm os turistas (UF, mapa por estado, cidades) — campo `location`
2. **Evolução temporal** — volume e nota média por ano, sazonalidade — campo `date`
3. **Aspectos** — ranking de praias + proxy de aspectos (frequência, *lift*, % de negativas)
4. **Nuvem de palavras** — por praia, com opção de separar positivas/negativas

Filtros globais (barra lateral): período (ano), praias e notas.

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```
Coloque o `avaliacoes_praias_final.csv` nesta pasta **ou** envie pela barra lateral
quando o app abrir.

## Estrutura
- `app.py` — interface (filtros + 4 abas)
- `data.py` — carga, parsers (UF, data, tokens) e cálculo dos aspectos
- `requirements.txt` — dependências

## Sobre o proxy de aspectos
O ranking de aspectos usa um **proxy por palavras-chave** nos tokens lematizados,
enquanto a matriz praia × aspecto do ABSA (Daniel) não fica pronta. Quando ela
existir, basta trocar as funções `resumo_aspectos` / `matriz_frequencia` /
`matriz_lift` em `data.py` pela saída real do ABSA.
