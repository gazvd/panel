"""
Módulo de Comparativo de Desempenho entre Eleições
Permite comparar a evolução temporal de candidatos e partidos ao longo de diferentes pleitos,
com opção de confrontar simultaneamente dois candidatos (até 4 pleitos no total).
Suporta agregação em todos os níveis territoriais: Regiões de Desenvolvimento, Municípios,
Zonas Eleitorais, Bairros e Colégios Eleitorais.
"""

import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from config import (
    PATH_RESULTADOS,
    PATH_LOCAIS_PARQUET,
    PRESIDENTES_NOMES,
    REGIOES_DESENVOLVIMENTO,
    CORES_PARTIDOS,
    fmt_int,
    fmt_pct,
    wrap_label
)
from modules.geo_loader import load_municipios_gdf


# --- CONSULTAS OTIMIZADAS EM DUCKDB ---

@st.cache_data(ttl=3600)
def get_opcoes_candidatos_pleito(ano: int, turno: int, cargo: str, id_municipio: int = None):
    """Retorna os candidatos ou legendas disponíveis para determinado ano, turno e cargo."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    where_clauses = [f"ano = {ano}", f"turno = {turno}", f"cargo = '{cargo}'"]
    if id_municipio:
        where_clauses.append(f"id_municipio = {id_municipio}")
    where_str = " AND ".join(where_clauses)

    if cargo == "presidente":
        q = f"""
            SELECT sigla_partido, SUM(total_votos) as total_votos
            FROM '{res_path}'
            WHERE {where_str} AND sigla_partido IS NOT NULL
            GROUP BY sigla_partido
            ORDER BY total_votos DESC
        """
        df = con.execute(q).df()
        if len(df) == 0:
            return pd.DataFrame(columns=['numero_candidato', 'nome_urna', 'sigla_partido', 'total_votos', 'label'])
        df['numero_candidato'] = None
        df['nome_urna'] = df['sigla_partido'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})"))
        df['label'] = df.apply(lambda r: f"{r['nome_urna']} ({r['sigla_partido']}) - {fmt_int(r['total_votos'])} votos", axis=1)
        return df
    else:
        q = f"""
            SELECT numero_candidato, nome_urna, sigla_partido, SUM(total_votos) as total_votos
            FROM '{res_path}'
            WHERE {where_str} AND numero_candidato IS NOT NULL
            GROUP BY numero_candidato, nome_urna, sigla_partido
            ORDER BY total_votos DESC
            LIMIT 250
        """
        df = con.execute(q).df()
        if len(df) == 0:
            return pd.DataFrame(columns=['numero_candidato', 'nome_urna', 'sigla_partido', 'total_votos', 'label'])
        df['label'] = df.apply(lambda r: f"{r['nome_urna']} ({r['sigla_partido']}) - {fmt_int(r['total_votos'])} votos", axis=1)
        return df


@st.cache_data(ttl=3600)
def get_votos_candidato_rd(ano: int, turno: int, cargo: str, numero_candidato: int = None, sigla_partido: str = None):
    """Calcula votos e % de válidos por Região de Desenvolvimento."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    gdf_mun = load_municipios_gdf()
    df_m = gdf_mun[['CD_MUN', 'REGIAO_DESENVOLVIMENTO']].copy()
    df_m['id_municipio'] = df_m['CD_MUN'].astype(int)
    con.register('mun_map_rd', df_m[['id_municipio', 'REGIAO_DESENVOLVIMENTO']])

    cand_filter = f"r.numero_candidato = {int(numero_candidato)}" if numero_candidato is not None else f"r.sigla_partido = '{sigla_partido}'"

    q = f"""
    WITH total_rd AS (
        SELECT m.REGIAO_DESENVOLVIMENTO as territorio, SUM(r.total_votos) as total_validos
        FROM '{res_path}' r
        JOIN mun_map_rd m ON r.id_municipio = m.id_municipio
        WHERE r.ano = {ano} AND r.turno = {turno} AND r.cargo = '{cargo}'
        GROUP BY m.REGIAO_DESENVOLVIMENTO
    ),
    cand_rd AS (
        SELECT m.REGIAO_DESENVOLVIMENTO as territorio, SUM(r.total_votos) as votos
        FROM '{res_path}' r
        JOIN mun_map_rd m ON r.id_municipio = m.id_municipio
        WHERE r.ano = {ano} AND r.turno = {turno} AND r.cargo = '{cargo}' AND {cand_filter}
        GROUP BY m.REGIAO_DESENVOLVIMENTO
    )
    SELECT t.territorio,
           COALESCE(c.votos, 0) as votos,
           t.total_validos,
           ROUND(100.0 * COALESCE(c.votos, 0) / NULLIF(t.total_validos, 0), 2) as pct_votos
    FROM total_rd t
    LEFT JOIN cand_rd c ON t.territorio = c.territorio
    ORDER BY votos DESC
    """
    return con.execute(q).df()


