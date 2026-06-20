# Como rodar o dashboard no Windows

## 1) Instalar o Python (uma única vez)
1. Baixe em https://www.python.org/downloads/
2. No instalador, **marque a caixa "Add Python to PATH"** antes de clicar em *Install Now*. (passo mais importante!)

## 2) Juntar os arquivos numa pasta
Na **mesma pasta**, deixe:
- `app.py`, `data.py`, `requirements.txt`, `rodar_dashboard.bat`
- `avaliacoes_praias_final.csv`  ← baixe do Drive (pasta `dados/finais`)

## 3) Rodar (jeito fácil)
- Dê **dois cliques** em **`rodar_dashboard.bat`**.
- Na 1ª vez ele instala as dependências (demora um pouco) e abre o app no navegador: **http://localhost:8501**
- Para **parar**: feche a janela preta.

## Jeito manual (terminal), se preferir
1. Abra a pasta no Explorer, clique na barra de endereço, digite `cmd` e Enter.
2. `python -m pip install -r requirements.txt`
3. `python -m streamlit run app.py`

## Problemas comuns
- **"'python' não é reconhecido"** → o Python não entrou no PATH. Reinstale marcando *Add Python to PATH* (ou use `py` no lugar de `python`).
- **"'streamlit' não é reconhecido"** → use sempre `python -m streamlit run app.py` (não só `streamlit`).
- **App abre pedindo o CSV** → coloque `avaliacoes_praias_final.csv` na pasta, ou envie pela barra lateral do próprio app.
- **Quero parar o app** → feche a janela preta (ou Ctrl+C nela).
