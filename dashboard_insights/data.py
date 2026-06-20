"""
Camada de dados do Dashboard de Insights — Módulo 3 (PLN / FURB).

Carrega o CSV final da pipeline (`avaliacoes_praias_final.csv`), reconstrói as
colunas de tokens e deriva os campos usados pelo dashboard:
  - UF e cidade de origem (a partir de `location`)
  - data (`dt`, `ano`, `mes`) com parser para os formatos mistos
  - flags de aspecto (proxy por palavras-chave) até o ABSA do Daniel ficar pronto

Os parsers aqui são os mesmos validados na etapa de exploração.
"""
from __future__ import annotations

import ast
import re

import numpy as np
import pandas as pd

ARQUIVO_PADRAO = "avaliacoes_praias_final.csv"


# --------------------------------------------------------------------------- #
# Tokens                                                                       #
# --------------------------------------------------------------------------- #
def para_lista(v):
    """Reconstrói uma lista de tokens salva como string no CSV."""
    if isinstance(v, list):
        return v
    if pd.isna(v):
        return []
    v = str(v).strip()
    if not v:
        return []
    try:
        out = ast.literal_eval(v)
        return out if isinstance(out, list) else []
    except (ValueError, SyntaxError):
        return v.split()


COLS_TOKENS_SUFIXOS = ("_tokens", "_normalized", "_stopwords", "_stemming", "_lemmatized")


# --------------------------------------------------------------------------- #
# Origem (location -> UF / cidade)                                             #
# --------------------------------------------------------------------------- #
UF = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}
ESTADO_NOME = {
    "acre": "AC", "alagoas": "AL", "amapá": "AP", "amazonas": "AM", "bahia": "BA",
    "ceará": "CE", "distrito federal": "DF", "espírito santo": "ES", "goiás": "GO",
    "maranhão": "MA", "mato grosso": "MT", "mato grosso do sul": "MS",
    "minas gerais": "MG", "pará": "PA", "paraíba": "PB", "paraná": "PR",
    "pernambuco": "PE", "piauí": "PI", "rio de janeiro": "RJ",
    "rio grande do norte": "RN", "rio grande do sul": "RS", "rondônia": "RO",
    "roraima": "RR", "santa catarina": "SC", "são paulo": "SP", "sergipe": "SE",
    "tocantins": "TO",
}
NOME_POR_UF = {sigla: nome.title() for nome, sigla in ESTADO_NOME.items()}


def parse_uf(s):
    """Extrai a UF de um campo `location`. Retorna sigla, 'EXTERIOR/OUTRO' ou None."""
    if not isinstance(s, str) or not s.strip():
        return None
    partes = [p.strip() for p in s.split(",")]
    ult = partes[-1]
    if ult.upper() in UF:
        return ult.upper()
    if ult.lower() in ESTADO_NOME:
        return ESTADO_NOME[ult.lower()]
    if s.strip().lower() in ESTADO_NOME:
        return ESTADO_NOME[s.strip().lower()]
    return "EXTERIOR/OUTRO"


def parse_cidade(s):
    if not isinstance(s, str) or not s.strip():
        return None
    return s.split(",")[0].strip()


# --------------------------------------------------------------------------- #
# Data (formatos mistos)                                                       #
# --------------------------------------------------------------------------- #
MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}


