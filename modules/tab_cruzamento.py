import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from config import PATH_RESULTADOS, PATH_LOCAIS_PARQUET, fmt_int, fmt_pct, get_cores_foco, normalize_text
from modules.geo_loader import load_municipios_gdf, load_regioes_gdf

PRESIDENTES_NOMES = {
    (2022, "PT"): "Lula",
    (2022, "PL"): "Jair Bolsonaro",
    (2022, "PDT"): "Ciro Gomes",
    (2022, "MDB"): "Simone Tebet",
    (2022, "UNIÃO"): "Soraya Thronicke",
    (2022, "NOVO"): "Felipe d'Avila",
    (2018, "PSL"): "Jair Bolsonaro",
    (2018, "PT"): "Fernando Haddad",
    (2018, "PDT"): "Ciro Gomes",
    (2018, "PSDB"): "Geraldo Alckmin",
    (2018, "NOVO"): "João Amoêdo",
    (2014, "PT"): "Dilma Rousseff",
    (2014, "PSDB"): "Aécio Neves",
    (2014, "PSB"): "Marina Silva",
    (2010, "PT"): "Dilma Rousseff",
    (2010, "PSDB"): "José Serra",
    (2010, "PV"): "Marina Silva"
}

@st.cache_data(ttl=3600)
def get_opcoes_candidatos_cruzamento(ano: int, turno: int, cargo: str):
    """Retorna candidatos ou partidos para o cargo selecionado com nomes normalizados."""
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    
    if cargo == "presidente":
        q = f"""
            SELECT sigla_partido, SUM(total_votos) as total_votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND sigla_partido IS NOT NULL
            GROUP BY sigla_partido
            ORDER BY total_votos DESC
        """
        df = con.execute(q).df()
        df['numero_candidato'] = None
        df['nome_urna'] = df['sigla_partido'].apply(lambda sigla: PRESIDENTES_NOMES.get((ano, sigla), f"Candidato ({sigla})"))
        df['label'] = df.apply(lambda r: f"{r['nome_urna']} ({r['sigla_partido']}) - {fmt_int(r['total_votos'])} votos", axis=1)
        return df
    else:
        q = f"""
            SELECT numero_candidato, nome_urna, sigla_partido, SUM(total_votos) as total_votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND numero_candidato IS NOT NULL
            GROUP BY numero_candidato, nome_urna, sigla_partido
            ORDER BY total_votos DESC
            LIMIT 100
        """
        df = con.execute(q).df()
        df['label'] = df.apply(lambda r: f"{r['nome_urna']} ({r['sigla_partido']}) - {fmt_int(r['total_votos'])} votos", axis=1)
        return df

