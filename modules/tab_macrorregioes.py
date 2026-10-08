import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
from modules.geo_loader import load_regioes_gdf
from modules.data_loader import get_votos_municipios
from config import CORES_PARTIDOS, COR_PADRAO, fmt_int, fmt_pct, get_cores_foco, normalize_text

def render_tab_macrorregioes(ano, turno, cargo, modo, partido_selecionado, cand_selecionado, df_mun_map):
    st.markdown("### 🌍 Macrorregiões (12 Regiões de Desenvolvimento)")
    st.caption("Visão agregada por macrorregião econômica e geográfica de Pernambuco.")
    
    # Identidade visual dinâmica (João Campos amarelo, Raquel roxo, PT vermelho, etc.)
    cand_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else None
    hex_cor, scale_plotly, scale_folium = get_cores_foco(cand_nome, partido_selecionado)
    
    # Obter dados de votos por município
    c_num = cand_selecionado['numero_candidato'] if (cand_selecionado is not None and pd.notna(cand_selecionado.get('numero_candidato'))) else None
    p_sigla = partido_selecionado if modo == "Partido" else (cand_selecionado.get('sigla_partido') if (c_num is None and cand_selecionado is not None) else None)
    
    df_votos = get_votos_municipios(ano, turno, cargo, partido=p_sigla, numero_candidato=c_num)
    
    # Cruzar com RD através de df_mun_map (CD_MUN -> REGIAO_DESENVOLVIMENTO)
    df_votos['CD_MUN'] = df_votos['id_municipio'].astype(str)
    df_merged = df_votos.merge(df_mun_map[['CD_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO']], on='CD_MUN', how='left')
    
    # Agregar por RD
    df_rd = df_merged.groupby('REGIAO_DESENVOLVIMENTO').agg(
        votos=('votos', 'sum'),
        total_validos=('total_validos', 'sum')
    ).reset_index()
    df_rd['pct_votos'] = (100.0 * df_rd['votos'] / df_rd['total_validos'].replace(0, 1)).round(2)
    df_rd = df_rd.sort_values('pct_votos', ascending=False).reset_index(drop=True)
    
    # KPIs rápidos
    total_votos_pe = df_rd['votos'].sum()
    total_validos_pe = df_rd['total_validos'].sum()
    pct_geral = (100.0 * total_votos_pe / total_validos_pe) if total_validos_pe > 0 else 0
    
    alvo_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else (partido_selecionado if partido_selecionado else "Total")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Votos no Estado", fmt_int(total_votos_pe))
    col2.metric("Total Válidos em PE", fmt_int(total_validos_pe))
    col3.metric("% no Estado", fmt_pct(pct_geral))
    col4.metric("Melhor Região", f"{df_rd.iloc[0]['REGIAO_DESENVOLVIMENTO']}" if len(df_rd) > 0 else "-")
    
    st.divider()
    
    # Controles: Critério de Análise + Busca Inteligente
    c_ctrl1, c_ctrl2 = st.columns([1.3, 1.7])
    with c_ctrl1:
        criterio_analise = st.radio(
            "Critério de Análise (Mapa e Gráfico):",
            ["Total de Votos (Nominais)", "Percentual (%)"],
            horizontal=True,
            key="crit_rd"
        )
    with c_ctrl2:
        busca_rd = st.text_input("🔍 Busca Inteligente (Região ou Município):", placeholder="Ex: Agreste, Sertão, Caruaru, Olinda...", key="busca_rd")
    
    if criterio_analise == "Total de Votos (Nominais)":
        df_rd_view = df_rd.sort_values('votos', ascending=False).reset_index(drop=True)
    else:
        df_rd_view = df_rd.sort_values('pct_votos', ascending=False).reset_index(drop=True)
        
    if busca_rd.strip():
        q_rd = normalize_text(busca_rd)
        mun_match = df_merged[df_merged['NM_MUN'].apply(lambda x: q_rd in normalize_text(x))]
        rd_match = df_rd[df_rd['REGIAO_DESENVOLVIMENTO'].apply(lambda x: q_rd in normalize_text(x))]
        
        regioes_filtradas = set(rd_match['REGIAO_DESENVOLVIMENTO'].tolist())
        if len(mun_match) > 0:
            regioes_filtradas.update(mun_match['REGIAO_DESENVOLVIMENTO'].unique().tolist())
            muns_encontrados = ", ".join(mun_match['NM_MUN'].unique().tolist()[:6])
            st.info(f"💡 O município **{muns_encontrados}** pertence à(s) região(ões): **{', '.join(regioes_filtradas)}**.")
            
        if regioes_filtradas:
            df_rd_view = df_rd_view[df_rd_view['REGIAO_DESENVOLVIMENTO'].isin(regioes_filtradas)].reset_index(drop=True)
        else:
            st.warning(f"Nenhuma região ou município encontrado para o termo '{busca_rd}'.")
        
    # Layout colunas: Mapa + Gráfico
    c_map, c_chart = st.columns([1.1, 0.9])
    
    with c_chart:
        if criterio_analise == "Total de Votos (Nominais)":
            st.markdown(f"**Votação por Região (Total de Votos Nominais)**")
            df_rd_plot = df_rd_view.copy()
            df_rd_plot['texto_barra'] = df_rd_plot['votos'].apply(fmt_int)
            fig = px.bar(
                df_rd_plot,
                x='votos',
                y='REGIAO_DESENVOLVIMENTO',
                orientation='h',
                text='texto_barra',
                labels={'votos': 'Total de Votos', 'REGIAO_DESENVOLVIMENTO': 'Região'},
                color='votos',
                color_continuous_scale=scale_plotly
            )
        else:
            st.markdown(f"**Votação por Região de Desenvolvimento (%)**")
            df_rd_plot = df_rd_view.copy()
            df_rd_plot['texto_barra'] = df_rd_plot['pct_votos'].apply(fmt_pct)
            fig = px.bar(
                df_rd_plot,
                x='pct_votos',
                y='REGIAO_DESENVOLVIMENTO',
                orientation='h',
                text='texto_barra',
                labels={'pct_votos': '% Votos Válidos', 'REGIAO_DESENVOLVIMENTO': 'Região'},
                color='pct_votos',
                color_continuous_scale=scale_plotly
            )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=420, margin=dict(l=0, r=0, t=10, b=0))
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
    with c_map:
        st.markdown(f"**Mapa Coroplético por Macrorregião ({criterio_analise})**")
        gdf_regioes = load_regioes_gdf().copy()
        gdf_regioes = gdf_regioes.merge(df_rd[['REGIAO_DESENVOLVIMENTO', 'votos', 'total_validos', 'pct_votos']], on='REGIAO_DESENVOLVIMENTO', how='left')
        gdf_regioes['votos'] = gdf_regioes['votos'].fillna(0).astype(int)
        gdf_regioes['pct_votos'] = gdf_regioes['pct_votos'].fillna(0.0)
        gdf_regioes['votos_fmt'] = gdf_regioes['votos'].apply(fmt_int)
        gdf_regioes['total_validos_fmt'] = gdf_regioes['total_validos'].apply(fmt_int)
        gdf_regioes['pct_votos_fmt'] = gdf_regioes['pct_votos'].apply(fmt_pct)
        
        coluna_cor = "votos" if criterio_analise == "Total de Votos (Nominais)" else "pct_votos"
        legenda_mapa = f"Total de Votos de {alvo_nome}" if criterio_analise == "Total de Votos (Nominais)" else f"% Votos de {alvo_nome}"
        
        # Folium map centrado em Pernambuco usando OpenStreetMap (zero restrição de API key)
        m = folium.Map(location=[-8.35, -37.8], zoom_start=7, tiles="OpenStreetMap")
        
        folium.Choropleth(
            geo_data=gdf_regioes.__geo_interface__,
            name="choropleth",
            data=gdf_regioes,
            columns=["REGIAO_DESENVOLVIMENTO", coluna_cor],
            key_on="feature.properties.REGIAO_DESENVOLVIMENTO",
            fill_color=scale_folium,
            fill_opacity=0.75,
            line_opacity=0.3,
            legend_name=legenda_mapa
        ).add_to(m)
        
        # Tooltip interativo
        folium.GeoJson(
            gdf_regioes,
            style_function=lambda x: {'fillColor': 'transparent', 'color': '#2C3E50', 'weight': 1.5},
            tooltip=folium.GeoJsonTooltip(
                fields=['REGIAO_DESENVOLVIMENTO', 'votos_fmt', 'pct_votos_fmt', 'total_validos_fmt'],
                aliases=['Região:', 'Votos Obtidos:', '% Votos:', 'Total Válidos:']
            )
        ).add_to(m)
        
        st_folium(m, height=420, width="100%")
        
    # Tabela com formatação brasileira
    df_table = df_rd.copy()
    df_table['Votos Obtidos'] = df_table['votos'].apply(fmt_int)
    df_table['Total Votos Válidos'] = df_table['total_validos'].apply(fmt_int)
    df_table['% Votos Válidos'] = df_table['pct_votos'].apply(fmt_pct)
    df_table = df_table.rename(columns={'REGIAO_DESENVOLVIMENTO': 'Região de Desenvolvimento'})
    
    st.dataframe(
        df_table[['Região de Desenvolvimento', 'Votos Obtidos', 'Total Votos Válidos', '% Votos Válidos']],
        use_container_width=True,
        hide_index=True
    )
