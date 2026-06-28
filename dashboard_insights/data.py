"""
Camada de dados do Dashboard de Insights — Módulo 3 (PLN / FURB).

Carrega o CSV final da pipeline (`avaliacoes_praias_final.csv`), reconstrói as
colunas de tokens e deriva os campos usados pelo dashboard:
  - UF e cidade de origem (a partir de `location`)
  - data (`dt`, `ano`, `mes`) com parser para os formatos mistos
  - aspectos via ABSA (Gemini), agregados a partir do arquivo granular review × aspecto

Os parsers aqui são os mesmos validados na etapa de exploração.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import numpy as np
import pandas as pd

ARQUIVO_PADRAO = "avaliacoes_praias_final.csv"
ARQUIVO_ABSA = "avaliacoes_aspectos_gemini.csv"  # saída do ABSA (Gemini), review × aspecto


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
# Atenção: nome.title() colocaria os conectores em maiúscula ("Rio Grande Do Sul"),
# o que NÃO casa com o GeoJSON do mapa (que usa "Rio Grande do Sul") — assim RS, RJ,
# RN e MS sumiam do choropleth. Mantemos de/do/da/dos/das/e em minúsculo.
_CONECTORES = {"de", "do", "da", "dos", "das", "e"}


def _nome_proprio_estado(nome: str) -> str:
    return " ".join(p if p in _CONECTORES else p.capitalize() for p in nome.split())


NOME_POR_UF = {sigla: _nome_proprio_estado(nome) for nome, sigla in ESTADO_NOME.items()}


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
# Aspectos (ABSA do Gemini — matriz praia × aspecto)                           #
#                                                                              #
# Antes era um proxy por palavras-chave (flags asp_*). Agora lemos a saída real #
# do ABSA: o arquivo granular (uma linha por review × aspecto) é agregado sob   #
# demanda no recorte filtrado (dff), preservando a reação aos filtros de        #
# ano/nota/praia. A ligação com a base é a coluna `review_id` (ordem das        #
# linhas). Para voltar ao proxy, recuperar a versão anterior no histórico git.  #
# --------------------------------------------------------------------------- #
_absa_cache: pd.DataFrame | None = None

SENT_NEGATIVOS = {"negativo", "muito_negativo"}


def _carregar_absa() -> pd.DataFrame:
    """Lê o ABSA granular (review × aspecto) uma vez e mantém em cache."""
    global _absa_cache
    if _absa_cache is None:
        caminho = Path(__file__).resolve().parent / ARQUIVO_ABSA
        a = pd.read_csv(caminho)
        a = a[a["aspecto"].notna()].drop_duplicates(["review_id", "aspecto"])
        _absa_cache = a.reset_index(drop=True)
    return _absa_cache


def _taxonomia() -> tuple[list[str], dict[str, str]]:
    """Lista de aspectos (ordenada pelo nome legível) e mapa slug -> nome."""
    a = _carregar_absa()
    pares = (a[["aspecto", "aspecto_nome"]]
             .drop_duplicates()
             .sort_values("aspecto_nome"))
    return list(pares["aspecto"]), dict(zip(pares["aspecto"], pares["aspecto_nome"]))


def _absa_do_recorte(df: pd.DataFrame) -> pd.DataFrame:
    """ABSA limitado às reviews de `df`, com praia/rating vindos da base.

    Junta por `review_id`. Cada linha é uma menção a um aspecto numa review e
    carrega o rating geral e a praia da própria base — assim a agregação
    acompanha os filtros (ano/nota/praia) aplicados no dashboard.
    """
    absa = _carregar_absa()[
        ["review_id", "aspecto", "aspecto_nome", "nota_aspecto", "sentimento", "confianca"]
    ]
    base = df[["review_id", "praia", "rating"]]
    return absa.merge(base, on="review_id", how="inner")


def resumo_aspectos(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela global por aspecto: menções, % de avaliações, notas, lift e % negativas."""
    aspectos, rotulo = _taxonomia()
    sub = _absa_do_recorte(df)
    total = len(df)
    media_global = df["rating"].mean()
    linhas = []
    for asp in aspectos:
        m = sub[sub["aspecto"] == asp]
        if m.empty:
            continue
        linhas.append({
            "aspecto": rotulo[asp],
            "menções": int(len(m)),
            "% avaliações": round(len(m) / total * 100, 1) if total else 0.0,
            "nota do aspecto": round(m["nota_aspecto"].mean(), 2),
            "nota quando citado": round(m["rating"].mean(), 2),
            "lift (vs média)": round(m["rating"].mean() - media_global, 2),
            "% negativas": round(m["sentimento"].isin(SENT_NEGATIVOS).mean() * 100, 1),
            "confiança": round(m["confianca"].mean(), 2),
        })
    cols = ["aspecto", "menções", "% avaliações", "nota do aspecto",
            "nota quando citado", "lift (vs média)", "% negativas", "confiança"]
    out = pd.DataFrame(linhas, columns=cols)
    return out.sort_values("lift (vs média)") if not out.empty else out


def matriz_frequencia(df: pd.DataFrame) -> pd.DataFrame:
    """% de avaliações de cada praia que citam cada aspecto (reage aos filtros)."""
    aspectos, rotulo = _taxonomia()
    sub = _absa_do_recorte(df)
    tot = df.groupby("praia").size()
    cont = sub.groupby(["praia", "aspecto"]).size().unstack(fill_value=0)
    cont = cont.reindex(index=tot.index, columns=aspectos).fillna(0)
    freq = cont.div(tot, axis=0) * 100
    freq.columns = [rotulo[a] for a in aspectos]
    return freq


def matriz_lift(df: pd.DataFrame, min_mencoes: int = 10) -> pd.DataFrame:
    """Nota média de quem cita o aspecto MENOS a média da praia (vermelho = ponto fraco)."""
    aspectos, rotulo = _taxonomia()
    sub = _absa_do_recorte(df)
    linhas = {}
    for praia, g in df.groupby("praia"):
        base = g["rating"].mean()
        sp = sub[sub["praia"] == praia]
        linhas[praia] = {
            asp: (sp.loc[sp["aspecto"] == asp, "rating"].mean() - base)
            if (sp["aspecto"] == asp).sum() >= min_mencoes else np.nan
            for asp in aspectos
        }
    out = pd.DataFrame(linhas).T.reindex(columns=aspectos)
    out.columns = [rotulo[a] for a in aspectos]
    return out


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
    tokens reconstruídos, UF/cidade de origem, data e `review_id` (ligação com o ABSA).
    """
    df = pd.read_csv(fonte, encoding="utf-8-sig").reset_index(drop=True)

    # id estável = ordem das linhas (chave de ligação com o ABSA granular)
    df.insert(0, "review_id", range(1, len(df) + 1))

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

    # aspectos: agregados sob demanda a partir do ABSA (resumo_aspectos /
    # matriz_frequencia / matriz_lift), ligados pela coluna `review_id`.
    return df


# Fonte dos aspectos: ABSA Gemini (avaliacoes_aspectos_gemini.csv), ligado por review_id.
