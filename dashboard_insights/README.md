# Dashboard de Insights (PLN / FURB)
Dashboard interativo das avaliações de praias de Santa Catarina (TripAdvisor).
Esqueleto em **Streamlit + Plotly**, construído sobre o arquivo final da pipeline
do grupo (`avaliacoes_praias_final.csv`).

## Componentes
1. **Origem** — de onde vêm os turistas (UF, mapa por estado, cidades) — campo `location`
2. **Evolução temporal** — volume e nota média por ano, sazonalidade — campo `date`
3. **Aspectos** — ranking de praias + proxy de aspectos (frequência, *lift*, % de negativas)
4. **Nuvem de palavras** — por praia, com opção de separar positivas/negativas
5. **Assistente de Praias** — chatbot RAG que responde perguntas em linguagem natural citando avaliações reais

Filtros globais (barra lateral): período (ano), praias e notas.

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```


## Estrutura
- `app.py` — interface (filtros + 4 abas + chatbot na sidebar)
- `data.py` — carga, parsers (UF, data, tokens) e cálculo dos aspectos
- `chatbot_tab.py` — módulo do assistente RAG (busca TF-IDF + Gemini)
- `requirements.txt` — dependências
- `.streamlit/secrets.toml` — chave da API Gemini (não versionado)

## Assistente de Praias (RAG + Chatbot)

O chatbot responde perguntas como *"quero praia tranquila, com boa infraestrutura e boa para criança"* em três etapas:

1. **Busca semântica** — recupera os reviews mais relevantes via TF-IDF nos tokens lematizados
2. **Notas por aspecto** — consulta a matriz praia × aspecto do ABSA
3. **Geração de resposta** — o Gemini monta a resposta citando trechos reais das avaliações

### Configuração da API Gemini

Obtenha uma chave em [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) e adicione ao arquivo `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "sua_chave_aqui"
```

Ou defina como variável de ambiente antes de rodar:
```bash
# Windows
set GEMINI_API_KEY=sua_chave_aqui

# Linux / Mac
export GEMINI_API_KEY=sua_chave_aqui
```

## Sobre o proxy de aspectos
O ranking de aspectos usa um **proxy por palavras-chave** nos tokens lematizados,
enquanto a matriz praia × aspecto do ABSA não fica pronta. Quando ela
existir, basta trocar as funções `resumo_aspectos` / `matriz_frequencia` /
`matriz_lift` em `data.py` pela saída real do ABSA.
