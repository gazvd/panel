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
    """Retorna candidatos ou partidos para o cargo selecionado."""
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
    st.caption("Cruze os dados de dois candidatos distintos (mesmo pleito ou pleitos diferentes), analise correlações territoriais e investigue votos casados.")
    
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

    st.divider()

    # --- 2. CONFIGURAÇÃO DO RECORTE E NÍVEL DE AGREGAÇÃO ---
    st.markdown("#### 🧭 Escopo Geográfico & Agregação")
    cg1, cg2, cg3 = st.columns([1.2, 1.2, 1.6])
    
    with cg1:
        nivel_agreg = st.selectbox(
            "Nível Territorial:",
            ["🏛️ Municípios (185)", "🌍 Regiões de Desenvolvimento (12)", "🗳️ Zonas Eleitorais (209)", "🏫 Colégios Eleitorais (3.406)"],
            index=0,
            key="nivel_agreg_cruz"
        )
    with cg2:
        metrica_cruz = st.radio(
            "Métrica de Comparação:",
            ["Percentual (% Votos Válidos)", "Total de Votos (Nominais)"],
            horizontal=True,
            key="metrica_cruz"
        )
    with cg3:
        rds_todas = ["TODO O ESTADO"] + sorted(df_mun_map['REGIAO_DESENVOLVIMENTO'].unique().tolist())
        filtro_rd = st.selectbox("Filtrar Região de Desenvolvimento:", rds_todas, index=0, key="rd_cruz")

    # --- 3. CONSULTA SQL OTIMIZADA NO DUCKDB ---
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    locais_path = str(PATH_LOCAIS_PARQUET).replace("\\", "/")

    # Filtro de Candidato A
    if cargo_a == "presidente":
        filtro_item_a = f"sigla_partido = '{info_a['sigla_partido']}'"
    else:
        filtro_item_a = f"numero_candidato = {int(info_a['numero_candidato'])}"

    # Filtro de Candidato B
    if cargo_b == "presidente":
        filtro_item_b = f"sigla_partido = '{info_b['sigla_partido']}'"
    else:
        filtro_item_b = f"numero_candidato = {int(info_b['numero_candidato'])}"

    # Carregar dados com base no nível territorial
    with st.spinner("Calculando cruzamento territorial..."):
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
                    SELECT id_local, nome_local, bairro, municipio, zona, secao
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
            # Mapear região através de NM_MUN
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

    # Cálculo dos percentuais
    df_cruz['pct_a'] = (100.0 * df_cruz['votos_a'] / df_cruz['total_a'].replace(0, 1)).round(2)
    df_cruz['pct_b'] = (100.0 * df_cruz['votos_b'] / df_cruz['total_b'].replace(0, 1)).round(2)
    df_cruz['votos_validos_unidade'] = df_cruz[['total_a', 'total_b']].max(axis=1)

    # Definir valores de X e Y com base na métrica
    if "Percentual" in metrica_cruz:
        x_val = df_cruz['pct_a']
        y_val = df_cruz['pct_b']
        x_lbl = f"% Votos: {info_a['nome_urna']}"
        y_lbl = f"% Votos: {info_b['nome_urna']}"
        df_cruz['val_x'] = df_cruz['pct_a']
        df_cruz['val_y'] = df_cruz['pct_b']
    else:
        x_val = df_cruz['votos_a']
        y_val = df_cruz['votos_b']
        x_lbl = f"Votos Nominais: {info_a['nome_urna']}"
        y_lbl = f"Votos Nominais: {info_b['nome_urna']}"
        df_cruz['val_x'] = df_cruz['votos_a']
        df_cruz['val_y'] = df_cruz['votos_b']

    # --- 4. CÁLCULO ESTATÍSTICO DE CORRELAÇÃO E DIAGNÓSTICO ---
    std_x = np.std(x_val)
    std_y = np.std(y_val)
    
    if std_x > 0 and std_y > 0 and len(df_cruz) > 1:
        corr_pearson = float(np.corrcoef(x_val, y_val)[0, 1])
        r2 = corr_pearson ** 2
        # Ajuste de linha de tendência
        m_slope, b_intercept = np.polyfit(x_val, y_val, 1)
    else:
        corr_pearson = 0.0
        r2 = 0.0
        m_slope, b_intercept = 0.0, 0.0

    # Diagnóstico Político da Correlação
    if corr_pearson >= 0.70:
        diag_badge = "🟢 Forte Dobradinha / Aliança Sólida"
        diag_desc = f"Existe uma correlação fortíssima ({corr_pearson:.2f}) entre os votos. Onde {info_a['nome_urna']} vence, {info_b['nome_urna']} também recebe votação expressiva."
    elif corr_pearson >= 0.40:
        diag_badge = "🟡 Associação Positiva Moderada"
        diag_desc = f"Correlação moderada ({corr_pearson:.2f}). Há transferência ou sinergia de votos relevante em diversas praças."
    elif corr_pearson > -0.40:
        diag_badge = "⚪ Votos Descolados / Independentes"
        diag_desc = f"Correlação fraca ({corr_pearson:.2f}). As bases eleitorais de ambos operam de forma autônoma e em regiões distintas."
    else:
        diag_badge = "🔴 Polarização Inversa / Concorrência"
        diag_desc = f"Correlação negativa ({corr_pearson:.2f}). Os dois candidatos disputam eleitorados antagônicos."

    # KPIs de Destaque
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Correlação de Pearson (r)", f"{corr_pearson:+.3f}", help="Varia de -1 a +1. Mede a força da associação linear entre os votos.")
    k2.metric("Aderência (R²)", f"{r2 * 100:.1f}%", help="Percentual da variação de votos de B explicado pela variação de A.")
    k3.metric(f"Votos {info_a['nome_urna']}", fmt_int(df_cruz['votos_a'].sum()))
    k4.metric(f"Votos {info_b['nome_urna']}", fmt_int(df_cruz['votos_b'].sum()))

    st.info(f"**Diagnóstico:** {diag_badge} — {diag_desc}")
    st.divider()

    # --- 5. GRÁFICO DE DISPERSÃO (SCATTER PLOT COM REGRESSÃO) ---
    c_graf1, c_graf2 = st.columns([1.3, 0.7])
    
    with c_graf1:
        st.markdown(f"**Dispersão Territorial: {info_a['nome_urna']} vs. {info_b['nome_urna']}**")
        
        # Criar scatter plot interativo
        fig_scatter = px.scatter(
            df_cruz,
            x='val_x',
            y='val_y',
            color='regiao',
            size='votos_validos_unidade',
            hover_name='unidade',
            hover_data={
                'val_x': False,
                'val_y': False,
                'votos_a': True,
                'pct_a': True,
                'votos_b': True,
                'pct_b': True,
                'regiao': True
            },
            labels={
                'val_x': x_lbl,
                'val_y': y_lbl,
                'votos_a': f'Votos {info_a["nome_urna"]}',
                'pct_a': f'% {info_a["nome_urna"]}',
                'votos_b': f'Votos {info_b["nome_urna"]}',
                'pct_b': f'% {info_b["nome_urna"]}',
                'regiao': 'Região'
            }
        )

        # Adicionar linha de tendência (OLS) se houver pontos suficientes
        if len(df_cruz) > 1 and std_x > 0:
            x_line = np.linspace(x_val.min(), x_val.max(), 50)
            y_line = m_slope * x_line + b_intercept
            fig_scatter.add_trace(
                go.Scatter(
                    x=x_line,
                    y=y_line,
                    mode='lines',
                    name='Tendência (Regressão)',
                    line=dict(color='#2C3E50', dash='dash', width=2)
                )
            )

        fig_scatter.update_layout(
            height=480,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with c_graf2:
        st.markdown("**Top Casamentos / Dobradinhas**")
        st.caption("Unidades com maior votação conjunta dos dois candidatos:")
        
        # Score de Dobradinha = soma normalizada ou produto
        df_cruz['score_dobradinha'] = df_cruz['pct_a'] + df_cruz['pct_b']
        top_casados = df_cruz.sort_values('score_dobradinha', ascending=False).head(8).copy()
        
        # Gráfico de barras horizontais empilhadas ou agrupadas
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=top_casados['unidade'],
            x=top_casados['pct_a'],
            name=info_a['nome_urna'],
            orientation='h',
            marker=dict(color='#1F78B4')
        ))
        fig_bar.add_trace(go.Bar(
            y=top_casados['unidade'],
            x=top_casados['pct_b'],
            name=info_b['nome_urna'],
            orientation='h',
            marker=dict(color='#FF7F00')
        ))
        fig_bar.update_layout(
            barmode='group',
            height=480,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            xaxis_title="% dos Votos Válidos"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- 6. DESTAQUES ESTRATÉGICOS (CARDS) ---
    st.markdown("#### 🎯 Destaques Territoriais da Parceria")
    d1, d2, d3 = st.columns(3)
    
    # 1. Maior Sintonia
    top1 = df_cruz.sort_values('score_dobradinha', ascending=False).iloc[0]
    with d1:
        st.success(
            f"🤝 **Maior Casamento de Votos**\n\n"
            f"**{top1['unidade']}**\n\n"
            f"• {info_a['nome_urna']}: **{fmt_pct(top1['pct_a'])}** ({fmt_int(top1['votos_a'])})\n\n"
            f"• {info_b['nome_urna']}: **{fmt_pct(top1['pct_b'])}** ({fmt_int(top1['votos_b'])})"
        )

    # 2. Bastião de A (onde A mais superou B)
    df_cruz['dif_a_b'] = df_cruz['pct_a'] - df_cruz['pct_b']
    top_bast_a = df_cruz.sort_values('dif_a_b', ascending=False).iloc[0]
    with d2:
        st.info(
            f"🚀 **Pico Exclusivo de {info_a['nome_urna']}**\n\n"
            f"**{top_bast_a['unidade']}**\n\n"
            f"• {info_a['nome_urna']}: **{fmt_pct(top_bast_a['pct_a'])}**\n\n"
            f"• {info_b['nome_urna']}: **{fmt_pct(top_bast_a['pct_b'])}** (Diferença: {fmt_pct(top_bast_a['dif_a_b'])})"
        )

    # 3. Bastião de B (onde B mais superou A)
    top_bast_b = df_cruz.sort_values('dif_a_b', ascending=True).iloc[0]
    with d3:
        st.warning(
            f"⚡ **Pico Exclusivo de {info_b['nome_urna']}**\n\n"
            f"**{top_bast_b['unidade']}**\n\n"
            f"• {info_b['nome_urna']}: **{fmt_pct(top_bast_b['pct_b'])}**\n\n"
            f"• {info_a['nome_urna']}: **{fmt_pct(top_bast_a['pct_a'])}** (Diferença: {fmt_pct(-top_bast_b['dif_a_b'])})"
        )

    # --- 7. TABELA DETALHADA COM BUSCA E DOWNLOAD ---
    st.markdown("#### 📋 Tabela Analítica Completa")
    busca_tab = st.text_input("🔍 Filtrar tabela por nome da unidade:", placeholder="Digite o nome para filtrar...", key="busca_tab_cruz")
    
    df_tab = df_cruz.copy()
    if busca_tab.strip():
        q_tab = normalize_text(busca_tab)
        df_tab = df_tab[df_tab['unidade'].apply(lambda x: q_tab in normalize_text(x))]
        
    df_tab_view = df_tab.sort_values('score_dobradinha', ascending=False).copy()
    df_tab_view['Votos A'] = df_tab_view['votos_a'].apply(fmt_int)
    df_tab_view['% Votos A'] = df_tab_view['pct_a'].apply(fmt_pct)
    df_tab_view['Votos B'] = df_tab_view['votos_b'].apply(fmt_int)
    df_tab_view['% Votos B'] = df_tab_view['pct_b'].apply(fmt_pct)
    df_tab_view['Diferença (%)'] = (df_tab_view['pct_a'] - df_tab_view['pct_b']).apply(lambda v: f"{v:+.2f}%".replace(".", ","))

    cols_show = ['unidade', 'regiao', 'Votos A', '% Votos A', 'Votos B', '% Votos B', 'Diferença (%)']
    st.dataframe(
        df_tab_view[cols_show].rename(columns={
            'unidade': 'Unidade Territorial',
            'regiao': 'Região de Desenvolvimento',
            'Votos A': f'Votos ({info_a["nome_urna"]})',
            '% Votos A': f'% ({info_a["nome_urna"]})',
            'Votos B': f'Votos ({info_b["nome_urna"]})',
            '% Votos B': f'% ({info_b["nome_urna"]})'
        }),
        use_container_width=True,
        hide_index=True
    )

    # Download CSV
    csv_bytes = df_tab[cols_show].to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Exportar Dados do Cruzamento (.CSV)",
        data=csv_bytes,
        file_name=f"cruzamento_{normalize_text(info_a['nome_urna'])}_{normalize_text(info_b['nome_urna'])}.csv",
        mime="text/csv"
    )