@st.cache_data(ttl=3600)
def get_votos_candidato_municipios(ano: int, turno: int, cargo: str, numero_candidato: int = None, sigla_partido: str = None):
    """Calcula votos e % de válidos por Município."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    gdf_mun = load_municipios_gdf()
    df_m = gdf_mun[['CD_MUN', 'NM_MUN']].copy()
    df_m['id_municipio'] = df_m['CD_MUN'].astype(int)
    con.register('mun_map_nomes', df_m[['id_municipio', 'NM_MUN']])

    cand_filter = f"r.numero_candidato = {int(numero_candidato)}" if numero_candidato is not None else f"r.sigla_partido = '{sigla_partido}'"

    q = f"""
    WITH total_mun AS (
        SELECT r.id_municipio, SUM(r.total_votos) as total_validos
        FROM '{res_path}' r
        WHERE r.ano = {ano} AND r.turno = {turno} AND r.cargo = '{cargo}'
        GROUP BY r.id_municipio
    ),
    cand_mun AS (
        SELECT r.id_municipio, SUM(r.total_votos) as votos
        FROM '{res_path}' r
        WHERE r.ano = {ano} AND r.turno = {turno} AND r.cargo = '{cargo}' AND {cand_filter}
        GROUP BY r.id_municipio
    )
    SELECT m.NM_MUN as territorio,
           t.id_municipio,
           COALESCE(c.votos, 0) as votos,
           t.total_validos,
           ROUND(100.0 * COALESCE(c.votos, 0) / NULLIF(t.total_validos, 0), 2) as pct_votos
    FROM total_mun t
    JOIN mun_map_nomes m ON t.id_municipio = m.id_municipio
    LEFT JOIN cand_mun c ON t.id_municipio = c.id_municipio
    ORDER BY votos DESC
    """
    return con.execute(q).df()


@st.cache_data(ttl=3600)
def get_votos_candidato_zonas(ano: int, turno: int, cargo: str, id_municipio: int, numero_candidato: int = None, sigla_partido: str = None):
    """Calcula votos e % de válidos por Zona Eleitoral dentro do município."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    cand_filter = f"r.numero_candidato = {int(numero_candidato)}" if numero_candidato is not None else f"r.sigla_partido = '{sigla_partido}'"

    q = f"""
    WITH total_zona AS (
        SELECT r.zona, SUM(r.total_votos) as total_validos
        FROM '{res_path}' r
        WHERE r.ano = {ano} AND r.turno = {turno} AND r.cargo = '{cargo}' AND r.id_municipio = {id_municipio}
        GROUP BY r.zona
    ),
    cand_zona AS (
        SELECT r.zona, SUM(r.total_votos) as votos
        FROM '{res_path}' r
        WHERE r.ano = {ano} AND r.turno = {turno} AND r.cargo = '{cargo}' AND r.id_municipio = {id_municipio} AND {cand_filter}
        GROUP BY r.zona
    )
    SELECT 'Zona ' || t.zona as territorio,
           t.zona,
           COALESCE(c.votos, 0) as votos,
           t.total_validos,
           ROUND(100.0 * COALESCE(c.votos, 0) / NULLIF(t.total_validos, 0), 2) as pct_votos
    FROM total_zona t
    LEFT JOIN cand_zona c ON t.zona = c.zona
    ORDER BY t.zona ASC
    """
    return con.execute(q).df()


@st.cache_data(ttl=3600)
def get_votos_candidato_bairros(ano: int, turno: int, cargo: str, id_municipio: int, nome_municipio: str, numero_candidato: int = None, sigla_partido: str = None):
    """Calcula votos e % de válidos por Bairro/Distrito no município selecionado."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    loc_path = str(PATH_LOCAIS_PARQUET).replace("\\", "/")
    cand_filter = f"r.numero_candidato = {int(numero_candidato)}" if numero_candidato is not None else f"r.sigla_partido = '{sigla_partido}'"
    mun_clean = nome_municipio.upper().strip()

    q = f"""
    WITH locais_mun AS (
        SELECT DISTINCT zona, secao, UPPER(TRIM(bairro)) as bairro
        FROM '{loc_path}'
        WHERE UPPER(municipio) = '{mun_clean}' AND bairro IS NOT NULL AND TRIM(bairro) != ''
    ),
    votos_sec AS (
        SELECT r.zona, r.secao,
               SUM(r.total_votos) as total_sec,
               SUM(CASE WHEN {cand_filter} THEN r.total_votos ELSE 0 END) as votos_cand
        FROM '{res_path}' r
        WHERE r.ano = {ano} AND r.turno = {turno} AND r.cargo = '{cargo}' AND r.id_municipio = {id_municipio}
        GROUP BY r.zona, r.secao
    ),
    joined AS (
        SELECT l.bairro as territorio,
               v.votos_cand,
               v.total_sec
        FROM locais_mun l
        JOIN votos_sec v ON l.zona = v.zona AND l.secao = v.secao
    )
    SELECT territorio,
           SUM(votos_cand) as votos,
           SUM(total_sec) as total_validos,
           ROUND(100.0 * SUM(votos_cand) / NULLIF(SUM(total_sec), 0), 2) as pct_votos
    FROM joined
    GROUP BY territorio
    ORDER BY votos DESC
    """
    return con.execute(q).df()


@st.cache_data(ttl=3600)
def get_votos_candidato_locais(ano: int, turno: int, cargo: str, id_municipio: int, nome_municipio: str, numero_candidato: int = None, sigla_partido: str = None):
    """Calcula votos e % de válidos por Colégio Eleitoral (Local de Votação)."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    loc_path = str(PATH_LOCAIS_PARQUET).replace("\\", "/")
    cand_filter = f"r.numero_candidato = {int(numero_candidato)}" if numero_candidato is not None else f"r.sigla_partido = '{sigla_partido}'"
    mun_clean = nome_municipio.upper().strip()

    q = f"""
    WITH locais_mun AS (
        SELECT DISTINCT zona, secao, id_local, nome_local, UPPER(TRIM(bairro)) as bairro
        FROM '{loc_path}'
        WHERE UPPER(municipio) = '{mun_clean}'
    ),
    votos_sec AS (
        SELECT r.zona, r.secao,
               SUM(r.total_votos) as total_sec,
               SUM(CASE WHEN {cand_filter} THEN r.total_votos ELSE 0 END) as votos_cand
        FROM '{res_path}' r
        WHERE r.ano = {ano} AND r.turno = {turno} AND r.cargo = '{cargo}' AND r.id_municipio = {id_municipio}
        GROUP BY r.zona, r.secao
    ),
    joined AS (
        SELECT l.nome_local as territorio,
               l.bairro,
               v.votos_cand,
               v.total_sec
        FROM locais_mun l
        JOIN votos_sec v ON l.zona = v.zona AND l.secao = v.secao
    )
    SELECT territorio,
           bairro,
           SUM(votos_cand) as votos,
           SUM(total_sec) as total_validos,
           ROUND(100.0 * SUM(votos_cand) / NULLIF(SUM(total_sec), 0), 2) as pct_votos
    FROM joined
    GROUP BY territorio, bairro
    ORDER BY votos DESC
    """
    return con.execute(q).df()


