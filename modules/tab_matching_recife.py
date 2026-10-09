import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from config import (
    PATH_RESULTADOS,
    PATH_LOCAIS_PARQUET,
    PRESIDENTES_NOMES,
    fmt_int,
    fmt_pct,
    get_cores_foco,
    get_contrast_color,
    normalize_text
)
from modules.geo_loader import load_mosaico_bairros_gdf, load_zonas_gdf
from modules.data_loader import get_locais_votacao_base

# Cores oficiais da taxonomia estratégica de matching
COR_ALIANCA_PLENA = "#27AE60"       # Verde Esmeralda: QL1 >= 1 & QL2 >= 1 & QL3 >= 1
COR_ALERTA_VAZAMENTO = "#E74C3C"    # Vermelho: QL2 >= 1 & QL3 >= 1 & QL1 < 1
COR_MAJORITARIA_AUTO = "#2980B9"    # Azul Oceano: QL1 >= 1 & QL2 < 1 & QL3 < 1
COR_PARCIAL_ESTADUAL = "#E67E22"    # Laranja: QL1 >= 1 & QL2 >= 1 & QL3 < 1
COR_PARCIAL_FEDERAL = "#D35400"     # Ferrugem: QL1 >= 1 & QL3 >= 1 & QL2 < 1
COR_VACUO_CHAPA = "#95A5A6"         # Cinza: QL1 < 1 & QL2 < 1 & QL3 < 1
COR_DESCOLAMENTO_IND = "#34495E"    # Grafite / Petróleo Escuro: Outros descolamentos (neutro, sem conflito partidário)

@st.cache_data(ttl=3600)
def get_opcoes_partidos_recife(ano: int, turno: int, cargo: str):
    """Retorna a soma de votos por legenda/partido no Recife para o cargo e pleito."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    q = f"""
        SELECT sigla_partido, SUM(total_votos) as total_votos
        FROM '{res_path}'
        WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}'
          AND id_municipio = 2611606 AND sigla_partido IS NOT NULL
        GROUP BY sigla_partido
        ORDER BY total_votos DESC
    """
    df = con.execute(q).df()
    if len(df) == 0:
        return pd.DataFrame(columns=['sigla_partido', 'total_votos', 'numero_candidato', 'nome_urna', 'label'])
    df['numero_candidato'] = None
    df['nome_urna'] = df['sigla_partido'].apply(lambda s: f"{s} (Partido)")
    df['label'] = df.apply(lambda r: f"🚩 {r['sigla_partido']} (Total Partido) - {fmt_int(r['total_votos'])} votos", axis=1)
    return df

@st.cache_data(ttl=3600)
def get_opcoes_candidatos_recife(ano: int, turno: int, cargo: str):
    """Retorna candidatos que receberam votos no Recife para o pleito."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    
    if cargo == "presidente":
        q = f"""
            SELECT sigla_partido, SUM(total_votos) as total_votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}'
              AND id_municipio = 2611606 AND sigla_partido IS NOT NULL
            GROUP BY sigla_partido
            ORDER BY total_votos DESC
        """
        df = con.execute(q).df()
        df['numero_candidato'] = None
        df['nome_urna'] = df['sigla_partido'].apply(lambda sigla: PRESIDENTES_NOMES.get((ano, sigla), f"Candidato ({sigla})"))
        df['label'] = df.apply(lambda r: f"{r['nome_urna']} ({r['sigla_partido']}) [{ano}] - {fmt_int(r['total_votos'])} votos", axis=1)
        return df
    else:
        q = f"""
            SELECT numero_candidato, nome_urna, sigla_partido, SUM(total_votos) as total_votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}'
              AND id_municipio = 2611606 AND numero_candidato IS NOT NULL
            GROUP BY numero_candidato, nome_urna, sigla_partido
            ORDER BY total_votos DESC
            LIMIT 150
        """
        df = con.execute(q).df()
        df['label'] = df.apply(lambda r: f"{r['nome_urna']} ({r['sigla_partido']}) [{ano}] - {fmt_int(r['total_votos'])} votos", axis=1)
        return df

