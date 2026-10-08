import streamlit as st
import pandas as pd
from config import BASE_DIR, PATH_GEO_MUNICIPIOS, fmt_int, fmt_pct
from modules.geo_loader import load_municipios_gdf
from modules.data_loader import (
    get_metadata_filtros,
    get_ranking_candidatos,
    get_ranking_partidos
)
from modules.tab_macrorregioes import render_tab_macrorregioes
from modules.tab_municipios import render_tab_municipios
from modules.tab_zonas import render_tab_zonas
from modules.tab_bairros import render_tab_bairros
from modules.tab_locais import render_tab_locais
from modules.tab_cruzamento import render_tab_cruzamento

# 1. Configuração da Página
st.set_page_config(
    page_title="Eleições Pernambuco (2008–2026)",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Carregar metadados e mapeamento de municípios
df_meta = get_metadata_filtros()
gdf_mun_base = load_municipios_gdf()
df_mun_map = gdf_mun_base[['CD_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO']].copy()
df_mun_map['CD_MUN'] = df_mun_map['CD_MUN'].astype(str)

# 3. Barra Lateral (Sidebar) com Filtros Globais
st.sidebar.title("🗳️ Filtros Eleitorais")
st.sidebar.markdown("---")

# Filtro Ano
anos_disponiveis = sorted(df_meta['ano'].unique(), reverse=True)
default_ano_idx = 0  # Ano mais recente
ano_sel = st.sidebar.selectbox("Ano da Eleição:", anos_disponiveis, index=default_ano_idx)

# Filtro Cargo (filtrado pelo ano)
cargos_ano = sorted(df_meta[df_meta['ano'] == ano_sel]['cargo'].unique())
cargo_sel = st.sidebar.selectbox("Cargo em Disputa:", cargos_ano, index=0)

# Filtro Turno (filtrado pelo ano e cargo)
turnos_ano_cargo = sorted(df_meta[(df_meta['ano'] == ano_sel) & (df_meta['cargo'] == cargo_sel)]['turno'].unique())
turno_sel = st.sidebar.selectbox("Turno:", turnos_ano_cargo, index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Foco da Análise")
modo_analise = st.sidebar.radio("Analisar por:", ["Candidato", "Partido"], horizontal=True)

cand_selecionado = None
partido_selecionado = None

if modo_analise == "Candidato":
    with st.spinner("Carregando candidatos..."):
        df_cands = get_ranking_candidatos(ano_sel, turno_sel, cargo_sel, limit=80)
        
    if len(df_cands) > 0:
        cands_labels = [
            f"{row['nome_urna']} ({row['sigla_partido']}) - {fmt_int(row['total_votos'])} votos"
            for _, row in df_cands.iterrows()
        ]
        cand_idx = st.sidebar.selectbox(
            "Selecione o Candidato:",
            range(len(cands_labels)),
            format_func=lambda i: cands_labels[i]
        )
        cand_selecionado = df_cands.iloc[cand_idx].to_dict()
        partido_selecionado = cand_selecionado['sigla_partido']
    else:
        st.sidebar.info("Nenhum candidato encontrado para este pleito.")
else:
    with st.spinner("Carregando partidos..."):
        df_parts = get_ranking_partidos(ano_sel, turno_sel, cargo_sel)
        
    if len(df_parts) > 0:
        parts_labels = [
            f"{row['sigla_partido']} ({fmt_int(row['total_votos'])} votos)"
            for _, row in df_parts.iterrows()
        ]
        part_idx = st.sidebar.selectbox(
            "Selecione o Partido:",
            range(len(parts_labels)),
            format_func=lambda i: parts_labels[i]
        )
        partido_selecionado = df_parts.iloc[part_idx]['sigla_partido']
    else:
        st.sidebar.info("Nenhum partido encontrado para este pleito.")

# Informações no rodapé da Sidebar
st.sidebar.markdown("---")
st.sidebar.caption(
    "📊 **Base Histórica de Pernambuco**\n"
    "• 185 Municípios\n"
    "• 209 Zonas-Município\n"
    "• 1.058 Bairros/Distritos\n"
    "• 3.406 Colégios Eleitorais\n"
    "• 22.111 Seções Eleitorais\n"
    "• TRE-PE / TSE Oficial"
)

# 4. Cabeçalho Principal
alvo_display = cand_selecionado['nome_urna'] if cand_selecionado is not None else partido_selecionado
partido_badge = f" ({cand_selecionado['sigla_partido']})" if cand_selecionado is not None else ""

st.title("🗳️ Painel Eleitoral de Pernambuco")
st.markdown(
    f"##### Eleições {ano_sel} • {turno_sel}º Turno • **{cargo_sel.upper()}** — Exibindo: **{alvo_display}{partido_badge}**"
)

# 5. Estrutura em Abas Modulares
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌍 Regiões de Desenvolvimento (12)",
    "🏛️ Municípios (185)",
    "🗳️ Zonas Eleitorais (209)",
    "🏘️ Bairros & Distritos (1.058)",
    "🏫 Colégios Eleitorais (3.406)",
    "🔗 Cruzamentos & Dobradinhas"
])

with tab1:
    render_tab_macrorregioes(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map)

with tab2:
    render_tab_municipios(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map)

with tab3:
    render_tab_zonas(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map)

with tab4:
    render_tab_bairros(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map)

with tab5:
    render_tab_locais(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map)

with tab6:
    render_tab_cruzamento(df_meta, df_mun_map)