# --- HELPER DE INTERFACE: SELETOR DE CANDIDATO/PLEITO ---

def _render_seletor_pleito_candidato(label_prefix: str, key_prefix: str, df_meta: pd.DataFrame, default_ano: int, default_cargo: str, default_turno: int = 1):
    """Renderiza controles para seleção de Ano, Cargo, Turno e Candidato."""
    c1, c2, c3 = st.columns([1, 1.3, 0.9])
    
    anos_disp = sorted(df_meta['ano'].unique(), reverse=True)
    idx_ano = anos_disp.index(default_ano) if default_ano in anos_disp else 0
    with c1:
        ano = st.selectbox(f"Ano ({label_prefix}):", anos_disp, index=idx_ano, key=f"{key_prefix}_ano")

    cargos_disp = sorted(df_meta[df_meta['ano'] == ano]['cargo'].unique())
    idx_cargo = cargos_disp.index(default_cargo) if default_cargo in cargos_disp else 0
    with c2:
        cargo = st.selectbox(f"Cargo ({label_prefix}):", cargos_disp, index=idx_cargo, key=f"{key_prefix}_cargo")

    turnos_disp = sorted(df_meta[(df_meta['ano'] == ano) & (df_meta['cargo'] == cargo)]['turno'].unique())
    idx_turno = turnos_disp.index(default_turno) if default_turno in turnos_disp else 0
    with c3:
        turno = st.selectbox(f"Turno ({label_prefix}):", turnos_disp, index=idx_turno, key=f"{key_prefix}_turno")

    # Obter lista de candidatos para o pleito
    df_cands = get_opcoes_candidatos_pleito(ano, turno, cargo)
    
    if len(df_cands) == 0:
        st.warning(f"Nenhum candidato encontrado para {ano} • {cargo.upper()} • {turno}º Turno.")
        return None

    cands_labels = df_cands['label'].tolist()
    cand_idx = st.selectbox(
        f"Candidato / Legenda ({label_prefix}):",
        range(len(cands_labels)),
        format_func=lambda i: cands_labels[i],
        key=f"{key_prefix}_cand"
    )

    escolhido = df_cands.iloc[cand_idx].to_dict()
    return {
        "ano": ano,
        "turno": turno,
        "cargo": cargo,
        "numero_candidato": escolhido.get("numero_candidato"),
        "sigla_partido": escolhido.get("sigla_partido"),
        "nome_urna": escolhido.get("nome_urna"),
        "label_completo": escolhido.get("label"),
        "label_curto": f"{escolhido.get('nome_urna')} ({ano})"
    }


# --- FUNÇÃO PRINCIPAL DE RENDERIZAÇÃO DA ABA ---