def render_tab_matching_recife(df_meta, df_mun_map):
    st.markdown("### 🎯 Matching & Dobradinhas Eleitorais — Recife (3 Níveis)")
    st.caption(
        "Cruze o alinhamento e a transferência de votos em 3 níveis simultâneos: "
        "**Majoritária (Governador / Prefeito)**, **Proporcional Estadual (Deputado Estadual / Vereador)** e "
        "**Proporcional Federal (Deputado Federal / Dobradinha)**. "
        "Avalie por **Bairro (94 Bairros)**, **Colégio Eleitoral (416 Locais)** ou **Zona Eleitoral (11 Zonas)** "
        "a lealdade territorial da chapa, sinergia de votos e riscos de vazamento / traição."
    )

    # GUIA METODOLÓGICO E GLOSSÁRIO POLÍTICO
    with st.expander("📖 Guia Metodológico & Glossário Político: O que é Descolamento Individual, Voto Casado e as 3 Visões?", expanded=False):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown(r"""
            ##### 🏷️ Dicionário das Classificações Estratégicas
            
            * 🤝 **Aliança Plena / Voto Casado ($QL_1 \ge 1.0 \land QL_2 \ge 1.0 \land QL_3 \ge 1.0$):**  
              *Território de força máxima e transferência perfeita.* Todos os 3 atores estão simultaneamente acima de suas médias no Recife. A dobradinha caminha integrada e arrasta a majoritária.
            
            * ⚠️ **Alerta de Vazamento / Descolamento ($QL_2 \ge 1.0 \land QL_3 \ge 1.0 \land QL_1 < 1.0$):**  
              *Ponto crítico de atenção.* Ambos os parlamentares têm votação expressiva, mas o voto não chegou na candidatura majoritária. Indica potencial vazamento para concorrentes majoritários ou infidelidade na base comunitária.
            
            * 🚀 **Força Majoritária Autônoma ($QL_1 \ge 1.0 \land QL_2 < 1.0 \land QL_3 < 1.0$):**  
              *Voto de opinião ou liderança carismática.* O candidato majoritário supera a média municipal sozinho, sem depender da estrutura eleitoral dos deputados.
            
            * 🎯 **Casamento Parcial 1 ou 2 ($QL_1 \ge 1.0$ e alinhamento com apenas 1 parlamentar):**  
              *Sinergia assimétrica.* A majoritária casou votos com apenas um dos deputados da dobradinha, enquanto o outro não acompanhou o ritmo no território.
            
            * 🔄 **Descolamento Individual (Apenas um parlamentar com $QL \ge 1.0$, demais $< 1.0$):**  
              *Bolsão eleitoral isolado / nicho pessoal.* O parlamentar possui uma base histórica ou paroquial concentrada naquele território, mas esse capital político fica retido: ele **não transfere votos para a majoritária** e **não carrega o parceiro de dobradinha**.
            
            * 🏜️ **Vácuo da Chapa ($QL_1 < 1.0 \land QL_2 < 1.0 \land QL_3 < 1.0$):**  
              *Reduto da oposição.* Baixo desempenho conjunto para todos os membros do grupo político; território dominado por outras forças partidárias.
            """)
        with col_g2:
            st.markdown(r"""
            ##### 🗺️ As 3 Visões Territoriais (Views)
            
            * 🏘️ **Bairros Oficiais (94 Bairros do Recife):**  
              Permite a análise socioespacial e de planejamento urbano da cidade. Ideal para identificar padrões entre morro e asfalto, zona norte e zona sul, e entender a penetração social de cada candidatura.
            
            * 🏫 **Colégios Eleitorais (416 Locais de Votação):**  
              A escala microeleitoral no detalhe das escolas e seções de votação. Essencial para coordenações operacionais de campanha, alocação de fiscais de urna, cobrança de lideranças comunitárias e ações cirúrgicas de campo.
            
            * 🗳️ **Zonas Eleitorais (11 Zonas do Recife):**  
              A escala cartorária e jurídica oficial do TRE-PE. Ideal para coordenação macroeleitoral, planejamento de carreatas, comícios zonais e articulação política regional.
            
            ---
            ##### 📐 Como Ler os Quocientes (QL) & Métricas
            * **Quociente Eleitoral Local (QL):** Normaliza o desempenho dividindo o percentual local pelo percentual médio no Recife ($QL = \%_{\text{local}} / \%_{\text{Recife}}$). Um valor de **1.0** indica desempenho idêntico à média da capital; **2.0** indica o dobro da média; abaixo de **1.0** indica votação abaixo do padrão municipal.
            * **Score 3D:** Média geométrica ponderada ($\sqrt[3]{QL_1 \times QL_2 \times QL_3}$), sintetizando a intensidade conjunta da vitória dos três candidatos no território.
            * **Sinergia da Dobradinha ($r_{23}$):** Correlação linear que mede se os deputados caminham juntos nos mesmos bairros ou se dividem o Recife em redutos separados.
            * **Transferência Majoritária ($R^2$):** Porcentagem da variação dos votos do líder majoritário explicada pela presença combinada dos dois deputados.
            """)

    # -------------------------------------------------------------
    # 1. SELEÇÃO DOS 3 NÍVEIS
    # -------------------------------------------------------------
    c1, c2, c3 = st.columns(3)
    
    anos_disp = sorted(df_meta['ano'].unique(), reverse=True)

    # NÍVEL 1: MAJORITÁRIA
    with c1:
        st.markdown("#### 🟡 Nível 1: Majoritária (Líder)")
        st.caption("Governador ou Prefeito (Eleições Anteriores)")
        ca1, ca2, ca3 = st.columns([1, 1.4, 1])
        with ca1:
            def_ano1 = anos_disp.index(2026) if 2026 in anos_disp else 0
            ano_1 = st.selectbox("Ano 1:", anos_disp, index=def_ano1, key="m_rec_ano_1")
        with ca2:
            cgs_1 = sorted(df_meta[df_meta['ano'] == ano_1]['cargo'].unique())
            def_cg1 = cgs_1.index("governador") if "governador" in cgs_1 else (cgs_1.index("prefeito") if "prefeito" in cgs_1 else 0)
            cargo_1 = st.selectbox("Cargo 1:", cgs_1, index=def_cg1, key="m_rec_cg_1")
        with ca3:
            turnos_1 = sorted(df_meta[(df_meta['ano'] == ano_1) & (df_meta['cargo'] == cargo_1)]['turno'].unique())
            turno_1 = st.selectbox("Turno 1:", turnos_1, index=0, key="m_rec_t_1")
            
        tipo_1 = st.radio("Tipo 1:", ["👤 Candidato", "🚩 Soma do Partido"], horizontal=True, key=f"m_rec_tipo_1_{ano_1}_{cargo_1}_{turno_1}")
        is_partido_1 = "Partido" in tipo_1

        if is_partido_1:
            df_itens_1 = get_opcoes_partidos_recife(ano_1, turno_1, cargo_1)
            lbl_sel_1 = "Selecione o Partido 1:"
        else:
            df_itens_1 = get_opcoes_candidatos_recife(ano_1, turno_1, cargo_1)
            lbl_sel_1 = "Selecione o Candidato 1:"

        if len(df_itens_1) > 0:
            def_idx_1 = 0
            if not is_partido_1:
                for idx_i, row_i in df_itens_1.iterrows():
                    if "JOAO CAMPOS" in normalize_text(row_i['nome_urna']):
                        def_idx_1 = idx_i
                        break
            else:
                for idx_i, row_i in df_itens_1.iterrows():
                    if row_i['sigla_partido'] == "PSB":
                        def_idx_1 = idx_i
                        break
            sel_idx_1 = st.selectbox(
                lbl_sel_1,
                range(len(df_itens_1)),
                index=def_idx_1,
                format_func=lambda i: df_itens_1.iloc[i]['label'],
                key=f"m_rec_item_1_{ano_1}_{cargo_1}_{turno_1}_{tipo_1}"
            )
            item_1 = df_itens_1.iloc[sel_idx_1]
        else:
            st.warning("Nenhum dado encontrado para o Nível 1.")
            return

    # NÍVEL 2: PROPORCIONAL ESTADUAL / VEREADOR
    with c2:
        st.markdown("#### 🟠 Nível 2: Estadual / Base (Parlamentar 1)")
        st.caption("Deputado Estadual ou Vereador")
        cb1, cb2, cb3 = st.columns([1, 1.4, 1])
        with cb1:
            def_ano2 = anos_disp.index(2026) if 2026 in anos_disp else 0
            ano_2 = st.selectbox("Ano 2:", anos_disp, index=def_ano2, key="m_rec_ano_2")
        with cb2:
            cgs_2 = sorted(df_meta[df_meta['ano'] == ano_2]['cargo'].unique())
            def_cg2 = cgs_2.index("deputado estadual") if "deputado estadual" in cgs_2 else (cgs_2.index("vereador") if "vereador" in cgs_2 else 0)
            cargo_2 = st.selectbox("Cargo 2:", cgs_2, index=def_cg2, key="m_rec_cg_2")
        with cb3:
            turnos_2 = sorted(df_meta[(df_meta['ano'] == ano_2) & (df_meta['cargo'] == cargo_2)]['turno'].unique())
            turno_2 = st.selectbox("Turno 2:", turnos_2, index=0, key="m_rec_t_2")

        tipo_2 = st.radio("Tipo 2:", ["👤 Candidato", "🚩 Soma do Partido"], horizontal=True, key=f"m_rec_tipo_2_{ano_2}_{cargo_2}_{turno_2}")
        is_partido_2 = "Partido" in tipo_2

        if is_partido_2:
            df_itens_2 = get_opcoes_partidos_recife(ano_2, turno_2, cargo_2)
            lbl_sel_2 = "Selecione o Partido 2:"
        else:
            df_itens_2 = get_opcoes_candidatos_recife(ano_2, turno_2, cargo_2)
            lbl_sel_2 = "Selecione o Candidato 2:"

        if len(df_itens_2) > 0:
            def_idx_2 = 0
            if not is_partido_2:
                for idx_i, row_i in df_itens_2.iterrows():
                    if "FRANCISMAR" in normalize_text(row_i['nome_urna']):
                        def_idx_2 = idx_i
                        break
            else:
                for idx_i, row_i in df_itens_2.iterrows():
                    if row_i['sigla_partido'] == "PSB":
                        def_idx_2 = idx_i
                        break
            sel_idx_2 = st.selectbox(
                lbl_sel_2,
                range(len(df_itens_2)),
                index=def_idx_2,
                format_func=lambda i: df_itens_2.iloc[i]['label'],
                key=f"m_rec_item_2_{ano_2}_{cargo_2}_{turno_2}_{tipo_2}"
            )
            item_2 = df_itens_2.iloc[sel_idx_2]
        else:
            st.warning("Nenhum dado encontrado para o Nível 2.")
            return

    # NÍVEL 3: PROPORCIONAL FEDERAL / PARCERIA
    with c3:
        st.markdown("#### 🔵 Nível 3: Federal / Parceria (Parlamentar 2)")
        st.caption("Deputado Federal ou Segunda Dobradinha")
        cc1, cc2, cc3 = st.columns([1, 1.4, 1])
        with cc1:
            def_ano3 = anos_disp.index(2026) if 2026 in anos_disp else 0
            ano_3 = st.selectbox("Ano 3:", anos_disp, index=def_ano3, key="m_rec_ano_3")
        with cc2:
            cgs_3 = sorted(df_meta[df_meta['ano'] == ano_3]['cargo'].unique())
            def_cg3 = cgs_3.index("deputado federal") if "deputado federal" in cgs_3 else 0
            cargo_3 = st.selectbox("Cargo 3:", cgs_3, index=def_cg3, key="m_rec_cg_3")
        with cc3:
            turnos_3 = sorted(df_meta[(df_meta['ano'] == ano_3) & (df_meta['cargo'] == cargo_3)]['turno'].unique())
            turno_3 = st.selectbox("Turno 3:", turnos_3, index=0, key="m_rec_t_3")

        tipo_3 = st.radio("Tipo 3:", ["👤 Candidato", "🚩 Soma do Partido"], horizontal=True, key=f"m_rec_tipo_3_{ano_3}_{cargo_3}_{turno_3}")
        is_partido_3 = "Partido" in tipo_3

        if is_partido_3:
            df_itens_3 = get_opcoes_partidos_recife(ano_3, turno_3, cargo_3)
            lbl_sel_3 = "Selecione o Partido 3:"
        else:
            df_itens_3 = get_opcoes_candidatos_recife(ano_3, turno_3, cargo_3)
            lbl_sel_3 = "Selecione o Candidato 3:"

        if len(df_itens_3) > 0:
            def_idx_3 = 0
            if not is_partido_3:
                for idx_i, row_i in df_itens_3.iterrows():
                    if "PEDRO CAMPOS" in normalize_text(row_i['nome_urna']):
                        def_idx_3 = idx_i
                        break
            else:
                for idx_i, row_i in df_itens_3.iterrows():
                    if row_i['sigla_partido'] == "PSB":
                        def_idx_3 = idx_i
                        break
            sel_idx_3 = st.selectbox(
                lbl_sel_3,
                range(len(df_itens_3)),
                index=def_idx_3,
                format_func=lambda i: df_itens_3.iloc[i]['label'],
                key=f"m_rec_item_3_{ano_3}_{cargo_3}_{turno_3}_{tipo_3}"
            )
            item_3 = df_itens_3.iloc[sel_idx_3]
        else:
            st.warning("Nenhum dado encontrado para o Nível 3.")
            return

    st.divider()

    # Nomes e identificadores para o cabeçalho e gráficos
    nome_display_1 = f"{item_1['nome_urna']} ({item_1['sigla_partido']}) [{ano_1}]"
    nome_display_2 = f"{item_2['nome_urna']} ({item_2['sigla_partido']}) [{ano_2}]"
    nome_display_3 = f"{item_3['nome_urna']} ({item_3['sigla_partido']}) [{ano_3}]"

    cor_1, _, _ = get_cores_foco(item_1['nome_urna'], item_1['sigla_partido'])
    cor_2, _, _ = get_cores_foco(item_2['nome_urna'], item_2['sigla_partido'])
    cor_3, _, _ = get_cores_foco(item_3['nome_urna'], item_3['sigla_partido'])

    # Ajuste de cores para máxima clareza e fidelidade partidária:
    # REGRA: Nenhum parlamentar da base / do PSB deve receber ROXO (cor exclusiva do PSD).
    sigla1_u = str(item_1['sigla_partido']).upper()
    sigla2_u = str(item_2['sigla_partido']).upper()
    sigla3_u = str(item_3['sigla_partido']).upper()

    # Se for PSB, usa o amarelo oficial #FEC806 para a majoritária
    if "PSB" in sigla1_u:
        cor_1 = "#FEC806"

    # Se os três forem do mesmo partido ou colidirem na mesma cor (ex: os 3 do PSB)
    if cor_1.lower() == cor_2.lower() and cor_2.lower() == cor_3.lower():
        cor_1 = "#FEC806"  # Amarelo PSB oficial (Majoritária / João Campos)
        cor_2 = "#FF8C00"  # Laranja vibrante (Estadual / Francismar)
        cor_3 = "#1F78B4"  # Azul Cobalto (Federal / Pedro Campos)
    else:
        # Se 1 e 2 colidirem
        if cor_1.lower() == cor_2.lower():
            if cor_1.lower() in ["#fec806", "#f1c40f", "#ffff33"]:
                cor_2 = "#FF8C00"  # Laranja se o 1 for amarelo
            else:
                cor_2 = "#1F78B4"  # Azul se o 1 for outra cor
        # Se 3 colidir com 1 ou 2, ou se 3 for roxo sem ser do PSD
        if cor_3.lower() in [cor_1.lower(), cor_2.lower()] or (cor_3.lower() in ["#9b59b6", "#8e44ad"] and "PSD" not in sigla3_u):
            paleta_segura = ["#1F78B4", "#27AE60", "#FF8C00", "#E31A1C", "#0055A5"]
            cores_livres = [c for c in paleta_segura if c.lower() not in [cor_1.lower(), cor_2.lower()]]
            cor_3 = cores_livres[0] if cores_livres else "#1F78B4"

    # -------------------------------------------------------------
    # 2. ESCOPO TERRITORIAL E FILTROS
    # -------------------------------------------------------------
    st.markdown("#### 🧭 Granularidade Territorial & Filtros no Recife")
    cf1, cf2, cf3 = st.columns([1.3, 1.4, 1.3])
    with cf1:
        granul_sel = st.selectbox(
            "Nível de Agregação:",
            ["🏘️ Bairros Oficiais (94 Bairros)", "🏫 Colégios Eleitorais (416 Locais)", "🗳️ Zonas Eleitorais (11 Zonas)"],
            index=0,
            key="m_rec_granul",
            help="Escolha a escala de observação: Bairros (análise sociodemográfica dos 94 bairros), Colégios (microeleitoral nas 416 escolas) ou Zonas Eleitorais (11 zonas do TRE-PE)."
        )
    with cf2:
        filtro_categ = st.selectbox(
            "Filtrar por Diagnóstico Político:",
            [
                "TODOS OS TERRITÓRIOS",
                "🤝 Aliança Plena / Voto Casado",
                "⚠️ Alerta de Vazamento / Descolamento",
                "🚀 Força Majoritária Autônoma",
                "🎯 Casamento Parcial (Majoritária + Parlamentar 1)",
                "🎯 Casamento Parcial (Majoritária + Parlamentar 2)",
                "🏜️ Vácuo da Chapa",
                "🔄 Descolamento Individual"
            ],
            index=0,
            key="m_rec_filtro_categ",
            help="Filtre territórios pela tipologia política: Aliança Plena (força total), Alerta de Vazamento (risco para a majoritária), Força Autônoma, Descolamento Individual (bolsão isolado de apenas um deputado), etc."
        )
    with cf3:
        termo_busca = st.text_input("🔍 Buscar Território:", placeholder="Ex: Boa Viagem, Madalena, Zona 4, Escola...", key="m_rec_busca")

    # -------------------------------------------------------------
    # 3. EXTRAÇÃO DUCKDB E AGREGAÇÃO
    # -------------------------------------------------------------
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")

    # Filtro 1
    if is_partido_1 or cargo_1 == "presidente" or pd.isna(item_1['numero_candidato']):
        sigla_1_clean = str(item_1['sigla_partido']).replace("'", "''")
        cond_1 = f"sigla_partido = '{sigla_1_clean}'"
    else:
        cond_1 = f"numero_candidato = {int(float(item_1['numero_candidato']))}"

    # Filtro 2
    if is_partido_2 or cargo_2 == "presidente" or pd.isna(item_2['numero_candidato']):
        sigla_2_clean = str(item_2['sigla_partido']).replace("'", "''")
        cond_2 = f"sigla_partido = '{sigla_2_clean}'"
    else:
        cond_2 = f"numero_candidato = {int(float(item_2['numero_candidato']))}"

    # Filtro 3
    if is_partido_3 or cargo_3 == "presidente" or pd.isna(item_3['numero_candidato']):
        sigla_3_clean = str(item_3['sigla_partido']).replace("'", "''")
        cond_3 = f"sigla_partido = '{sigla_3_clean}'"
    else:
        cond_3 = f"numero_candidato = {int(float(item_3['numero_candidato']))}"

    with st.spinner("Processando cruzamento territorial no Recife..."):
        if "Zonas" in granul_sel:
            q_agg = f"""
                WITH v1 AS (
                    SELECT zona,
                           SUM(total_votos) as total_1,
                           SUM(CASE WHEN {cond_1} THEN total_votos ELSE 0 END) as votos_1
                    FROM '{res_path}'
                    WHERE ano = {ano_1} AND turno = {turno_1} AND cargo = '{cargo_1}' AND (id_municipio = 2611606 OR (id_municipio = 2605459 AND zona = 4))
                    GROUP BY zona
                ),
                v2 AS (
                    SELECT zona,
                           SUM(total_votos) as total_2,
                           SUM(CASE WHEN {cond_2} THEN total_votos ELSE 0 END) as votos_2
                    FROM '{res_path}'
                    WHERE ano = {ano_2} AND turno = {turno_2} AND cargo = '{cargo_2}' AND (id_municipio = 2611606 OR (id_municipio = 2605459 AND zona = 4))
                    GROUP BY zona
                ),
                v3 AS (
                    SELECT zona,
                           SUM(total_votos) as total_3,
                           SUM(CASE WHEN {cond_3} THEN total_votos ELSE 0 END) as votos_3
                    FROM '{res_path}'
                    WHERE ano = {ano_3} AND turno = {turno_3} AND cargo = '{cargo_3}' AND (id_municipio = 2611606 OR (id_municipio = 2605459 AND zona = 4))
                    GROUP BY zona
                )
                SELECT 
                    COALESCE(v1.zona, v2.zona, v3.zona) as zona,
                    COALESCE(v1.votos_1, 0) as votos_1, COALESCE(v1.total_1, 0) as total_1,
                    COALESCE(v2.votos_2, 0) as votos_2, COALESCE(v2.total_2, 0) as total_2,
                    COALESCE(v3.votos_3, 0) as votos_3, COALESCE(v3.total_3, 0) as total_3
                FROM v1
                FULL OUTER JOIN v2 ON v1.zona = v2.zona
                FULL OUTER JOIN v3 ON COALESCE(v1.zona, v2.zona) = v3.zona
                ORDER BY zona ASC
            """
            df_territorios = con.execute(q_agg).df()
            df_territorios['unidade'] = df_territorios['zona'].apply(lambda z: f"Zona {z}")
            df_territorios['id_territorio'] = df_territorios['zona'].astype(str)

        else:
            # Para Bairros e Colégios, agrega primeiro por (zona, secao)
            q_secoes = f"""
                WITH v1 AS (
                    SELECT zona, secao,
                           SUM(total_votos) as total_1,
                           SUM(CASE WHEN {cond_1} THEN total_votos ELSE 0 END) as votos_1
                    FROM '{res_path}'
                    WHERE ano = {ano_1} AND turno = {turno_1} AND cargo = '{cargo_1}' AND id_municipio = 2611606
                    GROUP BY zona, secao
                ),
                v2 AS (
                    SELECT zona, secao,
                           SUM(total_votos) as total_2,
                           SUM(CASE WHEN {cond_2} THEN total_votos ELSE 0 END) as votos_2
                    FROM '{res_path}'
                    WHERE ano = {ano_2} AND turno = {turno_2} AND cargo = '{cargo_2}' AND id_municipio = 2611606
                    GROUP BY zona, secao
                ),
                v3 AS (
                    SELECT zona, secao,
                           SUM(total_votos) as total_3,
                           SUM(CASE WHEN {cond_3} THEN total_votos ELSE 0 END) as votos_3
                    FROM '{res_path}'
                    WHERE ano = {ano_3} AND turno = {turno_3} AND cargo = '{cargo_3}' AND id_municipio = 2611606
                    GROUP BY zona, secao
                )
                SELECT 
                    COALESCE(v1.zona, v2.zona, v3.zona) as zona,
                    COALESCE(v1.secao, v2.secao, v3.secao) as secao,
                    COALESCE(v1.votos_1, 0) as votos_1, COALESCE(v1.total_1, 0) as total_1,
                    COALESCE(v2.votos_2, 0) as votos_2, COALESCE(v2.total_2, 0) as total_2,
                    COALESCE(v3.votos_3, 0) as votos_3, COALESCE(v3.total_3, 0) as total_3
                FROM v1
                FULL OUTER JOIN v2 ON v1.zona = v2.zona AND v1.secao = v2.secao
                FULL OUTER JOIN v3 ON COALESCE(v1.zona, v2.zona) = v3.zona AND COALESCE(v1.secao, v2.secao) = v3.secao
            """
            df_secoes = con.execute(q_secoes).df()

            df_locais = get_locais_votacao_base()
            locais_recife = df_locais[df_locais['municipio'].str.upper() == 'RECIFE'].copy()
            merged_locais = locais_recife.merge(df_secoes, on=['zona', 'secao'], how='inner')

            if "Bairros" in granul_sel:
                gdf_bairros_geo = load_mosaico_bairros_gdf(cd_mun='2611606').copy()
                loc_coords = merged_locais.dropna(subset=['latitude', 'longitude']).copy()
                pts = gpd.points_from_xy(loc_coords['longitude'], loc_coords['latitude'])
                gdf_pts = gpd.GeoDataFrame(loc_coords, geometry=pts, crs="EPSG:4326")
                sj = gpd.sjoin(gdf_pts, gdf_bairros_geo[['NM_BAIRRO', 'geometry']], how='left', predicate='within')

                df_territorios = sj.groupby('NM_BAIRRO').agg(
                    votos_1=('votos_1', 'sum'),
                    total_1=('total_1', 'sum'),
                    votos_2=('votos_2', 'sum'),
                    total_2=('total_2', 'sum'),
                    votos_3=('votos_3', 'sum'),
                    total_3=('total_3', 'sum')
                ).reset_index()
                df_territorios['unidade'] = df_territorios['NM_BAIRRO']
                df_territorios['id_territorio'] = df_territorios['NM_BAIRRO']

            else:  # Colégios Eleitorais
                df_territorios = merged_locais.groupby(['id_local', 'nome_local', 'bairro', 'zona', 'latitude', 'longitude']).agg(
                    votos_1=('votos_1', 'sum'),
                    total_1=('total_1', 'sum'),
                    votos_2=('votos_2', 'sum'),
                    total_2=('total_2', 'sum'),
                    votos_3=('votos_3', 'sum'),
                    total_3=('total_3', 'sum'),
                    aptos=('aptos', 'sum')
                ).reset_index()
                df_territorios['unidade'] = df_territorios.apply(lambda r: f"{r['nome_local']} ({r['bairro']})", axis=1)
                df_territorios['id_territorio'] = df_territorios['id_local']

    if len(df_territorios) == 0:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # -------------------------------------------------------------
    # 4. CÁLCULO DAS MÉTRICAS DE MATCHING, QL E SCORE 3D
    # -------------------------------------------------------------
    df_territorios['pct_1'] = 100.0 * df_territorios['votos_1'] / df_territorios['total_1'].replace(0, np.nan)
    df_territorios['pct_2'] = 100.0 * df_territorios['votos_2'] / df_territorios['total_2'].replace(0, np.nan)
    df_territorios['pct_3'] = 100.0 * df_territorios['votos_3'] / df_territorios['total_3'].replace(0, np.nan)

    # Médias ponderadas no Recife
    sum_v1, sum_t1 = df_territorios['votos_1'].sum(), df_territorios['total_1'].sum()
    sum_v2, sum_t2 = df_territorios['votos_2'].sum(), df_territorios['total_2'].sum()
    sum_v3, sum_t3 = df_territorios['votos_3'].sum(), df_territorios['total_3'].sum()

    media_1 = 100.0 * sum_v1 / sum_t1 if sum_t1 > 0 else 1.0
    media_2 = 100.0 * sum_v2 / sum_t2 if sum_t2 > 0 else 1.0
    media_3 = 100.0 * sum_v3 / sum_t3 if sum_t3 > 0 else 1.0

    # Quocientes Locais (QL)
    df_territorios['ql_1'] = (df_territorios['pct_1'] / media_1).fillna(0.0).round(3)
    df_territorios['ql_2'] = (df_territorios['pct_2'] / media_2).fillna(0.0).round(3)
    df_territorios['ql_3'] = (df_territorios['pct_3'] / media_3).fillna(0.0).round(3)

    # Matching 3D Score: Raiz Cúbica do Produto dos QLs
    df_territorios['score_3d'] = np.cbrt(
        df_territorios['ql_1'].clip(lower=0.001) *
        df_territorios['ql_2'].clip(lower=0.001) *
        df_territorios['ql_3'].clip(lower=0.001)
    ).round(3)

    # Sinergia média dos deputados (QL 2 e 3)
    df_territorios['ql_dobradinha'] = ((df_territorios['ql_2'] + df_territorios['ql_3']) / 2.0).round(3)

    # Classificação Política Estratégica
    def categorizar_matching(r):
        q1, q2, q3 = r['ql_1'], r['ql_2'], r['ql_3']
        if q1 >= 1.0 and q2 >= 1.0 and q3 >= 1.0:
            return "🤝 Aliança Plena / Voto Casado"
        elif q2 >= 1.0 and q3 >= 1.0 and q1 < 1.0:
            return "⚠️ Alerta de Vazamento / Descolamento"
        elif q1 >= 1.0 and q2 < 1.0 and q3 < 1.0:
            return "🚀 Força Majoritária Autônoma"
        elif q1 >= 1.0 and q2 >= 1.0 and q3 < 1.0:
            return "🎯 Casamento Parcial (Majoritária + Parlamentar 1)"
        elif q1 >= 1.0 and q3 >= 1.0 and q2 < 1.0:
            return "🎯 Casamento Parcial (Majoritária + Parlamentar 2)"
        elif q1 < 1.0 and q2 < 1.0 and q3 < 1.0:
            return "🏜️ Vácuo da Chapa"
        else:
            return "🔄 Descolamento Individual"

    df_territorios['classificacao'] = df_territorios.apply(categorizar_matching, axis=1)

    cor_map_classes = {
        "🤝 Aliança Plena / Voto Casado": COR_ALIANCA_PLENA,
        "⚠️ Alerta de Vazamento / Descolamento": COR_ALERTA_VAZAMENTO,
        "🚀 Força Majoritária Autônoma": COR_MAJORITARIA_AUTO,
        "🎯 Casamento Parcial (Majoritária + Parlamentar 1)": COR_PARCIAL_ESTADUAL,
        "🎯 Casamento Parcial (Majoritária + Parlamentar 2)": COR_PARCIAL_FEDERAL,
        "🏜️ Vácuo da Chapa": COR_VACUO_CHAPA,
        "🔄 Descolamento Individual": COR_DESCOLAMENTO_IND
    }
    df_territorios['cor_class'] = df_territorios['classificacao'].map(cor_map_classes).fillna("#BDC3C7")

    # Correlações de Pearson
    clean_p = df_territorios.dropna(subset=['pct_1', 'pct_2', 'pct_3'])
    if len(clean_p) > 2:
        r_23 = clean_p['pct_2'].corr(clean_p['pct_3'])
        r_12 = clean_p['pct_1'].corr(clean_p['pct_2'])
        r_13 = clean_p['pct_1'].corr(clean_p['pct_3'])

        # Regressão Múltipla OLS: pct_1 ~ b0 + b1*pct_2 + b2*pct_3
        try:
            X = np.column_stack([np.ones(len(clean_p)), clean_p['pct_2'].values, clean_p['pct_3'].values])
            y = clean_p['pct_1'].values
            beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            y_pred = X @ beta
            ss_tot = np.sum((y - np.mean(y))**2)
            ss_res = np.sum((y - y_pred)**2)
            r2_val = max(0.0, 1.0 - (ss_res / ss_tot if ss_tot > 0 else 0.0))
        except Exception:
            beta = [0, 0, 0]
            r2_val = 0.0
    else:
        r_23, r_12, r_13, r2_val = 0.0, 0.0, 0.0, 0.0
        beta = [0, 0, 0]

    # Contagens de classes
    total_unidades = len(df_territorios)
    qtd_plena = (df_territorios['classificacao'] == "🤝 Aliança Plena / Voto Casado").sum()
    pct_plena = 100.0 * qtd_plena / total_unidades if total_unidades > 0 else 0.0
    qtd_vaz = (df_territorios['classificacao'] == "⚠️ Alerta de Vazamento / Descolamento").sum()
    pct_vaz = 100.0 * qtd_vaz / total_unidades if total_unidades > 0 else 0.0

    # -------------------------------------------------------------
    # 5. TOP CARDS DE KPIS
    # -------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric(
            "🔗 Sinergia da Dobradinha (r₂₃)",
            f"{r_23:.2f}",
            help="Correlação de Pearson entre os parlamentares 1 e 2. Mede se fazem campanha juntos e compartilham os mesmos territórios."
        )
    with k2:
        st.metric(
            "📈 Transferência p/ Majoritária (R²)",
            f"{r2_val * 100:.1f}%",
            help="Proporção da variação dos votos da majoritária explicada conjuntamente pela votação dos dois parlamentares."
        )
    with k3:
        st.metric(
            "🤝 Bastiões de Aliança Plena",
            f"{qtd_plena} ({pct_plena:.1f}%)",
            help="Territórios onde a majoritária e os dois deputados estão simultaneamente acima da média municipal (QL >= 1.0)."
        )
    with k4:
        st.metric(
            "⚠️ Alertas de Vazamento",
            f"{qtd_vaz} ({pct_vaz:.1f}%)",
            help="Territórios onde ambos os parlamentares são fortes (QL >= 1.0), mas a majoritária ficou abaixo da média (QL < 1.0)."
        )

    # -------------------------------------------------------------
    # 6. DIAGNÓSTICO ESTRATÉGICO EXECUTIVO
    # -------------------------------------------------------------
    if r_23 >= 0.70:
        diag_dobradinha = "**Dobradinha Altamente Integrada:** Os dois parlamentares caminham de mãos dadas no Recife, concentrando votos nos mesmos redutos."
    elif r_23 >= 0.40:
        diag_dobradinha = "**Dobradinha Moderada:** Existe sobreposição de bases territoriais, mas cada parlamentar preserva nichos próprios."
    else:
        diag_dobradinha = "**Dobradinha Desarticulada ou Complementar:** Os parlamentares atuam em territórios distintos do Recife, dividindo a cidade."

    if r2_val >= 0.50:
        diag_transf = f"**Forte Transferência Estrutural (R² = {r2_val*100:.1f}%):** A votação da liderança majoritária é fortemente ancorada na força territorial dos deputados."
    elif r2_val >= 0.25:
        diag_transf = f"**Transferência Mista (R² = {r2_val*100:.1f}%):** O voto da majoritária combina voto de opinião e o arranjo dos deputados."
    else:
        diag_transf = f"**Força Majoritária Autônoma (R² = {r2_val*100:.1f}%):** O candidato majoritário tem tração própria e descolada da votação proporcional dos deputados."

    vazamentos_df = df_territorios[df_territorios['classificacao'] == "⚠️ Alerta de Vazamento / Descolamento"].sort_values('ql_dobradinha', ascending=False)
    if len(vazamentos_df) > 0:
        top_vaz = ", ".join(vazamentos_df['unidade'].head(3).tolist())
        diag_alerta = f"**Atenção para Vazamento:** Em {len(vazamentos_df)} território(s) ({top_vaz}), os deputados entregaram forte votação mas a majoritária perdeu tração relativa."
    else:
        diag_alerta = "**Fidelidade Alta:** Nenhum ponto crítico de vazamento conjunto detectado nos parâmetros de quociente."

    st.info(f"💡 **Diagnóstico Executivo da Triangulação:**\n- {diag_dobradinha}\n- {diag_transf}\n- {diag_alerta}")

    # Filtrar dados para exibição cartográfica e tabular
    df_filtrado = df_territorios.copy()
    if filtro_categ != "TODOS OS TERRITÓRIOS":
        df_filtrado = df_filtrado[df_filtrado['classificacao'] == filtro_categ]
    if termo_busca:
        norm_busca = normalize_text(termo_busca)
        df_filtrado = df_filtrado[df_filtrado['unidade'].apply(lambda u: norm_busca in normalize_text(u))]

    # -------------------------------------------------------------
    # 7. MAPA CARTOGRÁFICO INTERATIVO (FOLIUM)
    # -------------------------------------------------------------
    st.markdown("#### 🗺️ Mapa Territorial da Triangulação no Recife")
    st.caption("Cores representam a categoria estratégica do território. Clique em cada área ou marcador para detalhes completos.")

    m = folium.Map(location=[-8.05, -34.90], zoom_start=12, tiles="OpenStreetMap")

    if "Bairros" in granul_sel:
        gdf_bairros_geo = load_mosaico_bairros_gdf(cd_mun='2611606').copy()
        gdf_map = gdf_bairros_geo.merge(df_territorios, left_on='NM_BAIRRO', right_on='NM_BAIRRO', how='inner')
        if filtro_categ != "TODOS OS TERRITÓRIOS":
            gdf_map = gdf_map[gdf_map['classificacao'] == filtro_categ]
        if termo_busca:
            norm_b = normalize_text(termo_busca)
            gdf_map = gdf_map[gdf_map['NM_BAIRRO'].apply(lambda b: norm_b in normalize_text(b))]

        for _, row in gdf_map.iterrows():
            c_bg = row['cor_class']
            c_txt = get_contrast_color(c_bg)
            popup_html = f"""
            <div style="font-family: sans-serif; width: 280px; font-size: 13px;">
                <h4 style="margin: 0 0 6px 0; color: #2C3E50;">🏘️ {row['NM_BAIRRO']}</h4>
                <div style="background-color: {c_bg}; color: {c_txt}; padding: 4px 8px; border-radius: 4px; font-weight: bold; margin-bottom: 8px;">
                    {row['classificacao']}
                </div>
                <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 6px; margin-bottom: 8px;">
                    <b>⭐ Matching 3D Score:</b> <span style="font-size: 14px; font-weight: bold; color: #2980B9;">{row['score_3d']:.2f}</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 3px 0;"><b>{nome_display_1}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_1'])} ({fmt_pct(row['pct_1'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_1'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_1']:.2f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 3px 0;"><b>{nome_display_2}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_2'])} ({fmt_pct(row['pct_2'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_2'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_2']:.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 3px 0;"><b>{nome_display_3}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_3'])} ({fmt_pct(row['pct_3'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_3'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_3']:.2f}</td>
                    </tr>
                </table>
            </div>
            """
            sim_geo = row['geometry'].simplify(0.0005, preserve_topology=True)
            folium.GeoJson(
                sim_geo,
                style_function=lambda x, c=c_bg: {
                    'fillColor': c,
                    'color': '#2C3E50',
                    'weight': 1.2,
                    'fillOpacity': 0.65
                },
                highlight_function=lambda x: {'weight': 3, 'color': '#000000', 'fillOpacity': 0.85},
                tooltip=f"<b>{row['NM_BAIRRO']}</b><br>{row['classificacao']}<br>Score 3D: {row['score_3d']:.2f}",
                popup=folium.Popup(popup_html, max_width=320)
            ).add_to(m)

    elif "Zonas" in granul_sel:
        gdf_zonas_geo = load_zonas_gdf(cd_mun='2611606').copy()
        gdf_zonas_geo['zona'] = gdf_zonas_geo['CD_ZONA'].astype(int)
        df_territorios['zona'] = df_territorios['zona'].astype(int)
        gdf_map = gdf_zonas_geo.merge(df_territorios, on='zona', how='inner')
        if filtro_categ != "TODOS OS TERRITÓRIOS":
            gdf_map = gdf_map[gdf_map['classificacao'] == filtro_categ]
        if termo_busca:
            norm_b = normalize_text(termo_busca)
            gdf_map = gdf_map[gdf_map['unidade'].apply(lambda u: norm_b in normalize_text(u))]

        for _, row in gdf_map.iterrows():
            c_bg = row['cor_class']
            c_txt = get_contrast_color(c_bg)
            popup_html = f"""
            <div style="font-family: sans-serif; width: 280px; font-size: 13px;">
                <h4 style="margin: 0 0 6px 0; color: #2C3E50;">🗳️ Zona {row['zona']} (Recife)</h4>
                <div style="background-color: {c_bg}; color: {c_txt}; padding: 4px 8px; border-radius: 4px; font-weight: bold; margin-bottom: 8px;">
                    {row['classificacao']}
                </div>
                <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 6px; margin-bottom: 8px;">
                    <b>⭐ Matching 3D Score:</b> <span style="font-size: 14px; font-weight: bold; color: #2980B9;">{row['score_3d']:.2f}</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 3px 0;"><b>{nome_display_1}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_1'])} ({fmt_pct(row['pct_1'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_1'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_1']:.2f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 3px 0;"><b>{nome_display_2}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_2'])} ({fmt_pct(row['pct_2'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_2'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_2']:.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 3px 0;"><b>{nome_display_3}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_3'])} ({fmt_pct(row['pct_3'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_3'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_3']:.2f}</td>
                    </tr>
                </table>
            </div>
            """
            sim_geo = row['geometry'].simplify(0.0005, preserve_topology=True)
            folium.GeoJson(
                sim_geo,
                style_function=lambda x, c=c_bg: {
                    'fillColor': c,
                    'color': '#2C3E50',
                    'weight': 1.5,
                    'fillOpacity': 0.65
                },
                highlight_function=lambda x: {'weight': 3, 'color': '#000000', 'fillOpacity': 0.85},
                tooltip=f"<b>Zona {row['zona']}</b><br>{row['classificacao']}<br>Score 3D: {row['score_3d']:.2f}",
                popup=folium.Popup(popup_html, max_width=320)
            ).add_to(m)

    else:  # Colégios Eleitorais
        df_loc_map = df_filtrado.dropna(subset=['latitude', 'longitude']).copy()
        for _, row in df_loc_map.iterrows():
            c_bg = row['cor_class']
            c_txt = get_contrast_color(c_bg)
            popup_html = f"""
            <div style="font-family: sans-serif; width: 290px; font-size: 13px;">
                <h4 style="margin: 0 0 4px 0; color: #2C3E50;">🏫 {row['nome_local']}</h4>
                <div style="font-size: 11px; color: #7F8C8D; margin-bottom: 6px;">📍 {row['bairro']} • Zona {row['zona']}</div>
                <div style="background-color: {c_bg}; color: {c_txt}; padding: 4px 8px; border-radius: 4px; font-weight: bold; margin-bottom: 8px;">
                    {row['classificacao']}
                </div>
                <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 6px; margin-bottom: 8px;">
                    <b>⭐ Matching 3D Score:</b> <span style="font-size: 14px; font-weight: bold; color: #2980B9;">{row['score_3d']:.2f}</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 3px 0;"><b>{nome_display_1}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_1'])} ({fmt_pct(row['pct_1'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_1'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_1']:.2f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 3px 0;"><b>{nome_display_2}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_2'])} ({fmt_pct(row['pct_2'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_2'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_2']:.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 3px 0;"><b>{nome_display_3}</b></td>
                        <td style="text-align: right;">{fmt_int(row['votos_3'])} ({fmt_pct(row['pct_3'])})</td>
                        <td style="text-align: right; color: {'#27AE60' if row['ql_3'] >= 1 else '#C0392B'}; font-weight: bold;">QL {row['ql_3']:.2f}</td>
                    </tr>
                </table>
            </div>
            """
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=6,
                color="#2C3E50",
                weight=1,
                fill=True,
                fill_color=c_bg,
                fill_opacity=0.85,
                tooltip=f"<b>{row['nome_local']}</b> ({row['bairro']})<br>{row['classificacao']}<br>Score 3D: {row['score_3d']:.2f}",
                popup=folium.Popup(popup_html, max_width=320)
            ).add_to(m)

    st_folium(
        m,
        key=f"folium_matching_rec_{granul_sel}_{filtro_categ}_{ano_1}_{cargo_1}_{ano_2}_{cargo_2}_{ano_3}_{cargo_3}",
        width=None,
        height=520,
        returned_objects=[]
    )

    # -------------------------------------------------------------
    # 8. GRÁFICOS PLOTLY (TOP BASTIÕES E DISPERSÃO ESTRATÉGICA)
    # -------------------------------------------------------------
    st.markdown("#### 📊 Análise Gráfica & Padrões Territoriais")
    tab_graf1, tab_graf2 = st.tabs(["🏆 Top Bastiões da Triangulação", "🎯 Matriz de Dispersão Estratégica (Dobradinha vs Majoritária)"])

    with tab_graf1:
        top10_score = df_filtrado.sort_values('score_3d', ascending=False).head(10).copy()
        if len(top10_score) > 0:
            top10_melt = top10_score.melt(
                id_vars=['unidade'],
                value_vars=['pct_1', 'pct_2', 'pct_3'],
                var_name='Nivel',
                value_name='Percentual'
            )
            top10_melt['Nivel'] = top10_melt['Nivel'].map({
                'pct_1': f"🟡 Majoritária: {item_1['nome_urna']}",
                'pct_2': f"🟠 Parlamentar 1: {item_2['nome_urna']}",
                'pct_3': f"🔵 Parlamentar 2: {item_3['nome_urna']}"
            })
            fig_bar = px.bar(
                top10_melt,
                x='Percentual',
                y='unidade',
                color='Nivel',
                barmode='group',
                orientation='h',
                color_discrete_sequence=[cor_1, cor_2, cor_3],
                title="Top 10 Territórios com Maior Sinergia Conjunta (Score 3D)"
            )
            fig_bar.update_layout(
                yaxis={'categoryorder': 'total ascending', 'tickfont': dict(size=9), 'automargin': True},
                xaxis_title="% dos Votos Válidos no Território",
                yaxis_title="",
                legend_title="",
                height=450,
                margin=dict(l=10, r=10, t=40, b=10),
                uniformtext=dict(minsize=8, mode='show')
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Nenhum registro para o filtro atual.")

    with tab_graf2:
        fig_scatter = px.scatter(
            df_territorios,
            x='ql_dobradinha',
            y='ql_1',
            color='classificacao',
            color_discrete_map=cor_map_classes,
            hover_name='unidade',
            hover_data={
                'ql_1': ':.2f',
                'ql_2': ':.2f',
                'ql_3': ':.2f',
                'score_3d': ':.2f',
                'votos_1': True
            },
            title="Matriz de Dispersão: Força da Dobradinha (QL Médio Parlamentar) vs Majoritária (QL 1)"
        )
        fig_scatter.add_vline(x=1.0, line_dash="dash", line_color="#7F8C8D", annotation_text="Média Dobradinha")
        fig_scatter.add_hline(y=1.0, line_dash="dash", line_color="#7F8C8D", annotation_text="Média Majoritária")
        fig_scatter.update_layout(
            xaxis_title="Força Média da Dobradinha Parlamentar (QL)",
            yaxis_title=f"Força da Majoritária: {item_1['nome_urna']} (QL)",
            height=480,
            margin=dict(l=10, r=10, t=40, b=10),
            legend_title="Categoria Estratégica"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # -------------------------------------------------------------
    # 9. DESTAQUES ESTRATÉGICOS (4 CARDS DETALHADOS)
    # -------------------------------------------------------------
    st.markdown("#### 🎯 Destaques Territoriais da Disputa")
    cd1, cd2, cd3, cd4 = st.columns(4)

    bastiao = df_territorios.sort_values('score_3d', ascending=False).iloc[0]
    with cd1:
        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; border-left: 4px solid {COR_ALIANCA_PLENA}; padding: 12px; border-radius: 4px;">
                <b style="color: {COR_ALIANCA_PLENA};">🏰 Bastião Supremo</b><br>
                <b>{bastiao['unidade']}</b><br>
                <small>Score 3D: <b>{bastiao['score_3d']:.2f}</b></small><br>
                <small>Majoritária: {fmt_pct(bastiao['pct_1'])} (QL {bastiao['ql_1']:.2f})</small><br>
                <small>Parlamentar 1: {fmt_pct(bastiao['pct_2'])} (QL {bastiao['ql_2']:.2f})</small><br>
                <small>Parlamentar 2: {fmt_pct(bastiao['pct_3'])} (QL {bastiao['ql_3']:.2f})</small>
            </div>
            """,
            unsafe_allow_html=True
        )

    df_alerta_vaz = df_territorios[df_territorios['classificacao'] == "⚠️ Alerta de Vazamento / Descolamento"]
    if len(df_alerta_vaz) > 0:
        maior_vaz = df_alerta_vaz.sort_values('ql_dobradinha', ascending=False).iloc[0]
        desc_vaz = f"""
            <b>{maior_vaz['unidade']}</b><br>
            <small>QL Dobradinha: <b>{maior_vaz['ql_dobradinha']:.2f}</b> | Majoritária: <b>{maior_vaz['ql_1']:.2f}</b></small><br>
            <small>Parlamentar 1: {fmt_pct(maior_vaz['pct_2'])}</small><br>
            <small>Parlamentar 2: {fmt_pct(maior_vaz['pct_3'])}</small><br>
            <small>Majoritária: {fmt_pct(maior_vaz['pct_1'])}</small>
        """
    else:
        desc_vaz = "<small>Nenhum vazamento identificado com os parâmetros atuais.</small>"

    with cd2:
        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; border-left: 4px solid {COR_ALERTA_VAZAMENTO}; padding: 12px; border-radius: 4px;">
                <b style="color: {COR_ALERTA_VAZAMENTO};">⚠️ Maior Ponto de Vazamento</b><br>
                {desc_vaz}
            </div>
            """,
            unsafe_allow_html=True
        )

    # Maior autonomia majoritária (alta majoritária com menor presença dos deputados)
    df_auto = df_territorios[df_territorios['ql_1'] >= 1.0].copy()
    if len(df_auto) > 0:
        df_auto['delta_auto'] = df_auto['ql_1'] - df_auto['ql_dobradinha']
        maior_auto = df_auto.sort_values('delta_auto', ascending=False).iloc[0]
        desc_auto = f"""
            <b>{maior_auto['unidade']}</b><br>
            <small>Majoritária: <b>{fmt_pct(maior_auto['pct_1'])}</b> (QL {maior_auto['ql_1']:.2f})</small><br>
            <small>QL Dobradinha: <b>{maior_auto['ql_dobradinha']:.2f}</b></small><br>
            <small>Voto autônomo e de opinião.</small>
        """
    else:
        desc_auto = "<small>Sem registros suficientes.</small>"

    with cd3:
        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; border-left: 4px solid {COR_MAJORITARIA_AUTO}; padding: 12px; border-radius: 4px;">
                <b style="color: {COR_MAJORITARIA_AUTO};">🚀 Autonomia Majoritária</b><br>
                {desc_auto}
            </div>
            """,
            unsafe_allow_html=True
        )

    # Dobradinha mais sincronizada e expressiva (menor diferença absoluta entre QL2 e QL3 com alta soma)
    df_sinc = df_territorios[(df_territorios['ql_2'] >= 1.0) & (df_territorios['ql_3'] >= 1.0)].copy()
    if len(df_sinc) > 0:
        df_sinc['diff_ql'] = np.abs(df_sinc['ql_2'] - df_sinc['ql_3'])
        mais_sinc = df_sinc.sort_values('diff_ql', ascending=True).iloc[0]
        desc_sinc = f"""
            <b>{mais_sinc['unidade']}</b><br>
            <small>Parlamentar 1: QL <b>{mais_sinc['ql_2']:.2f}</b></small><br>
            <small>Parlamentar 2: QL <b>{mais_sinc['ql_3']:.2f}</b></small><br>
            <small>Casamento perfeito entre os parlamentares.</small>
        """
    else:
        desc_sinc = "<small>Sem registros conjuntos acima da média.</small>"

    with cd4:
        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; border-left: 4px solid {COR_PARCIAL_ESTADUAL}; padding: 12px; border-radius: 4px;">
                <b style="color: {COR_PARCIAL_ESTADUAL};">⚖️ Dobradinha Mais Equilibrada</b><br>
                {desc_sinc}
            </div>
            """,
            unsafe_allow_html=True
        )

    # -------------------------------------------------------------
    # 10. TABELA ANALÍTICA COMPLETA & DOWNLOAD CSV
    # -------------------------------------------------------------
    st.markdown("#### 📋 Dados Analíticos Detalhados")
    cols_tabela = [
        'unidade',
        'classificacao',
        'score_3d',
        'votos_1', 'pct_1', 'ql_1',
        'votos_2', 'pct_2', 'ql_2',
        'votos_3', 'pct_3', 'ql_3'
    ]
    df_view = df_filtrado[cols_tabela].copy().sort_values('score_3d', ascending=False)
    df_view.rename(columns={
        'unidade': 'Território',
        'classificacao': 'Diagnóstico Estratégico',
        'score_3d': 'Matching 3D Score',
        'votos_1': f"Votos {item_1['nome_urna'][:15]}",
        'pct_1': f"% {item_1['nome_urna'][:15]}",
        'ql_1': f"QL {item_1['nome_urna'][:15]}",
        'votos_2': f"Votos {item_2['nome_urna'][:15]}",
        'pct_2': f"% {item_2['nome_urna'][:15]}",
        'ql_2': f"QL {item_2['nome_urna'][:15]}",
        'votos_3': f"Votos {item_3['nome_urna'][:15]}",
        'pct_3': f"% {item_3['nome_urna'][:15]}",
        'ql_3': f"QL {item_3['nome_urna'][:15]}"
    }, inplace=True)

    st.dataframe(df_view, use_container_width=True, hide_index=True)

    csv_data = df_view.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Baixar Dados em CSV",
        data=csv_data,
        file_name=f"matching_recife_3niveis_{ano_1}_{cargo_1}.csv",
        mime="text/csv"
    )
