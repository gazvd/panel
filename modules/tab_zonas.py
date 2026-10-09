import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
from modules.geo_loader import load_zonas_gdf
from modules.data_loader import get_votos_zonas
from config import fmt_int, fmt_pct, get_cores_foco, get_contrast_color, normalize_text, wrap_label

def render_tab_zonas(ano, turno, cargo, modo, partido_selecionado, cand_selecionado, df_mun_map, modo_todos=None):
    if modo_todos is None:
        modo_todos = (cand_selecionado is None and partido_selecionado is None)

    if modo_todos:
        st.markdown("### 🗳️ Zonas Eleitorais — Mapa de Vencedores (209 Unidades Zona-Município)")
        st.caption("Distribuição territorial de forças políticas nas 209 Zonas Eleitorais de Pernambuco.")
        
        from modules.data_loader import get_vencedores_zonas
        df_venc = get_vencedores_zonas(ano, turno, cargo, modo=modo)
        df_venc['CD_MUN'] = df_venc['id_municipio'].astype(str)
        
        gdf_zonas = load_zonas_gdf().copy()
        gdf_zonas['CD_MUN'] = gdf_zonas['CD_MUN'].astype(str)
        
        gdf_merged = gdf_zonas.merge(
            df_venc,
            left_on=['CD_MUN', 'CD_ZONA'],
            right_on=['CD_MUN', 'zona'],
            how='left'
        )
        
        if len(gdf_merged) == 0:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            return

        gdf_merged['cor'] = gdf_merged.apply(lambda r: get_cores_foco(r['vencedor'], r['partido_vencedor'])[0] if pd.notna(r['vencedor']) else '#2980B9', axis=1)
        gdf_merged['pct_vencedor_fmt'] = gdf_merged['pct_vencedor'].apply(fmt_pct)
        gdf_merged['pct_segundo_fmt'] = gdf_merged['pct_segundo'].apply(fmt_pct)
        gdf_merged['margem_pct_fmt'] = gdf_merged['margem_pct'].apply(lambda v: f"+{fmt_pct(v)}")
        gdf_merged['margem_votos_fmt'] = gdf_merged['margem_votos'].apply(lambda v: f"+{fmt_int(v)}")
        gdf_merged['votos_vencedor_fmt'] = gdf_merged['votos_vencedor'].apply(fmt_int)
        gdf_merged['votos_segundo_fmt'] = gdf_merged['votos_segundo'].apply(fmt_int)
        gdf_merged['total_validos_fmt'] = gdf_merged['total_validos'].apply(fmt_int)

        # Filtros
        c_f1, c_f2, c_f3, c_f4 = st.columns([1.1, 1.3, 1.2, 1.4])
        with c_f1:
            rds_list = ["TODAS"] + sorted(gdf_merged['REGIAO_DESENVOLVIMENTO'].dropna().unique().tolist())
            rd_sel = st.selectbox("Região:", rds_list, index=0, key="filtro_rd_venc_zonas")
        with c_f2:
            if rd_sel != "TODAS":
                muns_disponiveis = sorted(gdf_merged[gdf_merged['REGIAO_DESENVOLVIMENTO'] == rd_sel]['NM_MUN'].dropna().unique().tolist())
            else:
                muns_disponiveis = sorted(gdf_merged['NM_MUN'].dropna().unique().tolist())
            muns_list = ["TODOS"] + muns_disponiveis
            mun_sel = st.selectbox("Município:", muns_list, index=0, key=f"filtro_mun_venc_zonas_{rd_sel}")
        with c_f3:
            criterio_venc = st.radio("Critério de Destaque:", ["Margem de Vitória (p.p.)", "% do Vencedor", "Votos do Vencedor"], horizontal=True, key="crit_venc_zonas")
        with c_f4:
            busca_zona = st.text_input("🔍 Pesquisar Zona:", placeholder="Ex: 4, 149, Olinda, Recife...", key="busca_venc_zona")

        df_view = gdf_merged.copy()
        if rd_sel != "TODAS":
            df_view = df_view[df_view['REGIAO_DESENVOLVIMENTO'] == rd_sel]
        if mun_sel != "TODOS":
            df_view = df_view[df_view['NM_MUN'] == mun_sel]

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
                    f"🥇 **{z_sel['vencedor']} ({z_sel['partido_vencedor']})**: {z_sel['votos_vencedor_fmt']} votos ({z_sel['pct_vencedor_fmt']}) | "
                    f"🥈 **{z_sel['segundo']} ({z_sel['partido_segundo']})**: {z_sel['votos_segundo_fmt']} votos ({z_sel['pct_segundo_fmt']}) | "
                    f"Margem: **{z_sel['margem_pct_fmt']}** ({z_sel['margem_votos_fmt']} votos) | "
                    f"Total Válidos: **{z_sel['total_validos_fmt']}**"
                )
            elif len(df_view) == 0:
                st.warning(f"Nenhuma zona eleitoral encontrada para '{busca_zona}'.")

        # Placar de vitórias
        venc_counts = df_view['vencedor'].value_counts()
        lider_cand = venc_counts.index[0] if len(venc_counts) > 0 else "-"
        lider_vitorias = venc_counts.iloc[0] if len(venc_counts) > 0 else 0

        df_s_margem = df_view.sort_values('margem_pct', ascending=False)
        top_margem = df_s_margem.iloc[0] if len(df_s_margem) > 0 else None
        menor_margem = df_s_margem.iloc[-1] if len(df_s_margem) > 0 else None

        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Zonas Analisadas", f"{len(df_view)}")
        col2.metric("Líder em Zonas", f"{lider_cand} ({lider_vitorias} zonas)" if lider_cand != "-" else "-")
        col3.metric("Maior Margem", f"+{fmt_pct(top_margem['margem_pct'])} ({top_margem['NM_ZONA_MUN']})" if top_margem is not None else "-")
        col4.metric("Disputa Mais Acirrada", f"+{fmt_pct(menor_margem['margem_pct'])} ({menor_margem['NM_ZONA_MUN']})" if menor_margem is not None else "-")

        # Badges do Placar
        badges = []
        for cand, cnt in venc_counts.items():
            bg_c = get_cores_foco(cand)[0]
            fg_c = get_contrast_color(bg_c)
            badges.append(
                f"<span style='background-color: {bg_c}; color: {fg_c}; padding: 4px 10px; border-radius: 12px; margin-right: 8px; font-weight: bold; font-size: 0.9rem;'>"
                f"{cand}: {cnt} {'zona' if cnt == 1 else 'zonas'} ({cnt/len(df_view)*100:.1f}%)"
                f"</span>"
            )
        placar_html = " ".join(badges)
        st.markdown(f"**Placar de Zonas Conquistadas:** {placar_html}", unsafe_allow_html=True)
        st.divider()

        # Ordenação
        if criterio_venc == "Margem de Vitória (p.p.)":
            df_view_plot = df_view.sort_values('margem_pct', ascending=False).reset_index(drop=True)
        elif criterio_venc == "% do Vencedor":
            df_view_plot = df_view.sort_values('pct_vencedor', ascending=False).reset_index(drop=True)
        else:
            df_view_plot = df_view.sort_values('votos_vencedor', ascending=False).reset_index(drop=True)

        c_map, c_rank = st.columns([1.2, 0.8])

        with c_rank:
            st.markdown(f"**Top 10 Zonas Eleitorais ({criterio_venc})**")
            eixo_x = 'margem_pct' if criterio_venc == "Margem de Vitória (p.p.)" else ('pct_vencedor' if criterio_venc == "% do Vencedor" else 'votos_vencedor')
            top10 = df_view_plot.head(10).sort_values(eixo_x, ascending=True).copy()
            top10['texto_barra'] = top10.apply(
                lambda r: wrap_label(f"{r['vencedor']}: +{fmt_pct(r['margem_pct'])}" if criterio_venc == "Margem de Vitória (p.p.)"
                else (f"{r['vencedor']}: {fmt_pct(r['pct_vencedor'])}" if criterio_venc == "% do Vencedor" else f"{r['vencedor']}: {fmt_int(r['votos_vencedor'])}"), 26),
                axis=1
            )
            color_map = {row['vencedor']: row['cor'] for _, row in gdf_merged.iterrows()}

            fig = px.bar(
                top10,
                x=eixo_x,
                y='NM_ZONA_MUN',
                orientation='h',
                color='vencedor',
                color_discrete_map=color_map,
                text='texto_barra',
                labels={eixo_x: criterio_venc, 'NM_ZONA_MUN': 'Zona Eleitoral', 'vencedor': 'Vencedor'}
            )
            fig.update_layout(
                height=430,
                margin=dict(l=0, r=0, t=10, b=0),
                showlegend=True,
                uniformtext=dict(minsize=8, mode='show'),
                yaxis=dict(tickfont=dict(size=9), automargin=True)
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with c_map:
            st.markdown(f"**Mapa de Vencedores por Zona Eleitoral**")
            gdf_map = df_view.copy()

            bounds = gdf_map.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
            zoom = 8 if rd_sel != "TODAS" else 7
            if mun_sel != "TODOS" or (busca_zona.strip() and len(df_view) == 1):
                zoom = 10

            m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")

            def style_zona(feature):
                c = feature['properties'].get('cor') or '#2980B9'
                return {
                    'fillColor': c,
                    'color': '#34495E',
                    'weight': 1,
                    'fillOpacity': 0.75
                }

            folium.GeoJson(
                gdf_map,
                style_function=style_zona,
                tooltip=folium.GeoJsonTooltip(
                    fields=['NM_ZONA_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'vencedor', 'pct_vencedor_fmt', 'votos_vencedor_fmt', 'segundo', 'pct_segundo_fmt', 'margem_pct_fmt', 'total_validos_fmt'],
                    aliases=['Zona:', 'Município:', 'Região:', '🥇 Vencedor:', '% Vencedor:', 'Votos Vencedor:', '🥈 2º Colocado:', '% 2º Lugar:', 'Margem de Vitória:', 'Total Válidos:']
                )
            ).add_to(m)

            st_folium(
                m,
                key=f"folium_zonas_todos_{rd_sel}_{mun_sel}_{ano}_{cargo}_{turno}",
                returned_objects=[],
                height=430,
                width="100%"
            )

        st.markdown("**Tabela Completa de Vencedores por Zona Eleitoral**")
        df_table_zonas = df_view[[
            'CD_ZONA', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'vencedor', 'partido_vencedor', 'pct_vencedor_fmt', 'votos_vencedor_fmt',
            'segundo', 'partido_segundo', 'pct_segundo_fmt', 'margem_pct_fmt', 'total_validos_fmt'
        ]].rename(columns={
            'CD_ZONA': 'Zona',
            'NM_MUN': 'Município',
            'REGIAO_DESENVOLVIMENTO': 'Região de Desenvolvimento',
            'vencedor': '🥇 1º Colocado (Vencedor)',
            'partido_vencedor': 'Part. Venc.',
            'pct_vencedor_fmt': '% Vencedor',
            'votos_vencedor_fmt': 'Votos Vencedor',
            'segundo': '🥈 2º Colocado',
            'partido_segundo': 'Part. 2º',
            'pct_segundo_fmt': '% 2º Lugar',
            'margem_pct_fmt': 'Margem (p.p.)',
            'total_validos_fmt': 'Total Válidos'
        })
        st.dataframe(df_table_zonas, use_container_width=True, hide_index=True)
        return

    # MODO INDIVIDUAL (Candidato ou Partido Selecionado)
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
    c_f1, c_f2, c_f3, c_f4 = st.columns([1.1, 1.3, 1.2, 1.4])
    with c_f1:
        rds_list = ["TODAS"] + sorted(gdf_zonas['REGIAO_DESENVOLVIMENTO'].dropna().unique().tolist())
        rd_sel = st.selectbox("Região:", rds_list, index=0, key="filtro_rd_zonas")
    with c_f2:
        if rd_sel != "TODAS":
            muns_disponiveis = sorted(gdf_zonas[gdf_zonas['REGIAO_DESENVOLVIMENTO'] == rd_sel]['NM_MUN'].dropna().unique().tolist())
        else:
            muns_disponiveis = sorted(gdf_zonas['NM_MUN'].dropna().unique().tolist())
        muns_list = ["TODOS"] + muns_disponiveis
        mun_sel = st.selectbox("Município:", muns_list, index=0, key=f"filtro_mun_zonas_{rd_sel}")
    with c_f3:
        criterio_analise = st.radio("Critério:", ["Total de Votos (Nominais)", "Percentual (%)"], horizontal=True, key="crit_zonas")
    with c_f4:
        busca_zona = st.text_input("🔍 Pesquisar Zona:", placeholder="Ex: 4, 149, Olinda, Recife...", key="busca_zona")
        
    if rd_sel != "TODAS":
        gdf_zonas = gdf_zonas[gdf_zonas['REGIAO_DESENVOLVIMENTO'] == rd_sel]
    if mun_sel != "TODOS":
        gdf_zonas = gdf_zonas[gdf_zonas['NM_MUN'] == mun_sel]
        
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
            
        fig.update_layout(
            height=430,
            margin=dict(l=0, r=0, t=10, b=0),
            uniformtext=dict(minsize=8, mode='show'),
            yaxis=dict(tickfont=dict(size=9), automargin=True)
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
        
    with c_map:
        st.markdown(f"**Mapa das Zonas Eleitorais ({criterio_analise})**")
        bounds = gdf_merged.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        if mun_sel != "TODOS":
            zoom = 11
        elif rd_sel != "TODAS":
            zoom = 8
        else:
            zoom = 7
        
        if busca_zona.strip() and len(df_view) == 1:
            z_bounds = df_view.iloc[0].geometry.bounds
            if len(z_bounds) == 4 and not any(pd.isna(z_bounds)):
                center_lat = (z_bounds[1] + z_bounds[3]) / 2
                center_lon = (z_bounds[0] + z_bounds[2]) / 2
                zoom = 12
        
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
        
        st_folium(
            m,
            key=f"folium_zonas_ind_{alvo_nome}_{rd_sel}_{mun_sel}_{criterio_analise}_{ano}_{cargo}_{turno}",
            returned_objects=[],
            height=430,
            width="100%"
        )
        
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