def render_tab_comparativo_eleicoes(df_meta: pd.DataFrame, df_mun_map: pd.DataFrame):
    """Renderiza a aba de Comparativo de Desempenho entre Eleições."""
    st.markdown("### ⚖️ Comparativo de Desempenho entre Eleições")
    st.caption(
        "Analise a evolução de um candidato entre dois pleitos (ex: **João Campos 2020 vs 2024**, ou **Danilo Cabral 2022 vs João Campos 2026**). "
        "Você também pode habilitar a comparação simultânea com um segundo candidato ou oponente para avaliar ganhos e perdas territoriais."
    )

    # --- 1. CONFIGURAÇÃO DOS CANDIDATOS (SLOT A E SLOT B) ---
    c_card_a, c_card_b = st.columns(2)

    with c_card_a:
        st.markdown("#### 👤 Candidato A (Evolução Temporal)")
        st.caption("Selecione os dois momentos históricos do candidato (ou seus representantes de legenda).")
        
        ca1, ca2 = st.columns(2)
        with ca1:
            st.markdown("##### 📅 Pleito 1 (Base)")
            slot_a1 = _render_seletor_pleito_candidato(
                label_prefix="A1",
                key_prefix="comp_a1",
                df_meta=df_meta,
                default_ano=2020,
                default_cargo="prefeito",
                default_turno=1
            )
        with ca2:
            st.markdown("##### 📅 Pleito 2 (Comparação)")
            slot_a2 = _render_seletor_pleito_candidato(
                label_prefix="A2",
                key_prefix="comp_a2",
                df_meta=df_meta,
                default_ano=2024,
                default_cargo="prefeito",
                default_turno=1
            )

    with c_card_b:
        st.markdown("#### 👥 Candidato B (Opcional)")
        ativar_b = st.checkbox("Ativar comparação com Candidato B", value=False, key="check_ativar_cand_b")
        
        slot_b1 = None
        slot_b2 = None
        if ativar_b:
            st.caption("Selecione os dois momentos históricos do segundo candidato para confronto direto.")
            cb1, cb2 = st.columns(2)
            with cb1:
                st.markdown("##### 📅 Pleito 1 (Base B)")
                slot_b1 = _render_seletor_pleito_candidato(
                    label_prefix="B1",
                    key_prefix="comp_b1",
                    df_meta=df_meta,
                    default_ano=2020,
                    default_cargo="prefeito",
                    default_turno=1
                )
            with cb2:
                st.markdown("##### 📅 Pleito 2 (Comparação B)")
                slot_b2 = _render_seletor_pleito_candidato(
                    label_prefix="B2",
                    key_prefix="comp_b2",
                    df_meta=df_meta,
                    default_ano=2024,
                    default_cargo="prefeito",
                    default_turno=1
                )
        else:
            st.info("💡 Marque a opção acima caso queira comparar o crescimento de A contra um adversário político (ex: PSB vs PL / PT vs PSDB).")

    if not slot_a1 or not slot_a2:
        st.warning("Por favor, selecione os candidatos para os pleitos 1 e 2 do Candidato A.")
        return

    st.markdown("---")

    # --- 2. CONFIGURAÇÃO TERRITORIAL E FILTROS ---
    st.markdown("#### 🗺️ Granularidade Territorial & Filtros")

    c_geo1, c_geo2, c_geo3 = st.columns([1.2, 1.4, 1.4])

    with c_geo1:
        nivel_geo = st.selectbox(
            "Nível de Visualização Geográfica:",
            [
                "Regiões de Desenvolvimento (12)",
                "Municípios (185)",
                "Zonas Eleitorais",
                "Bairros & Distritos",
                "Colégios Eleitorais"
            ],
            index=2, # Default Zonas Eleitorais para análise rápida
            key="sel_nivel_geo_comp"
        )

    # Obter lista de municípios e índice padrão do Recife
    muns_nomes = sorted(df_mun_map['NM_MUN'].unique().tolist())
    recife_idx = muns_nomes.index("Recife") if "Recife" in muns_nomes else 0

    filtro_rd_especifica = None
    mun_nome_escolhido = None
    cd_mun_escolhido = None
    filtro_zona_especifica = None
    filtro_bairro_especifico = None
    busca_colegio = ""

    if nivel_geo == "Regiões de Desenvolvimento (12)":
        with c_geo2:
            opcoes_rd = ["⭐ Todas as 12 Regiões"] + REGIOES_DESENVOLVIMENTO
            rd_escolhida = st.selectbox("Filtrar Região:", opcoes_rd, index=0, key="sel_rd_comp")
            if rd_escolhida != "⭐ Todas as 12 Regiões":
                filtro_rd_especifica = rd_escolhida

    elif nivel_geo == "Municípios (185)":
        with c_geo2:
            opcoes_rd_mun = ["⭐ Todas as Regiões"] + REGIOES_DESENVOLVIMENTO
            rd_filtro_muns = st.selectbox("Filtrar por Região:", opcoes_rd_mun, index=0, key="sel_rd_filtro_mun_comp")
        with c_geo3:
            muns_da_rd = muns_nomes
            if rd_filtro_muns != "⭐ Todas as Regiões":
                muns_da_rd = sorted(df_mun_map[df_mun_map['REGIAO_DESENVOLVIMENTO'] == rd_filtro_muns]['NM_MUN'].unique().tolist())
            opcoes_mun_especifico = ["⭐ Todos os Municípios"] + muns_da_rd
            mun_especifico = st.selectbox("Filtrar Município Específico:", opcoes_mun_especifico, index=0, key="sel_mun_esp_comp")
            if mun_especifico != "⭐ Todos os Municípios":
                mun_nome_escolhido = mun_especifico

    elif nivel_geo == "Zonas Eleitorais":
        with c_geo2:
            mun_nome_escolhido = st.selectbox("Escolha o Município:", muns_nomes, index=recife_idx, key="sel_mun_zonas_comp")
            info_mun = df_mun_map[df_mun_map['NM_MUN'] == mun_nome_escolhido].iloc[0]
            cd_mun_escolhido = int(info_mun['CD_MUN'])
        with c_geo3:
            # Consulta zonas disponíveis no município
            df_z_disp = get_votos_candidato_zonas(slot_a2['ano'], slot_a2['turno'], slot_a2['cargo'], cd_mun_escolhido, slot_a2['numero_candidato'], slot_a2['sigla_partido'])
            zonas_list = sorted(df_z_disp['zona'].unique().tolist()) if len(df_z_disp) > 0 else []
            opcoes_zonas = ["⭐ Todas as Zonas"] + [f"Zona {z}" for z in zonas_list]
            zona_sel_ui = st.selectbox("Filtrar Zona:", opcoes_zonas, index=0, key="sel_zona_filtro_comp")
            if zona_sel_ui != "⭐ Todas as Zonas":
                filtro_zona_especifica = int(zona_sel_ui.replace("Zona ", ""))

    elif nivel_geo == "Bairros & Distritos":
        with c_geo2:
            mun_nome_escolhido = st.selectbox("Escolha o Município:", muns_nomes, index=recife_idx, key="sel_mun_bairros_comp")
            info_mun = df_mun_map[df_mun_map['NM_MUN'] == mun_nome_escolhido].iloc[0]
            cd_mun_escolhido = int(info_mun['CD_MUN'])
        with c_geo3:
            df_b_disp = get_votos_candidato_bairros(slot_a2['ano'], slot_a2['turno'], slot_a2['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_a2['numero_candidato'], slot_a2['sigla_partido'])
            bairros_list = sorted(df_b_disp['territorio'].unique().tolist()) if len(df_b_disp) > 0 else []
            opcoes_bairros = ["⭐ Todos os Bairros"] + bairros_list
            bairro_sel_ui = st.selectbox("Filtrar Bairro:", opcoes_bairros, index=0, key="sel_bairro_filtro_comp")
            if bairro_sel_ui != "⭐ Todos os Bairros":
                filtro_bairro_especifico = bairro_sel_ui

    elif nivel_geo == "Colégios Eleitorais":
        with c_geo2:
            mun_nome_escolhido = st.selectbox("Escolha o Município:", muns_nomes, index=recife_idx, key="sel_mun_locais_comp")
            info_mun = df_mun_map[df_mun_map['NM_MUN'] == mun_nome_escolhido].iloc[0]
            cd_mun_escolhido = int(info_mun['CD_MUN'])
        with c_geo3:
            busca_colegio = st.text_input("🔍 Pesquisar Colégio ou Bairro:", placeholder="Ex: Paulo Freire, FBV, Boa Viagem...", key="busca_colegio_comp")

    # --- 3. RECUPERAÇÃO E CONSOLIDAÇÃO DOS DADOS ---
    with st.spinner("Calculando desempenho comparativo territorial..."):
        if nivel_geo == "Regiões de Desenvolvimento (12)":
            df_a1 = get_votos_candidato_rd(slot_a1['ano'], slot_a1['turno'], slot_a1['cargo'], slot_a1['numero_candidato'], slot_a1['sigla_partido'])
            df_a2 = get_votos_candidato_rd(slot_a2['ano'], slot_a2['turno'], slot_a2['cargo'], slot_a2['numero_candidato'], slot_a2['sigla_partido'])
            df_b1 = get_votos_candidato_rd(slot_b1['ano'], slot_b1['turno'], slot_b1['cargo'], slot_b1['numero_candidato'], slot_b1['sigla_partido']) if ativar_b and slot_b1 else None
            df_b2 = get_votos_candidato_rd(slot_b2['ano'], slot_b2['turno'], slot_b2['cargo'], slot_b2['numero_candidato'], slot_b2['sigla_partido']) if ativar_b and slot_b2 else None

        elif nivel_geo == "Municípios (185)":
            df_a1 = get_votos_candidato_municipios(slot_a1['ano'], slot_a1['turno'], slot_a1['cargo'], slot_a1['numero_candidato'], slot_a1['sigla_partido'])
            df_a2 = get_votos_candidato_municipios(slot_a2['ano'], slot_a2['turno'], slot_a2['cargo'], slot_a2['numero_candidato'], slot_a2['sigla_partido'])
            df_b1 = get_votos_candidato_municipios(slot_b1['ano'], slot_b1['turno'], slot_b1['cargo'], slot_b1['numero_candidato'], slot_b1['sigla_partido']) if ativar_b and slot_b1 else None
            df_b2 = get_votos_candidato_municipios(slot_b2['ano'], slot_b2['turno'], slot_b2['cargo'], slot_b2['numero_candidato'], slot_b2['sigla_partido']) if ativar_b and slot_b2 else None

        elif nivel_geo == "Zonas Eleitorais":
            df_a1 = get_votos_candidato_zonas(slot_a1['ano'], slot_a1['turno'], slot_a1['cargo'], cd_mun_escolhido, slot_a1['numero_candidato'], slot_a1['sigla_partido'])
            df_a2 = get_votos_candidato_zonas(slot_a2['ano'], slot_a2['turno'], slot_a2['cargo'], cd_mun_escolhido, slot_a2['numero_candidato'], slot_a2['sigla_partido'])
            df_b1 = get_votos_candidato_zonas(slot_b1['ano'], slot_b1['turno'], slot_b1['cargo'], cd_mun_escolhido, slot_b1['numero_candidato'], slot_b1['sigla_partido']) if ativar_b and slot_b1 else None
            df_b2 = get_votos_candidato_zonas(slot_b2['ano'], slot_b2['turno'], slot_b2['cargo'], cd_mun_escolhido, slot_b2['numero_candidato'], slot_b2['sigla_partido']) if ativar_b and slot_b2 else None

        elif nivel_geo == "Bairros & Distritos":
            df_a1 = get_votos_candidato_bairros(slot_a1['ano'], slot_a1['turno'], slot_a1['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_a1['numero_candidato'], slot_a1['sigla_partido'])
            df_a2 = get_votos_candidato_bairros(slot_a2['ano'], slot_a2['turno'], slot_a2['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_a2['numero_candidato'], slot_a2['sigla_partido'])
            df_b1 = get_votos_candidato_bairros(slot_b1['ano'], slot_b1['turno'], slot_b1['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_b1['numero_candidato'], slot_b1['sigla_partido']) if ativar_b and slot_b1 else None
            df_b2 = get_votos_candidato_bairros(slot_b2['ano'], slot_b2['turno'], slot_b2['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_b2['numero_candidato'], slot_b2['sigla_partido']) if ativar_b and slot_b2 else None

        elif nivel_geo == "Colégios Eleitorais":
            df_a1 = get_votos_candidato_locais(slot_a1['ano'], slot_a1['turno'], slot_a1['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_a1['numero_candidato'], slot_a1['sigla_partido'])
            df_a2 = get_votos_candidato_locais(slot_a2['ano'], slot_a2['turno'], slot_a2['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_a2['numero_candidato'], slot_a2['sigla_partido'])
            df_b1 = get_votos_candidato_locais(slot_b1['ano'], slot_b1['turno'], slot_b1['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_b1['numero_candidato'], slot_b1['sigla_partido']) if ativar_b and slot_b1 else None
            df_b2 = get_votos_candidato_locais(slot_b2['ano'], slot_b2['turno'], slot_b2['cargo'], cd_mun_escolhido, mun_nome_escolhido, slot_b2['numero_candidato'], slot_b2['sigla_partido']) if ativar_b and slot_b2 else None

    # Merge das bases
    base_cols = ['territorio', 'votos', 'pct_votos']
    df_merged = pd.merge(
        df_a1[base_cols].rename(columns={'votos': 'votos_a1', 'pct_votos': 'pct_a1'}),
        df_a2[base_cols].rename(columns={'votos': 'votos_a2', 'pct_votos': 'pct_a2'}),
        on='territorio',
        how='outer'
    )
    df_merged['votos_a1'] = df_merged['votos_a1'].fillna(0).astype(float)
    df_merged['pct_a1'] = df_merged['pct_a1'].fillna(0.0).astype(float)
    df_merged['votos_a2'] = df_merged['votos_a2'].fillna(0).astype(float)
    df_merged['pct_a2'] = df_merged['pct_a2'].fillna(0.0).astype(float)

    df_merged['delta_votos_a'] = df_merged['votos_a2'] - df_merged['votos_a1']
    df_merged['delta_pct_a'] = (df_merged['pct_a2'] - df_merged['pct_a1']).round(2)

    if ativar_b and df_b1 is not None and df_b2 is not None:
        df_merged = pd.merge(
            df_merged,
            df_b1[base_cols].rename(columns={'votos': 'votos_b1', 'pct_votos': 'pct_b1'}),
            on='territorio',
            how='outer'
        )
        df_merged = pd.merge(
            df_merged,
            df_b2[base_cols].rename(columns={'votos': 'votos_b2', 'pct_votos': 'pct_b2'}),
            on='territorio',
            how='outer'
        )
        df_merged['votos_b1'] = df_merged['votos_b1'].fillna(0).astype(float)
        df_merged['pct_b1'] = df_merged['pct_b1'].fillna(0.0).astype(float)
        df_merged['votos_b2'] = df_merged['votos_b2'].fillna(0).astype(float)
        df_merged['pct_b2'] = df_merged['pct_b2'].fillna(0.0).astype(float)

        df_merged['delta_votos_b'] = df_merged['votos_b2'] - df_merged['votos_b1']
        df_merged['delta_pct_b'] = (df_merged['pct_b2'] - df_merged['pct_b1']).round(2)
        df_merged['saldo_a_vs_b_2'] = df_merged['votos_a2'] - df_merged['votos_b2']
        df_merged['vantagem_pct_a_2'] = (df_merged['pct_a2'] - df_merged['pct_b2']).round(2)

    # Aplicação de filtros pós-merge
    if filtro_rd_especifica:
        df_merged = df_merged[df_merged['territorio'] == filtro_rd_especifica]

    if mun_nome_escolhido and nivel_geo == "Municípios (185)":
        df_merged = df_merged[df_merged['territorio'] == mun_nome_escolhido]
    elif nivel_geo == "Municípios (185)" and rd_filtro_muns != "⭐ Todas as Regiões":
        muns_validos = set(df_mun_map[df_mun_map['REGIAO_DESENVOLVIMENTO'] == rd_filtro_muns]['NM_MUN'].unique())
        df_merged = df_merged[df_merged['territorio'].isin(muns_validos)]

    if filtro_zona_especifica is not None:
        df_merged = df_merged[df_merged['territorio'] == f"Zona {filtro_zona_especifica}"]

    if filtro_bairro_especifico is not None:
        df_merged = df_merged[df_merged['territorio'] == filtro_bairro_especifico]

    if busca_colegio.strip():
        term = busca_colegio.strip().upper()
        df_merged = df_merged[df_merged['territorio'].str.upper().str.contains(term, na=False)]

    if len(df_merged) == 0:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # --- 4. CARDS DE KPIS RESUMO ---
    st.markdown("---")
    st.markdown("#### 📌 Resumo de Desempenho Global (Filtro Atual)")

    tot_a1_votos = df_merged['votos_a1'].sum()
    tot_a2_votos = df_merged['votos_a2'].sum()
    delta_tot_a = tot_a2_votos - tot_a1_votos
    cresc_pct_a = (100.0 * delta_tot_a / tot_a1_votos) if tot_a1_votos > 0 else 0.0

    media_pct_a1 = df_merged['pct_a1'].mean()
    media_pct_a2 = df_merged['pct_a2'].mean()
    delta_media_pct_a = media_pct_a2 - media_pct_a1

    if ativar_b and slot_b1 and slot_b2:
        tot_b1_votos = df_merged['votos_b1'].sum()
        tot_b2_votos = df_merged['votos_b2'].sum()
        delta_tot_b = tot_b2_votos - tot_b1_votos
        cresc_pct_b = (100.0 * delta_tot_b / tot_b1_votos) if tot_b1_votos > 0 else 0.0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric(
                label=f"🔵 {slot_a1['label_curto']} (Votos)",
                value=fmt_int(tot_a1_votos)
            )
        with k2:
            sinal_a = "+" if delta_tot_a >= 0 else ""
            st.metric(
                label=f"🔵 {slot_a2['label_curto']} (Votos)",
                value=fmt_int(tot_a2_votos),
                delta=f"{sinal_a}{fmt_int(delta_tot_a)} ({sinal_a}{fmt_pct(cresc_pct_a)})"
            )
        with k3:
            sinal_b = "+" if delta_tot_b >= 0 else ""
            st.metric(
                label=f"🔴 {slot_b2['label_curto']} (Votos)",
                value=fmt_int(tot_b2_votos),
                delta=f"{sinal_b}{fmt_int(delta_tot_b)} ({sinal_b}{fmt_pct(cresc_pct_b)})"
            )
        with k4:
            saldo_a_b = tot_a2_votos - tot_b2_votos
            sinal_saldo = "+" if saldo_a_b >= 0 else ""
            st.metric(
                label=f"⚔️ Vantagem A sobre B ({slot_a2['ano']})",
                value=f"{sinal_saldo}{fmt_int(saldo_a_b)} votos",
                delta=f"Saldo no Pleito Recente"
            )
    else:
        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric(
                label=f"📅 {slot_a1['label_curto']} (Votos Nominais)",
                value=fmt_int(tot_a1_votos),
                delta=f"Média: {fmt_pct(media_pct_a1)}"
            )
        with k2:
            sinal_a = "+" if delta_tot_a >= 0 else ""
            st.metric(
                label=f"📅 {slot_a2['label_curto']} (Votos Nominais)",
                value=fmt_int(tot_a2_votos),
                delta=f"{sinal_a}{fmt_int(delta_tot_a)} ({sinal_a}{fmt_pct(cresc_pct_a)})"
            )
        with k3:
            sinal_pct = "+" if delta_media_pct_a >= 0 else ""
            st.metric(
                label=f"🚀 Evolução Média % de Válidos",
                value=f"{fmt_pct(media_pct_a2)}",
                delta=f"{sinal_pct}{fmt_pct(delta_media_pct_a)} p.p."
            )

    # --- 5. GRÁFICO DE BARRAS AGRUPADAS POR TERRITÓRIO ---
    st.markdown("---")
    st.markdown("#### 📊 Gráfico Comparativo por Território")

    # Controles do gráfico
    c_g1, c_g2, c_g3 = st.columns([1.5, 1.2, 1.3])
    with c_g1:
        metrica_grafico = st.radio(
            "Métrica no Gráfico:",
            [
                "Votos Nominais (Absoluto)",
                "% Votos Válidos (Percentual)",
                "Δ Saldo de Votos (Pleito 2 - Pleito 1)",
                "Δ Variação % p.p. (Pleito 2 - Pleito 1)"
            ],
            horizontal=True,
            key="rad_metrica_comp"
        )
    with c_g2:
        # Quantidade de territórios
        total_terrs = len(df_merged)
        top_n = st.slider(
            "Quantidade de Territórios no Gráfico:",
            min_value=min(5, total_terrs),
            max_value=min(60, total_terrs),
            value=min(15, total_terrs),
            step=1,
            key="slider_top_comp"
        )
    with c_g3:
        ordem_grafico = st.selectbox(
            "Ordenar Territórios por:",
            [
                "Maior Volume de Votos no Pleito 2 (Recomendado)",
                "Maior Crescimento de Votos (Δ Votos A)",
                "Maior Crescimento Percentual (Δ % A)",
                "Ordem Alfabética do Território"
            ],
            index=0,
            key="sel_ordem_comp"
        )

    # Ordenação dos dados
    if "Volume de Votos" in ordem_grafico:
        df_sorted = df_merged.sort_values(by="votos_a2", ascending=False)
    elif "Crescimento de Votos" in ordem_grafico:
        df_sorted = df_merged.sort_values(by="delta_votos_a", ascending=False)
    elif "Crescimento Percentual" in ordem_grafico:
        df_sorted = df_merged.sort_values(by="delta_pct_a", ascending=False)
    else:
        df_sorted = df_merged.sort_values(by="territorio", ascending=True)

    df_plot_sub = df_sorted.head(top_n).copy()

    # Construção da base longa (long format) para px.bar agrupado lado a lado
    # Garantir que em cada território todas as barras fiquem agrupadas juntas
    rows_plot = []

    label_a1 = f"A: {slot_a1['label_curto']}"
    label_a2 = f"A: {slot_a2['label_curto']}"
    label_b1 = f"B: {slot_b1['label_curto']}" if ativar_b and slot_b1 else None
    label_b2 = f"B: {slot_b2['label_curto']}" if ativar_b and slot_b2 else None

    # Mapeamento de cores sólidas e contrastantes
    cores_map = {
        label_a1: "#4A90E2", # Azul claro/médio
        label_a2: "#0D47A1"  # Azul escuro vibrante
    }
    if ativar_b and label_b1 and label_b2:
        cores_map[label_b1] = "#FF8A65" # Coral/Pêssego
        cores_map[label_b2] = "#D32F2F" # Vermelho vibrante

    # Paleta de variação delta
    label_delta_a = f"Δ A ({slot_a2['ano']} - {slot_a1['ano']})"
    label_delta_b = f"Δ B ({slot_b2['ano']} - {slot_b1['ano']})" if ativar_b and slot_b1 and slot_b2 else None
    cores_map[label_delta_a] = "#1565C0"
    if label_delta_b:
        cores_map[label_delta_b] = "#C62828"

    if metrica_grafico == "Votos Nominais (Absoluto)":
        y_col_title = "Votos Nominais"
        for _, r in df_plot_sub.iterrows():
            t_nome = r['territorio']
            rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_a1, "Valor": r['votos_a1'], "Texto": fmt_int(r['votos_a1'])})
            rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_a2, "Valor": r['votos_a2'], "Texto": fmt_int(r['votos_a2'])})
            if ativar_b and label_b1 and label_b2:
                rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_b1, "Valor": r['votos_b1'], "Texto": fmt_int(r['votos_b1'])})
                rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_b2, "Valor": r['votos_b2'], "Texto": fmt_int(r['votos_b2'])})

    elif metrica_grafico == "% Votos Válidos (Percentual)":
        y_col_title = "% de Votos Válidos"
        for _, r in df_plot_sub.iterrows():
            t_nome = r['territorio']
            rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_a1, "Valor": r['pct_a1'], "Texto": fmt_pct(r['pct_a1'])})
            rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_a2, "Valor": r['pct_a2'], "Texto": fmt_pct(r['pct_a2'])})
            if ativar_b and label_b1 and label_b2:
                rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_b1, "Valor": r['pct_b1'], "Texto": fmt_pct(r['pct_b1'])})
                rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_b2, "Valor": r['pct_b2'], "Texto": fmt_pct(r['pct_b2'])})

    elif metrica_grafico == "Δ Saldo de Votos (Pleito 2 - Pleito 1)":
        y_col_title = "Saldo de Votos (Δ)"
        for _, r in df_plot_sub.iterrows():
            t_nome = r['territorio']
            sinal_da = "+" if r['delta_votos_a'] >= 0 else ""
            rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_delta_a, "Valor": r['delta_votos_a'], "Texto": f"{sinal_da}{fmt_int(r['delta_votos_a'])}"})
            if ativar_b and label_delta_b:
                sinal_db = "+" if r['delta_votos_b'] >= 0 else ""
                rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_delta_b, "Valor": r['delta_votos_b'], "Texto": f"{sinal_db}{fmt_int(r['delta_votos_b'])}"})

    elif metrica_grafico == "Δ Variação % p.p. (Pleito 2 - Pleito 1)":
        y_col_title = "Variação em Pontos Percentuais (p.p.)"
        for _, r in df_plot_sub.iterrows():
            t_nome = r['territorio']
            sinal_pa = "+" if r['delta_pct_a'] >= 0 else ""
            rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_delta_a, "Valor": r['delta_pct_a'], "Texto": f"{sinal_pa}{fmt_pct(r['delta_pct_a'])}"})
            if ativar_b and label_delta_b:
                sinal_pb = "+" if r['delta_pct_b'] >= 0 else ""
                rows_plot.append({"Território": t_nome, "Candidato / Pleito": label_delta_b, "Valor": r['delta_pct_b'], "Texto": f"{sinal_pb}{fmt_pct(r['delta_pct_b'])}"})

    df_plot = pd.DataFrame(rows_plot)

    # Gráfico com Plotly Express em modo agrupado (barmode='group')
    fig = px.bar(
        df_plot,
        x="Território",
        y="Valor",
        color="Candidato / Pleito",
        barmode="group",
        color_discrete_map=cores_map,
        text="Texto",
        category_orders={"Território": df_plot_sub['territorio'].tolist()}
    )

    fig.update_layout(
        height=540,
        margin=dict(l=20, r=20, t=30, b=80),
        xaxis_title="Território",
        yaxis_title=y_col_title,
        legend_title="Candidato / Pleito",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        uniformtext=dict(minsize=8, mode='show')
    )
    fig.update_traces(
        textposition='outside',
        cliponaxis=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- 6. TABELA ANALÍTICA DETALHADA & DOWNLOAD ---
    st.markdown("---")
    st.markdown("#### 📋 Tabela Analítica de Comparação Territorial")

    # Formatar dados para apresentação
    df_tabela = df_sorted.copy()

    df_tabela[f"Votos {slot_a1['label_curto']}"] = df_tabela['votos_a1'].apply(fmt_int)
    df_tabela[f"% {slot_a1['label_curto']}"] = df_tabela['pct_a1'].apply(fmt_pct)
    df_tabela[f"Votos {slot_a2['label_curto']}"] = df_tabela['votos_a2'].apply(fmt_int)
    df_tabela[f"% {slot_a2['label_curto']}"] = df_tabela['pct_a2'].apply(fmt_pct)
    df_tabela[f"Δ Votos ({slot_a2['ano']}-{slot_a1['ano']})"] = df_tabela['delta_votos_a'].apply(lambda v: f"+{fmt_int(v)}" if v >= 0 else fmt_int(v))
    df_tabela[f"Δ % p.p. ({slot_a2['ano']}-{slot_a1['ano']})"] = df_tabela['delta_pct_a'].apply(lambda v: f"+{fmt_pct(v)}" if v >= 0 else fmt_pct(v))

    cols_exibir = [
        'territorio',
        f"Votos {slot_a1['label_curto']}",
        f"% {slot_a1['label_curto']}",
        f"Votos {slot_a2['label_curto']}",
        f"% {slot_a2['label_curto']}",
        f"Δ Votos ({slot_a2['ano']}-{slot_a1['ano']})",
        f"Δ % p.p. ({slot_a2['ano']}-{slot_a1['ano']})"
    ]

    if ativar_b and slot_b1 and slot_b2:
        df_tabela[f"Votos {slot_b1['label_curto']}"] = df_tabela['votos_b1'].apply(fmt_int)
        df_tabela[f"% {slot_b1['label_curto']}"] = df_tabela['pct_b1'].apply(fmt_pct)
        df_tabela[f"Votos {slot_b2['label_curto']}"] = df_tabela['votos_b2'].apply(fmt_int)
        df_tabela[f"% {slot_b2['label_curto']}"] = df_tabela['pct_b2'].apply(fmt_pct)
        df_tabela[f"Δ Votos B ({slot_b2['ano']}-{slot_b1['ano']})"] = df_tabela['delta_votos_b'].apply(lambda v: f"+{fmt_int(v)}" if v >= 0 else fmt_int(v))
        df_tabela[f"Δ % B p.p. ({slot_b2['ano']}-{slot_b1['ano']})"] = df_tabela['delta_pct_b'].apply(lambda v: f"+{fmt_pct(v)}" if v >= 0 else fmt_pct(v))
        df_tabela[f"Saldo A vs B ({slot_a2['ano']})"] = df_tabela['saldo_a_vs_b_2'].apply(lambda v: f"+{fmt_int(v)}" if v >= 0 else fmt_int(v))

        cols_exibir.extend([
            f"Votos {slot_b1['label_curto']}",
            f"% {slot_b1['label_curto']}",
            f"Votos {slot_b2['label_curto']}",
            f"% {slot_b2['label_curto']}",
            f"Δ Votos B ({slot_b2['ano']}-{slot_b1['ano']})",
            f"Δ % B p.p. ({slot_b2['ano']}-{slot_b1['ano']})",
            f"Saldo A vs B ({slot_a2['ano']})"
        ])

    df_view = df_tabela[cols_exibir].rename(columns={'territorio': 'Território'})

    st.dataframe(df_view, use_container_width=True, hide_index=True)

    csv_data = df_view.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Baixar Tabela Comparativa (CSV)",
        data=csv_data,
        file_name=f"comparativo_{slot_a1['nome_urna']}_{slot_a1['ano']}_vs_{slot_a2['ano']}.csv",
        mime="text/csv",
        use_container_width=True,
        key="btn_download_comp_csv"
    )
