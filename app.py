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
from modules.tab_matching_recife import render_tab_matching_recife

# 1. Configuração da Página
st.set_page_config(
    page_title="Eleições Pernambuco (2008–2026)",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SISTEMA DE AUTENTICAÇÃO (USUÁRIO E SENHA) ---
def check_password():
    """Verifica se o usuário e senha digitados são válidos."""
    if st.session_state.get("authenticated", False):
        return True

    # Layout centralizado para a tela de login
    col_l, col_center, col_r = st.columns([1, 1.8, 1])
    with col_center:
        st.markdown("### 🔒 Acesso Restrito")
        st.markdown("##### Painel de Inteligência Eleitoral de Pernambuco")

        with st.form("login_form"):
            username = st.text_input("Usuário:", placeholder="Digite seu usuário").strip()
            password = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
            btn_entrar = st.form_submit_button("Entrar", use_container_width=True)

        if btn_entrar:
            if not username or not password:
                st.warning("Por favor, preencha o usuário e a senha.")
                return False

            # Carregar banco de usuários dos secrets
            users_db = {}
            try:
                if "passwords" in st.secrets:
                    users_db = {k.lower(): str(v) for k, v in st.secrets["passwords"].items()}
                elif "users" in st.secrets:
                    users_db = {k.lower(): str(v) for k, v in st.secrets["users"].items()}
            except Exception:
                pass

            # Compatibilidade com secret de senha única (caso ainda não tenha cadastrado lista de usuários)
            single_pass = None
            try:
                if "password" in st.secrets:
                    single_pass = str(st.secrets["password"])
                elif "PASSWORD" in st.secrets:
                    single_pass = str(st.secrets["PASSWORD"])
            except Exception:
                pass

            # Fallback se nenhum secret estiver cadastrado
            if not users_db and not single_pass:
                users_db = {"admin": "demokratia"}

            u_clean = username.lower()
            
            # Validação 1: Lista de usuários cadastrados nos secrets
            if users_db and u_clean in users_db and str(users_db[u_clean]) == password:
                st.session_state["authenticated"] = True
                st.session_state["logged_user"] = username
                st.rerun()
            # Validação 2: Senha única cadastrada (permite qualquer nome de usuário preenchido com a senha certa)
            elif not users_db and single_pass and password == single_pass:
                st.session_state["authenticated"] = True
                st.session_state["logged_user"] = username
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos. Tente novamente.")

    return False

if not check_password():
    st.stop()


# 2. Carregar metadados e mapeamento de municípios
df_meta = get_metadata_filtros()
gdf_mun_base = load_municipios_gdf()
df_mun_map = gdf_mun_base[['CD_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO']].copy()
df_mun_map['CD_MUN'] = df_mun_map['CD_MUN'].astype(str)

# 3. Barra Lateral (Sidebar) com Filtros Globais
st.sidebar.title("🗳️ Filtros Eleitorais")
st.sidebar.markdown(f"👤 **Usuário:** `{st.session_state.get('logged_user', 'Conectado')}`")
if st.sidebar.button("🚪 Sair", key="btn_logout", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["logged_user"] = None
    st.rerun()
st.sidebar.markdown("---")

# Filtro Ano
anos_disponiveis = sorted(df_meta['ano'].unique(), reverse=True)
default_ano_idx = anos_disponiveis.index(2026) if 2026 in anos_disponiveis else 0
ano_sel = st.sidebar.selectbox("Ano da Eleição:", anos_disponiveis, index=default_ano_idx)

# Filtro Cargo (filtrado pelo ano)
cargos_ano = sorted(df_meta[df_meta['ano'] == ano_sel]['cargo'].unique())
default_cargo_idx = cargos_ano.index('governador') if 'governador' in cargos_ano else 0
cargo_sel = st.sidebar.selectbox("Cargo em Disputa:", cargos_ano, index=default_cargo_idx)

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
        cands_labels = ["⭐ TODOS (Mapa de Vencedores / Mais Votados)"] + [
            f"{row['nome_urna']} ({row['sigla_partido']}) - {fmt_int(row['total_votos'])} votos"
            for _, row in df_cands.iterrows()
        ]
        cand_idx = st.sidebar.selectbox(
            "Selecione o Candidato:",
            range(len(cands_labels)),
            format_func=lambda i: cands_labels[i],
            index=0,
            key=f"sel_cand_main_{ano_sel}_{cargo_sel}_{turno_sel}"
        )
        if cand_idx == 0:
            cand_selecionado = None
            partido_selecionado = None
        else:
            cand_selecionado = df_cands.iloc[cand_idx - 1].to_dict()
            partido_selecionado = cand_selecionado['sigla_partido']
    else:
        st.sidebar.info("Nenhum candidato encontrado para este pleito.")
else:
    with st.spinner("Carregando partidos..."):
        df_parts = get_ranking_partidos(ano_sel, turno_sel, cargo_sel)
        
    if len(df_parts) > 0:
        parts_labels = ["⭐ TODOS (Mapa de Vencedores por Partido)"] + [
            f"{row['sigla_partido']} ({fmt_int(row['total_votos'])} votos)"
            for _, row in df_parts.iterrows()
        ]
        part_idx = st.sidebar.selectbox(
            "Selecione o Partido:",
            range(len(parts_labels)),
            format_func=lambda i: parts_labels[i],
            index=0,
            key=f"sel_part_main_{ano_sel}_{cargo_sel}_{turno_sel}"
        )
        if part_idx == 0:
            partido_selecionado = None
            cand_selecionado = None
        else:
            partido_selecionado = df_parts.iloc[part_idx - 1]['sigla_partido']
            cand_selecionado = None
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
if st.sidebar.button("🔄 Limpar Cache / Recarregar", key="btn_clear_cache", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# 4. Cabeçalho Principal
modo_todos = (cand_selecionado is None and partido_selecionado is None)

if modo_todos:
    alvo_display = "MAPA DE VENCEDORES (Mais Votados)"
    partido_badge = ""
else:
    alvo_display = cand_selecionado['nome_urna'] if cand_selecionado is not None else partido_selecionado
    partido_badge = f" ({cand_selecionado['sigla_partido']})" if cand_selecionado is not None else ""

st.title("🗳️ Painel Eleitoral de Pernambuco")
st.markdown(
    f"##### Eleições {ano_sel} • {turno_sel}º Turno • **{cargo_sel.upper()}** — Exibindo: **{alvo_display}{partido_badge}**"
)

if modo_todos:
    st.info("🗺️ **Modo Mapa de Vencedores:** Exibindo os líderes de votos em cada região, município, zona eleitoral, bairro e colégio eleitoral. Para analisar um candidato ou partido individualmente, basta selecioná-lo no menu lateral.")

# 5. Estrutura em Abas Modulares
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🌍 Regiões de Desenvolvimento (12)",
    "🏛️ Municípios (185)",
    "🗳️ Zonas Eleitorais (209)",
    "🏘️ Bairros & Distritos (1.058)",
    "🏫 Colégios Eleitorais (3.406)",
    "🔗 Cruzamentos & Dobradinhas",
    "🎯 Matching Recife (3 Níveis)"
])

with tab1:
    render_tab_macrorregioes(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map, modo_todos=modo_todos)

with tab2:
    render_tab_municipios(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map, modo_todos=modo_todos)

with tab3:
    render_tab_zonas(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map, modo_todos=modo_todos)

with tab4:
    render_tab_bairros(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map, modo_todos=modo_todos)

with tab5:
    render_tab_locais(ano_sel, turno_sel, cargo_sel, modo_analise, partido_selecionado, cand_selecionado, df_mun_map, modo_todos=modo_todos)

with tab6:
    render_tab_cruzamento(df_meta, df_mun_map)

with tab7:
    render_tab_matching_recife(df_meta, df_mun_map)

