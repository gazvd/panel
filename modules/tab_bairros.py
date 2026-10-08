import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
import geopandas as gpd
from modules.geo_loader import load_mosaico_bairros_gdf
from modules.data_loader import get_locais_votacao_base
import duckdb
from config import PATH_RESULTADOS, fmt_int, fmt_pct, get_cores_foco, normalize_text

def render_tab_bairros(ano, turno, cargo, modo, partido_selecionado, cand_selecionado, df_mun_map):
    st.markdown("### 🏘️ Bairros & Distritos (Menor Agregação Territorial)")
    st.caption("Visão detalhada em mosaico contínuo. Selecione o município para carregar seus bairros e distritos.")
    
    # Seletor de Município e Critério
    muns_nomes = sorted(df_mun_map['NM_MUN'].unique().tolist())
    recife_idx = muns_nomes.index("Recife") if "Recife" in muns_nomes else 0
    
    c_sel1, c_sel2, c_sel3 = st.columns([1.1, 1.3, 1.6])
    with c_sel1:
        mun_nome_sel = st.selectbox("Escolha o Município:", muns_nomes, index=recife_idx)
    with c_sel2:
        criterio_analise = st.radio("Critério de Análise:", ["Total de Votos (Nominais)", "Percentual (%)"], horizontal=True, key="crit_bairros")
    with c_sel3:
        busca_bairro = st.text_input("🔍 Pesquisar Bairro ou Distrito:", placeholder="Ex: Boa Viagem, Madalena, Centro...", key="busca_bairro")
        
    mun_info = df_mun_map[df_mun_map['NM_MUN'] == mun_nome_sel].iloc[0]
    cd_mun_sel = str(mun_info['CD_MUN'])
    
    # Carregar APENAS os polígonos desse município (performance ultrarrápida!)
    gdf_bairros_mun = load_mosaico_bairros_gdf(cd_mun=cd_mun_sel).copy()
    
    if len(gdf_bairros_mun) == 0:
        st.warning(f"Nenhuma delimitação encontrada para o município {mun_nome_sel}.")
        return
        
    # Carregar locais de votação desse município
    df_locais = get_locais_votacao_base()
    locais_mun = df_locais[df_locais['municipio'].str.upper() == mun_nome_sel.upper()].copy()
    
    c_num = cand_selecionado['numero_candidato'] if (cand_selecionado is not None and pd.notna(cand_selecionado.get('numero_candidato'))) else None
    p_sigla = partido_selecionado if modo == "Partido" else (cand_selecionado.get('sigla_partido') if (c_num is None and cand_selecionado is not None) else None)
    alvo_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else (partido_selecionado if partido_selecionado else "Total")
    
    cand_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else None
    partido_nome = partido_selecionado if modo == "Partido" else (cand_selecionado.get('sigla_partido') if cand_selecionado else None)
    hex_cor, scale_plotly, scale_folium = get_cores_foco(cand_nome, partido_nome)
    
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    
    where_base = f"ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND id_municipio = {int(cd_mun_sel)}"
    
    # 1. Total válidos por seção
    q_tot = f"""
        SELECT zona, secao, SUM(total_votos) as total_validos
        FROM '{res_path}'
        WHERE {where_base}
        GROUP BY zona, secao
    """
    
    # 2. Votos do candidato/partido por seção
    where_item = where_base
    if c_num:
        where_item += f" AND numero_candidato = {c_num}"
    elif p_sigla:
        where_item += f" AND sigla_partido = '{p_sigla}'"
        
    q_item = f"""
        SELECT zona, secao, SUM(total_votos) as votos
        FROM '{res_path}'
        WHERE {where_item}
        GROUP BY zona, secao
    """
    
    q_res = f"""
        WITH t_tot AS ({q_tot}),
             t_item AS ({q_item})
        SELECT 
            t_tot.zona,
            t_tot.secao,
            COALESCE(t_item.votos, 0) as votos,
            t_tot.total_validos
        FROM t_tot
        LEFT JOIN t_item ON t_tot.zona = t_item.zona AND t_tot.secao = t_item.secao
    """
    votos_secoes = con.execute(q_res).df()
    
    # Cruzar votos com locais_mun
    locais_com_votos = locais_mun.merge(votos_secoes, on=['zona', 'secao'], how='left')
    locais_com_votos['votos'] = locais_com_votos['votos'].fillna(0).astype(int)
    locais_com_votos['total_validos'] = locais_com_votos['total_validos'].fillna(0).astype(int)
    
    # Spatial join dos colégios com os polígonos do mosaico desse município
    loc_coords = locais_com_votos.dropna(subset=['latitude', 'longitude']).copy()
    if len(loc_coords) > 0:
        pts = gpd.points_from_xy(loc_coords['longitude'], loc_coords['latitude'])
        gdf_pts = gpd.GeoDataFrame(loc_coords, geometry=pts, crs="EPSG:4326")
        
        # Spatial join para identificar exatamente em qual bairro/distrito cada voto ocorreu
        sj = gpd.sjoin(gdf_pts, gdf_bairros_mun[['NM_BAIRRO', 'TIPO_UNIDADE', 'geometry']], how='left', predicate='within')
        
        # Agregar por NM_BAIRRO
        bairro_agg = sj.groupby('NM_BAIRRO').agg(
            votos=('votos', 'sum'),
            total_validos=('total_validos', 'sum'),
            aptos=('aptos', 'sum'),
            locais_count=('id_local', 'nunique')
        ).reset_index()
    else:
        bairro_agg = pd.DataFrame(columns=['NM_BAIRRO', 'votos', 'total_validos', 'aptos', 'locais_count'])
        
    gdf_bairros_mun = gdf_bairros_mun.merge(bairro_agg, on='NM_BAIRRO', how='left')
    gdf_bairros_mun['votos'] = gdf_bairros_mun['votos'].fillna(0).astype(int)
    gdf_bairros_mun['total_validos'] = gdf_bairros_mun['total_validos'].fillna(0).astype(int)
    gdf_bairros_mun['pct_votos'] = (100.0 * gdf_bairros_mun['votos'] / gdf_bairros_mun['total_validos'].replace(0, 1)).round(2)
    gdf_bairros_mun['votos_fmt'] = gdf_bairros_mun['votos'].apply(fmt_int)
    gdf_bairros_mun['total_validos_fmt'] = gdf_bairros_mun['total_validos'].apply(fmt_int)
    gdf_bairros_mun['pct_votos_fmt'] = gdf_bairros_mun['pct_votos'].apply(fmt_pct)
    
    df_view = gdf_bairros_mun.copy()
    
    if busca_bairro.strip():
        q_b = normalize_text(busca_bairro)
        df_view = df_view[df_view.apply(lambda r: (q_b in normalize_text(r['NM_BAIRRO'])) or (q_b in normalize_text(r['NM_DIST'])), axis=1)].reset_index(drop=True)
        if len(df_view) == 1:
            b_sel = df_view.iloc[0]
            st.success(
                f"🎯 **{b_sel['NM_BAIRRO']}** ({b_sel['TIPO_UNIDADE']}) — "
                f"**{fmt_int(b_sel['votos'])} votos** ({fmt_pct(b_sel['pct_votos'])}) de {alvo_nome} | "
                f"Total Válidos: **{fmt_int(b_sel['total_validos'])}**"
            )
        elif len(df_view) == 0:
            st.warning(f"Nenhum bairro ou distrito com o termo '{busca_bairro}' em {mun_nome_sel}.")
    
    if criterio_analise == "Total de Votos (Nominais)":
        df_view = df_view.sort_values('votos', ascending=False).reset_index(drop=True)
    else:
        df_view = df_view.sort_values('pct_votos', ascending=False).reset_index(drop=True)
    
    # KPIs da cidade
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Unidades Mapeadas", f"{len(df_view)}", help="Bairros oficiais e distritos contíguos")
    top_pct = df_view.sort_values('pct_votos', ascending=False).iloc[0] if len(df_view) > 0 else None
    col2.metric("Maior % Obtido", f"{fmt_pct(top_pct['pct_votos'])} ({top_pct['NM_BAIRRO']})" if top_pct is not None else "-")
    top_v = df_view.sort_values('votos', ascending=False).iloc[0] if len(df_view) > 0 else None
    col3.metric("Maior Volume", f"{fmt_int(top_v['votos'])} votos ({top_v['NM_BAIRRO']})" if top_v is not None else "-")
    col4.metric("Total no Município", fmt_int(df_view['votos'].sum()))
    
    st.divider()
    
    c_map, c_rank = st.columns([1.2, 0.8])
    
    with c_rank:
        if criterio_analise == "Total de Votos (Nominais)":
            st.markdown(f"**Top Bairros / Distritos (Total de Votos)**")
            top_plot = df_view.head(12).sort_values('votos', ascending=True).copy()
            top_plot['texto_barra'] = top_plot['votos'].apply(fmt_int)
            fig = px.bar(
                top_plot,
                x='votos',
                y='NM_BAIRRO',
                orientation='h',
                text='texto_barra',
                color='votos',
                color_continuous_scale=scale_plotly,
                labels={'votos': 'Votos Nominais', 'NM_BAIRRO': 'Bairro / Distrito'}
            )
        else:
            st.markdown(f"**Top Bairros / Distritos (% Votos Válidos)**")
            top_plot = df_view.head(12).sort_values('pct_votos', ascending=True).copy()
            top_plot['texto_barra'] = top_plot['pct_votos'].apply(fmt_pct)
            fig = px.bar(
                top_plot,
                x='pct_votos',
                y='NM_BAIRRO',
                orientation='h',
                text='texto_barra',
                color='pct_votos',
                color_continuous_scale=scale_plotly,
                labels={'pct_votos': '% Votos Válidos', 'NM_BAIRRO': 'Bairro / Distrito'}
            )
            
        fig.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0))
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
    with c_map:
        st.markdown(f"**Mapa de {mun_nome_sel} ({criterio_analise})**")
        bounds = gdf_bairros_mun.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        zoom = 11
        
        if busca_bairro.strip() and len(df_view) == 1:
            b_bounds = df_view.iloc[0].geometry.bounds
            if len(b_bounds) == 4 and not any(pd.isna(b_bounds)):
                center_lat = (b_bounds[1] + b_bounds[3]) / 2
                center_lon = (b_bounds[0] + b_bounds[2]) / 2
                zoom = 13
        
        coluna_cor = "votos" if criterio_analise == "Total de Votos (Nominais)" else "pct_votos"
        legenda_mapa = f"Total de Votos de {alvo_nome}" if criterio_analise == "Total de Votos (Nominais)" else f"% Votos de {alvo_nome}"
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")
        
        folium.Choropleth(
            geo_data=gdf_bairros_mun.__geo_interface__,
            name="choropleth",
            data=gdf_bairros_mun,
            columns=["NM_BAIRRO", coluna_cor],
            key_on="feature.properties.NM_BAIRRO",
            fill_color=scale_folium,
            fill_opacity=0.75,
            line_opacity=0.4,
            legend_name=legenda_mapa
        ).add_to(m)
        
        folium.GeoJson(
            gdf_bairros_mun,
            style_function=lambda x: {'fillColor': 'transparent', 'color': '#2C3E50', 'weight': 1.2},
            tooltip=folium.GeoJsonTooltip(
                fields=['NM_BAIRRO', 'NM_DIST', 'TIPO_UNIDADE', 'votos_fmt', 'pct_votos_fmt', 'total_validos_fmt'],
                aliases=['Nome:', 'Distrito:', 'Tipo:', 'Votos Obtidos:', '% dos Válidos:', 'Válidos na Unidade:']
            )
        ).add_to(m)
        
        st_folium(m, height=450, width="100%")
        
    st.markdown(f"**Tabela Detalhada: {mun_nome_sel}**")
    df_table_b = df_view.copy()
    df_table_b['Votos Obtidos'] = df_table_b['votos'].apply(fmt_int)
    df_table_b['Total Votos Válidos'] = df_table_b['total_validos'].apply(fmt_int)
    df_table_b['% Votos Válidos'] = df_table_b['pct_votos'].apply(fmt_pct)
    
    st.dataframe(
        df_table_b[['NM_BAIRRO', 'NM_DIST', 'TIPO_UNIDADE', 'Votos Obtidos', 'Total Votos Válidos', '% Votos Válidos']].rename(columns={
            'NM_BAIRRO': 'Bairro / Unidade Territorial',
            'NM_DIST': 'Distrito de Origem',
            'TIPO_UNIDADE': 'Tipo de Unidade'
        }),
        use_container_width=True,
        hide_index=True
    )