def parse_data(s):
    """Converte os formatos de data da base ('22 de abril de 2025', '17/01/2017')."""
    if not isinstance(s, str):
        return pd.NaT
    s = s.strip().lower()
    m = re.match(r"^(\d{1,2}) de ([a-zç]+) de (\d{4})$", s)
    if m and m.group(2) in MESES:
        return pd.Timestamp(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        return pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.match(r"^([a-zç]+) de (\d{4})$", s)
    if m and m.group(1) in MESES:
        return pd.Timestamp(int(m.group(2)), MESES[m.group(1)], 1)
    return pd.NaT


# --------------------------------------------------------------------------- #
# Aspectos (proxy por palavras-chave — substituir pelo ABSA quando pronto)     #
# --------------------------------------------------------------------------- #
ASPECTOS = {
    "limpeza":   {"limpo", "limpeza", "sujo", "sujeira", "lixo", "poluir", "poluição", "poluído"},
    "segurança": {"seguro", "segurança", "perigoso", "perigo", "assalto", "roubo", "violência", "tranquilo"},
    "estrutura": {"estrutura", "infraestrutura", "banheiro", "quiosque", "restaurante", "bar", "estacionamento", "chuveiro"},
    "mar/água":  {"mar", "água", "onda", "agitado", "calmo", "correnteza", "maré", "azul"},
    "acesso":    {"acesso", "acessível", "escada", "trilha", "difícil", "fácil", "chegar", "estrada"},
    "beleza":    {"bonito", "lindo", "belo", "paisagem", "vista", "natureza", "maravilhoso", "paradisíaco"},
}


def _tokens_review(row):
    """Conjunto de tokens (lematizados) em minúsculo, título + texto."""
    return {w.lower() for w in set(row["text_lemmatized"]) | set(row["title_lemmatized"])}


def adicionar_flags_aspecto(df: pd.DataFrame) -> pd.DataFrame:
    """Cria as colunas booleanas `asp_<aspecto>` indicando menção ao aspecto."""
    tok = df.apply(_tokens_review, axis=1)
    for asp, kws in ASPECTOS.items():
        df["asp_" + asp] = tok.apply(lambda t, kws=kws: len(t & kws) > 0)
    return df


def resumo_aspectos(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela: menções, % avaliações, nota quando citado, lift e % de negativas."""
    media_global = df["rating"].mean()
    linhas = []
    for asp in ASPECTOS:
        col = "asp_" + asp
        cit = df[df[col]]
        linhas.append({
            "aspecto": asp,
            "menções": int(df[col].sum()),
            "% avaliações": round(df[col].mean() * 100, 1),
            "nota quando citado": round(cit["rating"].mean(), 2),
            "lift (vs média)": round(cit["rating"].mean() - media_global, 2),
            "% negativas (<=2)": round((cit["rating"] <= 2).mean() * 100, 1),
        })
    return pd.DataFrame(linhas).sort_values("lift (vs média)")


def matriz_frequencia(df: pd.DataFrame) -> pd.DataFrame:
    """% de avaliações de cada praia que citam cada aspecto."""
    freq = df.groupby("praia")[["asp_" + a for a in ASPECTOS]].mean() * 100
    freq.columns = list(ASPECTOS.keys())
    return freq


def matriz_lift(df: pd.DataFrame, min_mencoes: int = 10) -> pd.DataFrame:
    """Nota de quem cita o aspecto MENOS a média da praia (vermelho = ponto fraco)."""
    linhas = {}
    for praia, g in df.groupby("praia"):
        base = g["rating"].mean()
        linhas[praia] = {
            asp: (g.loc[g["asp_" + asp], "rating"].mean() - base)
            if g["asp_" + asp].sum() >= min_mencoes else np.nan
            for asp in ASPECTOS
        }
    return pd.DataFrame(linhas).T[list(ASPECTOS.keys())]


# --------------------------------------------------------------------------- #
# Nuvem de palavras                                                            #
# --------------------------------------------------------------------------- #
GENERICAS = {
    "praia", "mar", "dia", "lugar", "ser", "ir", "ficar", "ter", "fazer", "ver",
    "ano", "vez", "gente", "tudo", "todo", "pra", "aqui", "lá", "onde", "bem",
    "muito", "mais", "só", "também", "já", "ainda", "bom", "ótimo", "legal",
    "ótima", "bonito", "lindo",
}


def stopwords_dominio(df: pd.DataFrame) -> set:
    """Nomes das praias + termos genéricos, para limpar a nuvem."""
    nomes = set()
    for p in df["praia"].unique():
        nomes |= set(str(p).replace("praia_", "").split("_"))
    return nomes | GENERICAS


def texto_nuvem(df: pd.DataFrame, praia: str, stop: set) -> str:
    """Concatena os tokens lematizados de uma praia, sem stopwords de domínio."""
    toks = []
    for t in df.loc[df["praia"] == praia, "text_lemmatized"]:
        toks += [w for w in t if w.lower() not in stop and len(w) > 2]
    return " ".join(toks)


# --------------------------------------------------------------------------- #
# Carga                                                                        #
# --------------------------------------------------------------------------- #
def carregar_dados(fonte) -> pd.DataFrame:
    """
    Lê o CSV (caminho ou buffer) e devolve o DataFrame já enriquecido:
    tokens reconstruídos, UF/cidade de origem, data e flags de aspecto.
    """
    df = pd.read_csv(fonte, encoding="utf-8-sig")

    # tokens (listas salvas como string)
    for c in [c for c in df.columns if c.endswith(COLS_TOKENS_SUFIXOS)]:
        df[c] = df[c].apply(para_lista)

    # origem
    df["uf"] = df["location"].apply(parse_uf)
    df["cidade_origem"] = df["location"].apply(parse_cidade)
    df["origem_preenchida"] = df["location"].fillna("").str.strip().ne("")

    # data
    df["dt"] = df["date"].apply(parse_data)
    df["ano"] = df["dt"].dt.year
    df["mes"] = df["dt"].dt.month

    # aspectos (proxy)
    df = adicionar_flags_aspecto(df)
    return df