def render_tab_cruzamento(df_meta, df_mun_map):
    st.markdown("### 🔗 Cruzamento Eleitoral & Análise de Dobradinhas")
    st.caption(
        "Compare o comportamento territorial de dois candidatos ou pleitos com normalização por **Quociente Eleitoral (QL)**, "
        "correlação de movimento e a **Matriz Estratégica dos 4 Quadrantes Politicos**."
    )
    
    # --- 1. CONFIGURAÇÃO DOS CANDIDATOS (A e B) ---
    c_box_a, c_box_b = st.columns(2)
    
    with c_box_a:
        st.markdown("#### 🔵 Candidato A (Referência / Eixo X)")
        ca1, ca2, ca3 = st.columns([1, 1.4, 1])
        with ca1:
            anos_a = sorted(df_meta['ano'].unique(), reverse=True)
            default_ano_a = anos_a.index(2022) if 2022 in anos_a else 0
            ano_a = st.selectbox("Ano A:", anos_a, index=default_ano_a, key="ano_a_cruz")
        with ca2:
            cargos_a = sorted(df_meta[df_meta['ano'] == ano_a]['cargo'].unique())
            default_cg_a = cargos_a.index("deputado federal") if "deputado federal" in cargos_a else 0
            cargo_a = st.selectbox("Cargo A:", cargos_a, index=default_cg_a, key="cg_a_cruz")
        with ca3:
            turnos_a = sorted(df_meta[(df_meta['ano'] == ano_a) & (df_meta['cargo'] == cargo_a)]['turno'].unique())
            turno_a = st.selectbox("Turno A:", turnos_a, index=0, key="t_a_cruz")
            
        df_cands_a = get_opcoes_candidatos_cruzamento(ano_a, turno_a, cargo_a)
        if len(df_cands_a) > 0:
            cand_idx_a = st.selectbox("Selecione o Candidato A:", range(len(df_cands_a)), format_func=lambda i: df_cands_a.iloc[i]['label'], key="sel_cand_a")
            info_a = df_cands_a.iloc[cand_idx_a]
        else:
            st.warning("Nenhum candidato encontrado para a Seleção A.")
            return

    with c_box_b:
        st.markdown("#### 🟣 Candidato B (Comparado / Eixo Y)")
        cb1, cb2, cb3 = st.columns([1, 1.4, 1])
        with cb1:
            anos_b = sorted(df_meta['ano'].unique(), reverse=True)
            default_ano_b = anos_b.index(2022) if 2022 in anos_b else 0
            ano_b = st.selectbox("Ano B:", anos_b, index=default_ano_b, key="ano_b_cruz")
        with cb2:
            cargos_b = sorted(df_meta[df_meta['ano'] == ano_b]['cargo'].unique())
            default_cg_b = cargos_b.index("governador") if "governador" in cargos_b else 0
            cargo_b = st.selectbox("Cargo B:", cargos_b, index=default_cg_b, key="cg_b_cruz")
        with cb3:
            turnos_b = sorted(df_meta[(df_meta['ano'] == ano_b) & (df_meta['cargo'] == cargo_b)]['turno'].unique())
            turno_b = st.selectbox("Turno B:", turnos_b, index=0, key="t_b_cruz")
            
        df_cands_b = get_opcoes_candidatos_cruzamento(ano_b, turno_b, cargo_b)
        if len(df_cands_b) > 0:
            cand_idx_b = st.selectbox("Selecione o Candidato B:", range(len(df_cands_b)), format_func=lambda i: df_cands_b.iloc[i]['label'], key="sel_cand_b")
            info_b = df_cands_b.iloc[cand_idx_b]
        else:
            st.warning("Nenhum candidato encontrado para a Seleção B.")
            return

    # Cores personalizadas para os candidatos
    cor_a, _, _ = get_cores_foco(info_a['nome_urna'], info_a['sigla_partido'])
    cor_b, _, _ = get_cores_foco(info_b['nome_urna'], info_b['sigla_partido'])
    if cor_a.lower() == cor_b.lower():
        cor_a = "#2980B9"  # Azul Cobalto
        cor_b = "#8E44AD"  # Roxo

    st.divider()

    # --- 2. ESCOPO GEOGRÁFICO E LENTE ANALÍTICA ---
    st.markdown("#### 🧭 Escopo Geográfico & Lente Analítica")
    cg1, cg2, cg3 = st.columns([1.2, 1.5, 1.3])
    
    with cg1:
        nivel_agreg = st.selectbox(
            "Nível Territorial:",
            ["🏛️ Municípios (185)", "🌍 Regiões de Desenvolvimento (12)", "🗳️ Zonas Eleitorais (209)", "🏫 Colégios Eleitorais (3.406)"],
            index=0,
            key="nivel_agreg_cruz"
        )
    with cg2:
        modo_analise_cruz = st.radio(
            "Lente Metodológica:",
            ["🎯 Sinergia Relativa (Quociente QL / Movimento)", "📊 Percentual Bruto (% Votos Válidos)"],
            horizontal=True,
            key="modo_analise_cruz",
            help=(
                "A Sinergia Relativa (QL) normaliza os votos em relação à própria média de cada candidato, "
                "permitindo comparar cargos de escalas muito diferentes (como Deputado vs Governador) "
                "sem que a escala maior engula a menor."
            )
        )
    with cg3:
        rds_todas = ["TODO O ESTADO"] + sorted(df_mun_map['REGIAO_DESENVOLVIMENTO'].unique().tolist())
        filtro_rd = st.selectbox("Filtrar Região de Desenvolvimento:", rds_todas, index=0, key="rd_cruz")

    # --- 3. CONSULTA SQL OTIMIZADA NO DUCKDB ---
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    locais_path = str(PATH_LOCAIS_PARQUET).replace("\\", "/")

    # Filtro Candidato A
    if cargo_a == "presidente":
        filtro_item_a = f"sigla_partido = '{info_a['sigla_partido']}'"
    else:
        filtro_item_a = f"numero_candidato = {int(info_a['numero_candidato'])}"

    # Filtro Candidato B
    if cargo_b == "presidente":
        filtro_item_b = f"sigla_partido = '{info_b['sigla_partido']}'"
    else:
        filtro_item_b = f"numero_candidato = {int(info_b['numero_candidato'])}"

    # Carregar dados com base no nível territorial
    with st.spinner("Calculando cruzamento territorial e métricas de sinergia..."):
        if "Municípios" in nivel_agreg or "Regiões" in nivel_agreg:
            q = f"""
                WITH va AS (
                    SELECT 
                        id_municipio,
                        SUM(total_votos) as total_a,
                        SUM(CASE WHEN {filtro_item_a} THEN total_votos ELSE 0 END) as v_a
                    FROM '{res_path}'
                    WHERE ano = {ano_a} AND turno = {turno_a} AND cargo = '{cargo_a}'
                    GROUP BY id_municipio
                ),
                vb AS (
                    SELECT 
                        id_municipio,
                        SUM(total_votos) as total_b,
                        SUM(CASE WHEN {filtro_item_b} THEN total_votos ELSE 0 END) as v_b
                    FROM '{res_path}'
                    WHERE ano = {ano_b} AND turno = {turno_b} AND cargo = '{cargo_b}'
                    GROUP BY id_municipio
                )
                SELECT 
                    COALESCE(va.id_municipio, vb.id_municipio) as CD_MUN,
                    COALESCE(va.v_a, 0) as votos_a,
                    COALESCE(va.total_a, 0) as total_a,
                    COALESCE(vb.v_b, 0) as votos_b,
                    COALESCE(vb.total_b, 0) as total_b
                FROM va
                FULL OUTER JOIN vb ON va.id_municipio = vb.id_municipio
            """
            df_res = con.execute(q).df()
            df_res['CD_MUN'] = df_res['CD_MUN'].astype(str)
            df_res = df_res.merge(df_mun_map[['CD_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO']], on='CD_MUN', how='left')

            if "Regiões" in nivel_agreg:
                df_cruz = df_res.groupby('REGIAO_DESENVOLVIMENTO').agg(
                    votos_a=('votos_a', 'sum'),
                    total_a=('total_a', 'sum'),
                    votos_b=('votos_b', 'sum'),
                    total_b=('total_b', 'sum')
                ).reset_index()
                df_cruz['unidade'] = df_cruz['REGIAO_DESENVOLVIMENTO']
                df_cruz['regiao'] = df_cruz['REGIAO_DESENVOLVIMENTO']
            else:
                df_cruz = df_res.copy()
                df_cruz['unidade'] = df_cruz['NM_MUN']
                df_cruz['regiao'] = df_cruz['REGIAO_DESENVOLVIMENTO']

        elif "Zonas" in nivel_agreg:
            q = f"""
                WITH va AS (
                    SELECT 
                        id_municipio, zona,
                        SUM(total_votos) as total_a,
                        SUM(CASE WHEN {filtro_item_a} THEN total_votos ELSE 0 END) as v_a
                    FROM '{res_path}'
                    WHERE ano = {ano_a} AND turno = {turno_a} AND cargo = '{cargo_a}'
                    GROUP BY id_municipio, zona
                ),
                vb AS (
                    SELECT 
                        id_municipio, zona,
                        SUM(total_votos) as total_b,
                        SUM(CASE WHEN {filtro_item_b} THEN total_votos ELSE 0 END) as v_b
                    FROM '{res_path}'
                    WHERE ano = {ano_b} AND turno = {turno_b} AND cargo = '{cargo_b}'
                    GROUP BY id_municipio, zona
                )
                SELECT 
                    COALESCE(va.id_municipio, vb.id_municipio) as CD_MUN,
                    COALESCE(va.zona, vb.zona) as zona,
                    COALESCE(va.v_a, 0) as votos_a,
                    COALESCE(va.total_a, 0) as total_a,
                    COALESCE(vb.v_b, 0) as votos_b,
                    COALESCE(vb.total_b, 0) as total_b
                FROM va
                FULL OUTER JOIN vb ON va.id_municipio = vb.id_municipio AND va.zona = vb.zona
            """
            df_res = con.execute(q).df()
            df_res['CD_MUN'] = df_res['CD_MUN'].astype(str)
            df_res = df_res.merge(df_mun_map[['CD_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO']], on='CD_MUN', how='left')
            df_res['unidade'] = df_res.apply(lambda r: f"Zona {r['zona']} ({r['NM_MUN']})", axis=1)
            df_res['regiao'] = df_res['REGIAO_DESENVOLVIMENTO']
            df_cruz = df_res.copy()

        else: # Colégios Eleitorais
            q = f"""
                WITH sa AS (
                    SELECT 
                        zona, secao,
                        SUM(total_votos) as total_a,
                        SUM(CASE WHEN {filtro_item_a} THEN total_votos ELSE 0 END) as v_a
                    FROM '{res_path}'
                    WHERE ano = {ano_a} AND turno = {turno_a} AND cargo = '{cargo_a}'
                    GROUP BY zona, secao
                ),
                sb AS (
                    SELECT 
                        zona, secao,
                        SUM(total_votos) as total_b,
                        SUM(CASE WHEN {filtro_item_b} THEN total_votos ELSE 0 END) as v_b
                    FROM '{res_path}'
                    WHERE ano = {ano_b} AND turno = {turno_b} AND cargo = '{cargo_b}'
                    GROUP BY zona, secao
                ),
                loc AS (
                    SELECT DISTINCT id_local, nome_local, bairro, municipio, zona, secao
                    FROM '{locais_path}'
                )
                SELECT 
                    loc.id_local,
                    loc.nome_local,
                    loc.bairro,
                    loc.municipio as NM_MUN,
                    SUM(COALESCE(sa.v_a, 0)) as votos_a,
                    SUM(COALESCE(sa.total_a, 0)) as total_a,
                    SUM(COALESCE(sb.v_b, 0)) as votos_b,
                    SUM(COALESCE(sb.total_b, 0)) as total_b
                FROM loc
                LEFT JOIN sa ON loc.zona = sa.zona AND loc.secao = sa.secao
                LEFT JOIN sb ON loc.zona = sb.zona AND loc.secao = sb.secao
                GROUP BY loc.id_local, loc.nome_local, loc.bairro, loc.municipio
                HAVING (total_a > 0 OR total_b > 0)
            """
            df_res = con.execute(q).df()
            df_res = df_res.merge(df_mun_map[['NM_MUN', 'REGIAO_DESENVOLVIMENTO']].drop_duplicates(), on='NM_MUN', how='left')
            df_res['unidade'] = df_res.apply(lambda r: f"{r['nome_local']} ({r['bairro']} - {r['NM_MUN']})", axis=1)
            df_res['regiao'] = df_res['REGIAO_DESENVOLVIMENTO'].fillna("OUTRA")
            df_cruz = df_res.copy()

    # Filtro por Região de Desenvolvimento
    if filtro_rd != "TODO O ESTADO":
        df_cruz = df_cruz[df_cruz['regiao'] == filtro_rd]

    if len(df_cruz) == 0:
        st.warning("Nenhum dado encontrado para o filtro regional selecionado.")
        return

    # --- 4. ENGENHARIA DE FEATURES: QUOCIENTE ELEITORAL (QL) E MATRIZ ESTRATÉGICA ---
    # Percentuais brutos
    df_cruz['pct_a'] = (100.0 * df_cruz['votos_a'] / df_cruz['total_a'].replace(0, 1)).round(2)
    df_cruz['pct_b'] = (100.0 * df_cruz['votos_b'] / df_cruz['total_b'].replace(0, 1)).round(2)
    df_cruz['votos_validos_unidade'] = df_cruz[['total_a', 'total_b']].max(axis=1)

    # Médias ponderadas no recorte
    tot_val_a = df_cruz['total_a'].sum()
    tot_val_b = df_cruz['total_b'].sum()
    media_a = (100.0 * df_cruz['votos_a'].sum() / tot_val_a) if tot_val_a > 0 else df_cruz['pct_a'].mean()
    media_b = (100.0 * df_cruz['votos_b'].sum() / tot_val_b) if tot_val_b > 0 else df_cruz['pct_b'].mean()

    # Quociente Eleitoral (QL): Desempenho relativo à própria média do candidato
    df_cruz['ql_a'] = (df_cruz['pct_a'] / (media_a if media_a > 0 else 1.0)).round(3)
    df_cruz['ql_b'] = (df_cruz['pct_b'] / (media_b if media_b > 0 else 1.0)).round(3)

    # Score de Sinergia = Produto dos Quocientes Relativos (QL_A * QL_B)
    df_cruz['score_sinergia'] = (df_cruz['ql_a'] * df_cruz['ql_b']).round(3)

    # Descompasso Relativo = QL_A - QL_B (unidades adimensionais de força intra-candidato)
    df_cruz['descompasso_ql'] = (df_cruz['ql_a'] - df_cruz['ql_b']).round(3)

    # Classificação nos 4 Quadrantes Estratégicos
    def classificar_quadrante(r):
        if r['ql_a'] >= 1.0 and r['ql_b'] >= 1.0:
            return "🤝 Dobradinha Fiel (Ambos Acima da Média)"
        elif r['ql_a'] < 1.0 and r['ql_b'] >= 1.0:
            return f"⚡ Reduto de {info_b['nome_urna']} (B Forte / A Fraco)"
        elif r['ql_a'] >= 1.0 and r['ql_b'] < 1.0:
            return f"🚀 Reduto de {info_a['nome_urna']} (A Forte / B Fraco)"
        else:
            return "🏜️ Vácuo Eleitoral (Ambos Abaixo da Média)"

    df_cruz['quadrante'] = df_cruz.apply(classificar_quadrante, axis=1)

    # Cores fixas da Matriz Estratégica
    lbl_dobradinha = "🤝 Dobradinha Fiel (Ambos Acima da Média)"
    lbl_reduto_b = f"⚡ Reduto de {info_b['nome_urna']} (B Forte / A Fraco)"
    lbl_reduto_a = f"🚀 Reduto de {info_a['nome_urna']} (A Forte / B Fraco)"
    lbl_vacuo = "🏜️ Vácuo Eleitoral (Ambos Abaixo da Média)"

    cores_quadrantes = {
        lbl_dobradinha: "#27AE60",   # Verde Esmeralda
        lbl_reduto_a: cor_a,         # Cor do Candidato A
        lbl_reduto_b: cor_b,         # Cor do Candidato B
        lbl_vacuo: "#95A5A6"         # Cinza
    }

    # Estatísticas de Território
    total_unidades = len(df_cruz)
    n_dobradinha = len(df_cruz[df_cruz['quadrante'] == lbl_dobradinha])
    n_reduto_a = len(df_cruz[df_cruz['quadrante'] == lbl_reduto_a])
    n_reduto_b = len(df_cruz[df_cruz['quadrante'] == lbl_reduto_b])
    n_divergentes = n_reduto_a + n_reduto_b
    n_vacuo = len(df_cruz[df_cruz['quadrante'] == lbl_vacuo])

    taxa_dobradinha = (n_dobradinha / total_unidades) * 100.0 if total_unidades > 0 else 0.0
    taxa_divergencia = (n_divergentes / total_unidades) * 100.0 if total_unidades > 0 else 0.0

    # Correlações Estatísticas
    corr_pearson = float(df_cruz['pct_a'].corr(df_cruz['pct_b'], method='pearson'))
    corr_spearman = float(df_cruz['pct_a'].corr(df_cruz['pct_b'], method='spearman'))
    r2 = (corr_pearson ** 2) * 100.0

    # Diagnóstico Político Estratégico
    if taxa_divergencia >= 50.0 or corr_pearson <= -0.20:
        diag_badge = "🔴 Antagonismo Territorial / Eleitorados Concorrentes"
        diag_desc = (
            f"As bases eleitorais de {info_a['nome_urna']} e {info_b['nome_urna']} operam em direções opostas. "
            f"Em **{taxa_divergencia:.1f}%** das praças analisadas, o fortalecimento de um coincide com o enfraquecimento do outro. "
            f"A correlação linear de votos é negativa ({corr_pearson:+.2f})."
        )
    elif corr_spearman >= 0.40 or (taxa_dobradinha >= 35.0 and corr_pearson >= 0.25):
        diag_badge = "🟢 Sólida Parceria / Dobradinha Consolidada"
        diag_desc = (
            f"Há forte sintonia espacial ({corr_spearman:+.2f} de correlação de postos). "
            f"Em **{taxa_dobradinha:.1f}%** das praças, ambos superam simultaneamente a média de seus cargos, "
            f"indicando forte simbiose eleitoral e transferência mútua de votos."
        )
    elif corr_pearson >= 0.15:
        diag_badge = "🟡 Sinergia Seletiva / Casamentos Pontuais"
        diag_desc = (
            f"As bases compartilham afinidades moderadas ({corr_pearson:+.2f}), porém com casamentos concentrados "
            f"em regiões específicas, mantendo autonomia eleitoral no restante do território."
        )
    else:
        diag_badge = "⚪ Campanhas Descoladas / Eleitorados Independentes"
        diag_desc = (
            f"Correlação próxima de zero ({corr_pearson:+.2f}). A distribuição de votos dos candidatos é autônoma, "
            f"sem alinhamento sistemático nem disputa predatória evidente no mapa."
        )

    # --- 5. PAINEL DE KPIS ESTRATÉGICOS ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Sintonia de Movimento (Spearman ρ)",
        f"{corr_spearman:+.3f}",
        help="Mede se a ordem das melhores cidades de A bate com a ordem das melhores de B, independente de disputarem cargos de tamanhos diferentes."
    )
    k2.metric(
        "Correlação Linear (Pearson r)",
        f"{corr_pearson:+.3f}",
        help="Mede a associação linear direta entre os percentuais de votos nas unidades territoriais."
    )
    k3.metric(
        "Co-ocorrência de Redutos",
        f"{taxa_dobradinha:.1f}%",
        f"{n_dobradinha} de {total_unidades} unidades",
        help="Percentual de territórios onde AMBOS superam simultaneamente a sua própria média (QL > 1.0)."
    )
    k4.metric(
        "Taxa de Divergência",
        f"{taxa_divergencia:.1f}%",
        f"{n_divergentes} de {total_unidades} unidades",
        delta_color="inverse",
        help="Percentual de territórios onde um candidato sobreperforma e o outro subperforma (redutos antagônicos)."
    )

    st.info(f"**Diagnóstico Estratégico:** {diag_badge}\n\n{diag_desc}")
    st.divider()

    # --- 6. GRÁFICOS: MATRIZ DE QUADRANTES & TOP DOBRADINHAS REAIS ---
    c_graf1, c_graf2 = st.columns([1.35, 0.65])
    
    # Definir eixos de acordo com a lente metodológica
    is_sinergia = "Sinergia Relativa" in modo_analise_cruz

    if is_sinergia:
        x_col = 'ql_a'
        y_col = 'ql_b'
        x_ref = 1.0
        y_ref = 1.0
        x_titulo = f"Desempenho Relativo ({info_a['nome_urna']}) [1.0x = Média]"
        y_titulo = f"Desempenho Relativo ({info_b['nome_urna']}) [1.0x = Média]"
    else:
        x_col = 'pct_a'
        y_col = 'pct_b'
        x_ref = media_a
        y_ref = media_b
        x_titulo = f"% Votos Válidos: {info_a['nome_urna']} (Média: {fmt_pct(media_a)})"
        y_titulo = f"% Votos Válidos: {info_b['nome_urna']} (Média: {fmt_pct(media_b)})"

    with c_graf1:
        st.markdown("#### 🎯 Matriz Política dos 4 Quadrantes")
        st.caption(
            "Cada ponto representa uma unidade territorial dividida pela linha média de força de cada candidato:"
        )

        # Gráfico de Dispersão dos Quadrantes
        fig_scatter = px.scatter(
            df_cruz,
            x=x_col,
            y=y_col,
            color='quadrante',
            color_discrete_map=cores_quadrantes,
            size='votos_validos_unidade',
            hover_name='unidade',
            hover_data={
                x_col: False,
                y_col: False,
                'quadrante': True,
                'votos_a': True,
                'pct_a': True,
                'ql_a': True,
                'votos_b': True,
                'pct_b': True,
                'ql_b': True,
                'score_sinergia': True,
                'regiao': True
            },
            labels={
                'quadrante': 'Classificação Estratégica',
                'votos_a': f'Votos Nominais ({info_a["nome_urna"]})',
                'pct_a': f'% Válidos ({info_a["nome_urna"]})',
                'ql_a': f'Múltiplo da Média ({info_a["nome_urna"]})',
                'votos_b': f'Votos Nominais ({info_b["nome_urna"]})',
                'pct_b': f'% Válidos ({info_b["nome_urna"]})',
                'ql_b': f'Múltiplo da Média ({info_b["nome_urna"]})',
                'score_sinergia': 'Score de Sinergia (QL_A × QL_B)',
                'regiao': 'Região de Desenvolvimento'
            }
        )

        # Linhas de Divisão dos Quadrantes
        fig_scatter.add_vline(x=x_ref, line_dash="dash", line_color="#7F8C8D", line_width=1.5)
        fig_scatter.add_hline(y=y_ref, line_dash="dash", line_color="#7F8C8D", line_width=1.5)

        # Linha de Tendência OLS (Regressão)
        x_vals = df_cruz[x_col].values
        y_vals = df_cruz[y_col].values
        if len(df_cruz) > 1 and np.std(x_vals) > 0 and np.std(y_vals) > 0:
            m_slope, b_intercept = np.polyfit(x_vals, y_vals, 1)
            x_line = np.linspace(x_vals.min(), x_vals.max(), 50)
            y_line = m_slope * x_line + b_intercept
            fig_scatter.add_trace(
                go.Scatter(
                    x=x_line,
                    y=y_line,
                    mode='lines',
                    name='Tendência (Regressão)',
                    line=dict(color='#2C3E50', dash='dot', width=2)
                )
            )

        # Rótulos dos Quadrantes
        max_x = df_cruz[x_col].max()
        max_y = df_cruz[y_col].max()
        min_x = df_cruz[x_col].min()
        min_y = df_cruz[y_col].min()

        fig_scatter.update_layout(
            height=510,
            xaxis_title=x_titulo,
            yaxis_title=y_titulo,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with c_graf2:
        st.markdown("#### 🤝 Top Dobradinhas Reais")
        st.caption("Unidades com maior sinergia relativa simultânea (QL_A × QL_B):")
        
        top_casados = df_cruz.sort_values('score_sinergia', ascending=False).head(8).copy()
        top_casados['texto_barra_a'] = top_casados.apply(lambda r: f"{fmt_pct(r['pct_a'])} ({r['ql_a']:.1f}x)", axis=1)
        top_casados['texto_barra_b'] = top_casados.apply(lambda r: f"{fmt_pct(r['pct_b'])} ({r['ql_b']:.1f}x)", axis=1)

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=top_casados['unidade'],
            x=top_casados['ql_a'],
            text=top_casados['texto_barra_a'],
            textposition='auto',
            name=f"{info_a['nome_urna']} (x Média)",
            orientation='h',
            marker=dict(color=cor_a)
        ))
        fig_bar.add_trace(go.Bar(
            y=top_casados['unidade'],
            x=top_casados['ql_b'],
            text=top_casados['texto_barra_b'],
            textposition='auto',
            name=f"{info_b['nome_urna']} (x Média)",
            orientation='h',
            marker=dict(color=cor_b)
        ))
        fig_bar.add_vline(x=1.0, line_dash="dash", line_color="#7F8C8D", line_width=1.5)
        fig_bar.update_layout(
            barmode='group',
            height=510,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5),
            xaxis_title="Múltiplo da Própria Média (1.0x = Média)",
            yaxis=dict(autorange="reversed")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- 7. DESTAQUES ESTRATÉGICOS (CARDS) ---
    st.markdown("#### 🎯 Destaques Territoriais da Parceria")
    d1, d2, d3, d4 = st.columns(4)
    
    # 1. Maior Sinergia Conjunta
    top1 = df_cruz.sort_values('score_sinergia', ascending=False).iloc[0]
    with d1:
        st.success(
            f"🤝 **Maior Casamento / Sinergia**\n\n"
            f"**{top1['unidade']}**\n\n"
            f"• {info_a['nome_urna']}: **{fmt_pct(top1['pct_a'])}** ({top1['ql_a']:.2f}x média)\n\n"
            f"• {info_b['nome_urna']}: **{fmt_pct(top1['pct_b'])}** ({top1['ql_b']:.2f}x média)\n\n"
            f"• Sinergia Conjunta: **{top1['score_sinergia']:.2f} pts**"
        )

    # 2. Bastião de A (onde A mais superou sua média em relação a B)
    top_bast_a = df_cruz.sort_values('descompasso_ql', ascending=False).iloc[0]
    with d2:
        st.info(
            f"🚀 **Fortaleza Exclusiva de {info_a['nome_urna']}**\n\n"
            f"**{top_bast_a['unidade']}**\n\n"
            f"• {info_a['nome_urna']}: **{fmt_pct(top_bast_a['pct_a'])}** ({top_bast_a['ql_a']:.2f}x média)\n\n"
            f"• {info_b['nome_urna']}: **{fmt_pct(top_bast_a['pct_b'])}** ({top_bast_a['ql_b']:.2f}x média)\n\n"
            f"• Vantagem Relativa: **+{top_bast_a['descompasso_ql']:.2f}x**"
        )

    # 3. Bastião de B (onde B mais superou sua média em relação a A)
    top_bast_b = df_cruz.sort_values('descompasso_ql', ascending=True).iloc[0]
    with d3:
        st.warning(
            f"⚡ **Fortaleza Exclusiva de {info_b['nome_urna']}**\n\n"
            f"**{top_bast_b['unidade']}**\n\n"
            f"• {info_b['nome_urna']}: **{fmt_pct(top_bast_b['pct_b'])}** ({top_bast_b['ql_b']:.2f}x média)\n\n"
            f"• {info_a['nome_urna']}: **{fmt_pct(top_bast_b['pct_a'])}** ({top_bast_b['ql_a']:.2f}x média)\n\n"
            f"• Vantagem Relativa: **+{-top_bast_b['descompasso_ql']:.2f}x**"
        )

    # 4. Resumo da Distribuição
    with d4:
        st.metric(
            "Balanço de Redutos",
            f"{n_dobradinha} Casados",
            f"{n_divergentes} Divergentes",
            help="Mostra a contagem de territórios onde ambos superam suas médias vs onde caminham em sentidos opostos."
        )
        st.caption(
            f"• **{n_reduto_a}** redutos só de {info_a['nome_urna']}\n\n"
            f"• **{n_reduto_b}** redutos só de {info_b['nome_urna']}\n\n"
            f"• **{n_vacuo}** cidades com ambos fracos"
        )

    # --- 8. TABELA ANALÍTICA COMPLETA COM BUSCA E DOWNLOAD ---
    st.markdown("#### 📋 Tabela Analítica Completa")
    busca_tab = st.text_input("🔍 Filtrar tabela por nome da unidade:", placeholder="Digite o nome para filtrar...", key="busca_tab_cruz")
    
    df_tab = df_cruz.copy()
    if busca_tab.strip():
        q_tab = normalize_text(busca_tab)
        df_tab = df_tab[df_tab['unidade'].apply(lambda x: q_tab in normalize_text(x))]
        
    df_tab_view = df_tab.sort_values('score_sinergia', ascending=False).copy()
    df_tab_view['Votos A'] = df_tab_view['votos_a'].apply(fmt_int)
    df_tab_view['% Votos A'] = df_tab_view['pct_a'].apply(fmt_pct)
    df_tab_view['Desempenho A (QL)'] = df_tab_view['ql_a'].apply(lambda v: f"{v:.2f}x".replace(".", ","))
    df_tab_view['Votos B'] = df_tab_view['votos_b'].apply(fmt_int)
    df_tab_view['% Votos B'] = df_tab_view['pct_b'].apply(fmt_pct)
    df_tab_view['Desempenho B (QL)'] = df_tab_view['ql_b'].apply(lambda v: f"{v:.2f}x".replace(".", ","))
    df_tab_view['Sinergia (Score)'] = df_tab_view['score_sinergia'].apply(lambda v: f"{v:.2f}".replace(".", ","))

    cols_show = [
        'unidade', 'regiao', 'quadrante',
        'Votos A', '% Votos A', 'Desempenho A (QL)',
        'Votos B', '% Votos B', 'Desempenho B (QL)',
        'Sinergia (Score)'
    ]

    st.dataframe(
        df_tab_view[cols_show].rename(columns={
            'unidade': 'Unidade Territorial',
            'regiao': 'Região de Desenvolvimento',
            'quadrante': 'Quadrante Estratégico',
            'Votos A': f'Votos ({info_a["nome_urna"]})',
            '% Votos A': f'% ({info_a["nome_urna"]})',
            'Desempenho A (QL)': f'Múltiplo ({info_a["nome_urna"]})',
            'Votos B': f'Votos ({info_b["nome_urna"]})',
            '% Votos B': f'% ({info_b["nome_urna"]})',
            'Desempenho B (QL)': f'Múltiplo ({info_b["nome_urna"]})',
            'Sinergia (Score)': 'Score Sinergia'
        }),
        use_container_width=True,
        hide_index=True
    )

    # Download CSV formatado
    csv_bytes = df_tab_view[cols_show].to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Exportar Dados do Cruzamento (.CSV)",
        data=csv_bytes,
        file_name=f"cruzamento_{normalize_text(info_a['nome_urna'])}_{normalize_text(info_b['nome_urna'])}.csv",
        mime="text/csv"
    )
