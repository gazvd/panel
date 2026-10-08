import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
from modules.geo_loader import load_zonas_gdf
from modules.data_loader import get_votos_zonas
from config import fmt_int, fmt_pct, get_cores_foco, normalize_text

def render_tab_zonas(ano, turno, cargo, modo, partido_selecionado, cand_selecionado, df_mun_map):
    st.markdown("### 🗳️ Zonas Eleitorais (209 Unidades Zona-Município)")
    st.caption("Delimitação eleitoral que preserva rigorosamente as fronteiras municipais e particiona os municípios multizonais.")
    
    cand_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else None
    partido_nome = partido_selecionado if modo == "Partido" else (cand_selecionado.get('sigla_partido') if cand_selecionado else None)
    hex_cor, scale_plotly, scale_folium = get_cores_foco(cand_nome, partido_nome)
    
    c_num = cand_selecionado['numero_candidato'] if (cand_selecionado is not None and pd.notna(cand_selecionado.get('numero_candidato'))) else None
    p_sigla = partido_selecionado if modo == "Partido" else (cand_selecionado.get('sigla_partido') if (c_num is None and cand_selecionado is not None) else None)
    alvo_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else (partido_selecionado if partido_selecionado else "Total")
    
    # 1. Carregar camada de zonas
    gdf_zonas = load_zonas_gdf().copy()
    
    # Controles de Filtro, Critério e Busca Inteligente
    c_f1, c_f2, c_f3 = st.columns([1.0, 1.3, 1.7])
    with c_f1:
        rds_list = ["TODAS"] + sorted(gdf_zonas['REGIAO_DESENVOLVIMENTO'].unique().tolist())
        rd_sel = st.selectbox("Região:", rds_list, index=0, key="filtro_rd_zonas")
    with c_f2:
        criterio_analise = st.radio("Critério:", ["Total de Votos (Nominais)", "Percentual (%)"], horizontal=True, key="crit_zonas")
    with c_f3:
        busca_zona = st.text_input("🔍 Pesquisar Zona ou Município:", placeholder="Ex: 4, 149, Olinda, Recife...", key="busca_zona")
        
    if rd_sel != "TODAS":
        gdf_zonas = gdf_zonas[gdf_zonas['REGIAO_DESENVOLVIMENTO'] == rd_sel]
        
    # 2. Obter votos por zona
    df_votos_z = get_votos_zonas(ano, turno, cargo, partido=p_sigla, numero_candidato=c_num)
    df_votos_z['CD_MUN'] = df_votos_z['id_municipio'].astype(str)
    
    # Merge com os 209 polígonos
    gdf_zonas['CD_MUN'] = gdf_zonas['CD_MUN'].astype(str)
    gdf_merged = gdf_zonas.merge(
        df_votos_z[['CD_MUN', 'zona', 'votos', 'total_validos', 'pct_votos']],
        left_on=['CD_MUN', 'CD_ZONA'],
        right_on=['CD_MUN', 'zona'],
        how='left'
    )
    gdf_merged['votos'] = gdf_merged['votos'].fillna(0).astype(int)
    gdf_merged['total_validos'] = gdf_merged['total_validos'].fillna(0).astype(int)
    gdf_merged['pct_votos'] = gdf_merged['pct_votos'].fillna(0.0)
    gdf_merged['votos_fmt'] = gdf_merged['votos'].apply(fmt_int)
    gdf_merged['total_validos_fmt'] = gdf_merged['total_validos'].apply(fmt_int)
    gdf_merged['pct_votos_fmt'] = gdf_merged['pct_votos'].apply(fmt_pct)
    
    df_view = gdf_merged.copy()
    
    if busca_zona.strip():
        q_z = normalize_text(busca_zona)
        q_digits = "".join(filter(str.isdigit, q_z))
        
        def match_z(row):
            txt_m = (q_z in normalize_text(row['NM_MUN'])) or (q_z in normalize_text(row['NM_ZONA_MUN']))
            num_m = False
            if q_digits:
                num_m = (str(row['CD_ZONA']) == q_digits)
            return txt_m or num_m
            
        df_view = df_view[df_view.apply(match_z, axis=1)].reset_index(drop=True)
        if len(df_view) == 1:
            z_sel = df_view.iloc[0]
            st.success(
                f"🎯 **{z_sel['NM_ZONA_MUN']}** ({z_sel['REGIAO_DESENVOLVIMENTO']}) — "
                f"**{fmt_int(z_sel['votos'])} votos** ({fmt_pct(z_sel['pct_votos'])}) de {alvo_nome} | "
                f"Total Válidos: **{fmt_int(z_sel['total_validos'])}**"
            )
        elif len(df_view) == 0:
            st.warning(f"Nenhuma zona eleitoral encontrada para '{busca_zona}'.")
    
    if criterio_analise == "Total de Votos (Nominais)":
        df_view = df_view.sort_values('votos', ascending=False).reset_index(drop=True)
    else:
        df_view = df_view.sort_values('pct_votos', ascending=False).reset_index(drop=True)
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Zonas Analisadas", f"{len(df_view)}")
    top_pct = df_view.sort_values('pct_votos', ascending=False).iloc[0] if len(df_view) > 0 else None
    col2.metric("Maior % em Zona", f"{fmt_pct(top_pct['pct_votos'])} ({top_pct['NM_ZONA_MUN']})" if top_pct is not None else "-")
    top_v = df_view.sort_values('votos', ascending=False).iloc[0] if len(df_view) > 0 else None
    col3.metric("Maior Volume", f"{fmt_int(top_v['votos'])} votos ({top_v['NM_ZONA_MUN']})" if top_v is not None else "-")
    col4.metric("Total Votos na Seleção", fmt_int(df_view['votos'].sum()))
    
    st.divider()
    
    # Layout Mapa + Top 10 Zonas
    c_map, c_rank = st.columns([1.2, 0.8])
    
    with c_rank:
        if criterio_analise == "Total de Votos (Nominais)":
            st.markdown("**Top Zonas Eleitorais (Total de Votos)**")
            top10_z = df_view.head(10).sort_values('votos', ascending=True).copy()
            top10_z['texto_barra'] = top10_z['votos'].apply(fmt_int)
            fig = px.bar(
                top10_z,
                x='votos',
                y='NM_ZONA_MUN',
                orientation='h',
                text='texto_barra',
                color='votos',
                color_continuous_scale=scale_plotly,
                labels={'votos': 'Total de Votos', 'NM_ZONA_MUN': 'Zona Eleitoral'}
            )
        else:
            st.markdown("**Top Zonas Eleitorais (% Votos Válidos)**")
            top10_z = df_view.head(10).sort_values('pct_votos', ascending=True).copy()
            top10_z['texto_barra'] = top10_z['pct_votos'].apply(fmt_pct)
            fig = px.bar(
                top10_z,
                x='pct_votos',
                y='NM_ZONA_MUN',
                orientation='h',
                text='texto_barra',
                color='pct_votos',
                color_continuous_scale=scale_plotly,
                labels={'pct_votos': '% Válidos', 'NM_ZONA_MUN': 'Zona Eleitoral'}
            )
            
        fig.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=0))
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
    with c_map:
        st.markdown(f"**Mapa das Zonas Eleitorais ({criterio_analise})**")
        bounds = gdf_merged.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        zoom = 8 if rd_sel != "TODAS" else 7
        
        if busca_zona.strip() and len(df_view) == 1:
            z_bounds = df_view.iloc[0].geometry.bounds
            if len(z_bounds) == 4 and not any(pd.isna(z_bounds)):
                center_lat = (z_bounds[1] + z_bounds[3]) / 2
                center_lon = (z_bounds[0] + z_bounds[2]) / 2
                zoom = 11
        
        coluna_cor = "votos" if criterio_analise == "Total de Votos (Nominais)" else "pct_votos"
        legenda_mapa = f"Total de Votos de {alvo_nome}" if criterio_analise == "Total de Votos (Nominais)" else f"% Votos de {alvo_nome}"
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")
        
        folium.Choropleth(
            geo_data=gdf_merged.__geo_interface__,
            name="choropleth",
            data=gdf_merged,
            columns=["ID_ZONA_MUN", coluna_cor],
            key_on="feature.properties.ID_ZONA_MUN",
            fill_color=scale_folium,
            fill_opacity=0.75,
            line_opacity=0.4,
            legend_name=legenda_mapa
        ).add_to(m)
        
        folium.GeoJson(
            gdf_merged,
            style_function=lambda x: {'fillColor': 'transparent', 'color': '#2980B9', 'weight': 1.2},
            tooltip=folium.GeoJsonTooltip(
                fields=['NM_ZONA_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'votos_fmt', 'pct_votos_fmt', 'total_validos_fmt'],
                aliases=['Zona:', 'Município:', 'Região:', 'Votos Obtidos:', '% dos Válidos:', 'Total Válidos:']
            )
        ).add_to(m)
        
        st_folium(m, height=430, width="100%")
        
    st.markdown("**Tabela Completa das Zonas Eleitorais**")
    df_table_z = df_view.copy()
    df_table_z['Votos Obtidos'] = df_table_z['votos'].apply(fmt_int)
    df_table_z['Total Votos Válidos'] = df_table_z['total_validos'].apply(fmt_int)
    df_table_z['% Votos Válidos'] = df_table_z['pct_votos'].apply(fmt_pct)
    
    st.dataframe(
        df_table_z[['NM_ZONA_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'Votos Obtidos', 'Total Votos Válidos', '% Votos Válidos']].rename(columns={
            'NM_ZONA_MUN': 'Zona Eleitoral / Município',
            'NM_MUN': 'Município',
            'REGIAO_DESENVOLVIMENTO': 'Região de Desenvolvimento'
        }),
        use_container_width=True,
        hide_index=True
    )
