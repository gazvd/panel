import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
from modules.geo_loader import load_municipios_gdf
from modules.data_loader import get_votos_municipios
from config import fmt_int, fmt_pct, get_cores_foco, get_contrast_color, normalize_text, wrap_label

def render_tab_municipios(ano, turno, cargo, modo, partido_selecionado, cand_selecionado, df_mun_map, modo_todos=None):
    if modo_todos is None:
        modo_todos = (cand_selecionado is None and partido_selecionado is None)

    if modo_todos:
        st.markdown("### 🏛️ Municípios — Mapa de Vencedores (185 Municípios de Pernambuco)")
        st.caption("Distribuição geográfica dos candidatos mais votados em cada município e margens de vitória.")
        
        from modules.data_loader import get_vencedores_municipios
        df_venc = get_vencedores_municipios(ano, turno, cargo, modo=modo)
        df_venc['CD_MUN'] = df_venc['id_municipio'].astype(str)
        
        # Merge com metadados dos municípios
        df_mun_merged = df_mun_map.merge(df_venc, on='CD_MUN', how='left')
        
        if len(df_mun_merged) == 0:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            return

        # Atribuir cores dos vencedores
        df_mun_merged['cor'] = df_mun_merged.apply(lambda r: get_cores_foco(r['vencedor'], r['partido_vencedor'])[0] if pd.notna(r['vencedor']) else '#2980B9', axis=1)
        df_mun_merged['pct_vencedor_fmt'] = df_mun_merged['pct_vencedor'].apply(fmt_pct)
        df_mun_merged['pct_segundo_fmt'] = df_mun_merged['pct_segundo'].apply(fmt_pct)
        df_mun_merged['margem_pct_fmt'] = df_mun_merged['margem_pct'].apply(lambda v: f"+{fmt_pct(v)}")
        df_mun_merged['margem_votos_fmt'] = df_mun_merged['margem_votos'].apply(lambda v: f"+{fmt_int(v)}")
        df_mun_merged['votos_vencedor_fmt'] = df_mun_merged['votos_vencedor'].apply(fmt_int)
        df_mun_merged['votos_segundo_fmt'] = df_mun_merged['votos_segundo'].apply(fmt_int)
        df_mun_merged['total_validos_fmt'] = df_mun_merged['total_validos'].apply(fmt_int)

        # Filtros
        c_f1, c_f2, c_f3 = st.columns([1.0, 1.3, 1.7])
        with c_f1:
            rds_list = ["TODAS"] + sorted(df_mun_merged['REGIAO_DESENVOLVIMENTO'].dropna().unique().tolist())
            rd_filtro = st.selectbox("Região:", rds_list, index=0, key="filtro_rd_venc_mun")
        with c_f2:
            criterio_venc = st.radio("Critério de Destaque:", ["Margem de Vitória (p.p.)", "% do Vencedor", "Votos do Vencedor"], horizontal=True, key="crit_venc_mun")
        with c_f3:
            busca_mun = st.text_input("🔍 Pesquisar Município:", placeholder="Ex: Caruaru, Petrolina, Olinda...", key="busca_venc_mun")

        df_view = df_mun_merged if rd_filtro == "TODAS" else df_mun_merged[df_mun_merged['REGIAO_DESENVOLVIMENTO'] == rd_filtro].copy()

        if busca_mun.strip():
            q_m = normalize_text(busca_mun)
            df_view = df_view[df_view['NM_MUN'].apply(lambda x: q_m in normalize_text(x))].reset_index(drop=True)
            if len(df_view) == 1:
                m_sel = df_view.iloc[0]
                st.success(
                    f"🎯 **{m_sel['NM_MUN']}** ({m_sel['REGIAO_DESENVOLVIMENTO']}) — "
                    f"🥇 **{m_sel['vencedor']} ({m_sel['partido_vencedor']})**: {m_sel['votos_vencedor_fmt']} votos ({m_sel['pct_vencedor_fmt']}) | "
                    f"🥈 **{m_sel['segundo']} ({m_sel['partido_segundo']})**: {m_sel['votos_segundo_fmt']} votos ({m_sel['pct_segundo_fmt']}) | "
                    f"Margem: **{m_sel['margem_pct_fmt']}** ({m_sel['margem_votos_fmt']} votos) | "
                    f"Total Válidos: **{m_sel['total_validos_fmt']}**"
                )
            elif len(df_view) == 0:
                st.warning(f"Nenhum município encontrado com o termo '{busca_mun}'.")

        # Placar de vitórias e Filtro Clicável por Vencedor
        df_view_base = df_view.copy()
        venc_counts = df_view_base['vencedor'].value_counts()
        lider_cand = venc_counts.index[0] if len(venc_counts) > 0 else "-"
        lider_vitorias = venc_counts.iloc[0] if len(venc_counts) > 0 else 0

        df_s_margem = df_view_base.sort_values('margem_pct', ascending=False)
        top_margem = df_s_margem.iloc[0] if len(df_s_margem) > 0 else None
        menor_margem = df_s_margem.iloc[-1] if len(df_s_margem) > 0 else None

        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Municípios Analisados", f"{len(df_view_base)}")
        col2.metric("Líder em Vitórias", f"{lider_cand} ({lider_vitorias} mun.)" if lider_cand != "-" else "-")
        col3.metric("Maior Margem", f"+{fmt_pct(top_margem['margem_pct'])} ({top_margem['NM_MUN']})" if top_margem is not None else "-")
        col4.metric("Disputa Mais Acirrada", f"+{fmt_pct(menor_margem['margem_pct'])} ({menor_margem['NM_MUN']})" if menor_margem is not None else "-")

        df_view = df_view_base.copy()

        # Placar exclusivo para análise por partido (simples e direto)
        if modo == "Partido":
            badges = []
            for partido, cnt in venc_counts.items():
                bg_c = get_cores_foco(sigla_partido=partido)[0]
                fg_c = get_contrast_color(bg_c)
                badges.append(
                    f"<span style='background-color: {bg_c}; color: {fg_c}; padding: 4px 10px; border-radius: 12px; margin-right: 8px; font-weight: bold; font-size: 0.88rem;'>"
                    f"{partido}: {cnt} {'cidade' if cnt == 1 else 'cidades'} ({cnt/len(df_view_base)*100:.1f}%)"
                    f"</span>"
                )
            placar_html = " ".join(badges)
            st.markdown(f"**Placar de Cidades Conquistadas por Partido:** {placar_html}", unsafe_allow_html=True)
            st.write("")

        st.divider()

        # Ordenar df_view conforme critério
        if criterio_venc == "Margem de Vitória (p.p.)":
            df_view_plot = df_view.sort_values('margem_pct', ascending=False).reset_index(drop=True)
        elif criterio_venc == "% do Vencedor":
            df_view_plot = df_view.sort_values('pct_vencedor', ascending=False).reset_index(drop=True)
        else:
            df_view_plot = df_view.sort_values('votos_vencedor', ascending=False).reset_index(drop=True)

        c_map, c_rank = st.columns([1.2, 0.8])

        with c_rank:
            st.markdown(f"**Top 10 Municípios ({criterio_venc})**")
            top10 = df_view_plot.head(10).sort_values(
                'margem_pct' if criterio_venc == "Margem de Vitória (p.p.)" else ('pct_vencedor' if criterio_venc == "% do Vencedor" else 'votos_vencedor'),
                ascending=True
            ).copy()
            
            eixo_x = 'margem_pct' if criterio_venc == "Margem de Vitória (p.p.)" else ('pct_vencedor' if criterio_venc == "% do Vencedor" else 'votos_vencedor')
            top10['texto_barra'] = top10.apply(
                lambda r: wrap_label(f"{r['vencedor']}: +{fmt_pct(r['margem_pct'])}" if criterio_venc == "Margem de Vitória (p.p.)"
                else (f"{r['vencedor']}: {fmt_pct(r['pct_vencedor'])}" if criterio_venc == "% do Vencedor" else f"{r['vencedor']}: {fmt_int(r['votos_vencedor'])}"), 26),
                axis=1
            )
            color_map = {row['vencedor']: row['cor'] for _, row in df_mun_merged.iterrows()}

            fig = px.bar(
                top10,
                x=eixo_x,
                y='NM_MUN',
                orientation='h',
                color='vencedor',
                color_discrete_map=color_map,
                text='texto_barra',
                labels={eixo_x: criterio_venc, 'NM_MUN': 'Município', 'vencedor': 'Vencedor'}
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
            st.markdown(f"**Mapa de Vencedores por Município**")
            gdf_mun = load_municipios_gdf().copy()
            if rd_filtro != "TODAS":
                gdf_mun = gdf_mun[gdf_mun['REGIAO_DESENVOLVIMENTO'] == rd_filtro]

            gdf_mun['CD_MUN'] = gdf_mun['CD_MUN'].astype(str)
            gdf_mun = gdf_mun.merge(df_mun_merged[['CD_MUN', 'vencedor', 'partido_vencedor', 'pct_vencedor_fmt', 'votos_vencedor_fmt', 'segundo', 'partido_segundo', 'pct_segundo_fmt', 'margem_pct_fmt', 'margem_votos_fmt', 'total_validos_fmt', 'cor']], on='CD_MUN', how='left')

            bounds = gdf_mun.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
            zoom = 8 if rd_filtro != "TODAS" else 7

            if busca_mun.strip() and len(df_view) == 1:
                m_bounds = gdf_mun[gdf_mun['CD_MUN'] == df_view.iloc[0]['CD_MUN']].total_bounds
                if len(m_bounds) == 4 and not any(pd.isna(m_bounds)):
                    center_lat = (m_bounds[1] + m_bounds[3]) / 2
                    center_lon = (m_bounds[0] + m_bounds[2]) / 2
                    zoom = 10

            m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")

            def style_mun(feature):
                c = feature['properties'].get('cor') or '#2980B9'
                return {
                    'fillColor': c,
                    'color': '#34495E',
                    'weight': 1,
                    'fillOpacity': 0.75
                }

            folium.GeoJson(
                gdf_mun,
                style_function=style_mun,
                tooltip=folium.GeoJsonTooltip(
                    fields=['NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'vencedor', 'pct_vencedor_fmt', 'votos_vencedor_fmt', 'segundo', 'pct_segundo_fmt', 'margem_pct_fmt', 'total_validos_fmt'],
                    aliases=['Município:', 'Região:', '🥇 Vencedor:', '% Vencedor:', 'Votos Vencedor:', '🥈 2º Colocado:', '% 2º Lugar:', 'Margem de Vitória:', 'Total Válidos:']
                )
            ).add_to(m)

            st_folium(
                m,
                key=f"folium_mun_todos_{rd_filtro}_{criterio_venc}_{ano}_{cargo}_{turno}",
                returned_objects=[],
                height=430,
                width="100%"
            )

        st.markdown("**Tabela Completa de Vencedores por Município**")
        df_table_mun = df_view[[
            'NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'vencedor', 'partido_vencedor', 'pct_vencedor_fmt', 'votos_vencedor_fmt',
            'segundo', 'partido_segundo', 'pct_segundo_fmt', 'margem_pct_fmt', 'total_validos_fmt'
        ]].rename(columns={
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
        st.dataframe(df_table_mun, use_container_width=True, hide_index=True)

        cd_mun_foco = None
        nm_mun_foco = None
        if busca_mun.strip() and len(df_view) == 1:
            cd_mun_foco = df_view.iloc[0]['CD_MUN']
            nm_mun_foco = df_view.iloc[0]['NM_MUN']

        from modules.painel_eleitos import render_painel_eleitos
        render_painel_eleitos(
            ano=ano,
            cargo=cargo,
            df_mun_map=df_mun_map,
            cd_mun_selecionado=cd_mun_foco,
            nm_mun_selecionado=nm_mun_foco,
            regiao_selecionada=rd_filtro if rd_filtro != "TODAS" else None,
            tab_origem="mun_todos"
        )
        return

    # MODO INDIVIDUAL (Candidato ou Partido Selecionado)
    st.markdown("### 🏛️ Municípios (185 Municípios de Pernambuco)")
    st.caption("Distribuição eleitoral e comparativo municipal em todo o território estadual.")
    
    cand_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else None
    hex_cor, scale_plotly, scale_folium = get_cores_foco(cand_nome, partido_selecionado)
    
    c_num = cand_selecionado['numero_candidato'] if (cand_selecionado is not None and pd.notna(cand_selecionado.get('numero_candidato'))) else None
    p_sigla = partido_selecionado if modo == "Partido" else (cand_selecionado.get('sigla_partido') if (c_num is None and cand_selecionado is not None) else None)
    alvo_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else (partido_selecionado if partido_selecionado else "Total")
    
    # Obter dados de votos
    df_votos = get_votos_municipios(ano, turno, cargo, partido=p_sigla, numero_candidato=c_num)
    df_votos['CD_MUN'] = df_votos['id_municipio'].astype(str)
    
    # Merge com metadados dos municípios
    df_mun_merged = df_mun_map.merge(df_votos[['CD_MUN', 'votos', 'total_validos', 'pct_votos']], on='CD_MUN', how='left')
    df_mun_merged['votos'] = df_mun_merged['votos'].fillna(0).astype(int)
    df_mun_merged['total_validos'] = df_mun_merged['total_validos'].fillna(0).astype(int)
    df_mun_merged['pct_votos'] = df_mun_merged['pct_votos'].fillna(0.0)
    
    # Controles de Filtro, Critério e Busca Inteligente
    c_filtro1, c_filtro2, c_filtro3 = st.columns([1.0, 1.3, 1.7])
    with c_filtro1:
        rds_list = ["TODAS"] + sorted(df_mun_merged['REGIAO_DESENVOLVIMENTO'].unique().tolist())
        rd_filtro = st.selectbox("Região:", rds_list, index=0)
    with c_filtro2:
        criterio_analise = st.radio("Critério de Análise:", ["Total de Votos (Nominais)", "Percentual (%)"], horizontal=True, key="crit_mun")
    with c_filtro3:
        busca_mun = st.text_input("🔍 Pesquisar Município:", placeholder="Ex: Caruaru, Petrolina, Olinda...", key="busca_mun")
        
    df_view = df_mun_merged if rd_filtro == "TODAS" else df_mun_merged[df_mun_merged['REGIAO_DESENVOLVIMENTO'] == rd_filtro]
    
    if busca_mun.strip():
        q_m = normalize_text(busca_mun)
        df_view = df_view[df_view['NM_MUN'].apply(lambda x: q_m in normalize_text(x))].reset_index(drop=True)
        if len(df_view) == 1:
            m_sel = df_view.iloc[0]
            rank_vol = (df_mun_merged.sort_values('votos', ascending=False)['CD_MUN'].tolist().index(m_sel['CD_MUN'])) + 1
            rank_pct = (df_mun_merged.sort_values('pct_votos', ascending=False)['CD_MUN'].tolist().index(m_sel['CD_MUN'])) + 1
            st.success(
                f"🎯 **{m_sel['NM_MUN']}** ({m_sel['REGIAO_DESENVOLVIMENTO']}) — "
                f"**{fmt_int(m_sel['votos'])} votos** ({fmt_pct(m_sel['pct_votos'])}) de {alvo_nome} | "
                f"Total Válidos: **{fmt_int(m_sel['total_validos'])}** | "
                f"Ranking Estadual: **#{rank_vol}** em votos nominais e **#{rank_pct}** em % dos válidos."
            )
        elif len(df_view) == 0:
            st.warning(f"Nenhum município encontrado com o termo '{busca_mun}'.")
    
    if criterio_analise == "Total de Votos (Nominais)":
        df_view = df_view.sort_values('votos', ascending=False).reset_index(drop=True)
    else:
        df_view = df_view.sort_values('pct_votos', ascending=False).reset_index(drop=True)
    
    # KPIs rápidos
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Municípios Analisados", f"{len(df_view)}")
    top_vol = df_view.sort_values('votos', ascending=False).iloc[0] if len(df_view) > 0 else None
    col2.metric("Maior Volume", f"{fmt_int(top_vol['votos'])} votos ({top_vol['NM_MUN']})" if top_vol is not None else "-")
    top_pct = df_view.sort_values('pct_votos', ascending=False).iloc[0] if len(df_view) > 0 else None
    col3.metric("Maior % Obtido", f"{fmt_pct(top_pct['pct_votos'])} ({top_pct['NM_MUN']})" if top_pct is not None else "-")
    col4.metric("Total Votos na Seleção", fmt_int(df_view['votos'].sum()))
    
    st.divider()
    
    # Mapa + Top 10
    c_map, c_rank = st.columns([1.2, 0.8])
    
    with c_rank:
        if criterio_analise == "Total de Votos (Nominais)":
            st.markdown(f"**Top 10 Municípios (Votos Nominais)**")
            top10 = df_view.head(10).sort_values('votos', ascending=True).copy()
            top10['texto_barra'] = top10['votos'].apply(fmt_int)
            fig = px.bar(
                top10,
                x='votos',
                y='NM_MUN',
                orientation='h',
                text='texto_barra',
                color='votos',
                color_continuous_scale=scale_plotly,
                labels={'votos': 'Votos Nominais', 'NM_MUN': 'Município'}
            )
        else:
            st.markdown(f"**Top 10 Municípios (% Votos Válidos)**")
            top10 = df_view.head(10).sort_values('pct_votos', ascending=True).copy()
            top10['texto_barra'] = top10['pct_votos'].apply(fmt_pct)
            fig = px.bar(
                top10,
                x='pct_votos',
                y='NM_MUN',
                orientation='h',
                text='texto_barra',
                color='pct_votos',
                color_continuous_scale=scale_plotly,
                labels={'pct_votos': '% Válidos', 'NM_MUN': 'Município'}
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
        st.markdown(f"**Mapa Municipal de Pernambuco ({criterio_analise})**")
        gdf_mun = load_municipios_gdf().copy()
        if rd_filtro != "TODAS":
            gdf_mun = gdf_mun[gdf_mun['REGIAO_DESENVOLVIMENTO'] == rd_filtro]
            
        gdf_mun['CD_MUN'] = gdf_mun['CD_MUN'].astype(str)
        gdf_mun = gdf_mun.merge(df_view[['CD_MUN', 'votos', 'total_validos', 'pct_votos']], on='CD_MUN', how='left')
        gdf_mun['votos'] = gdf_mun['votos'].fillna(0).astype(int)
        gdf_mun['pct_votos'] = gdf_mun['pct_votos'].fillna(0.0)
        gdf_mun['votos_fmt'] = gdf_mun['votos'].apply(fmt_int)
        gdf_mun['total_validos_fmt'] = gdf_mun['total_validos'].apply(fmt_int)
        gdf_mun['pct_votos_fmt'] = gdf_mun['pct_votos'].apply(fmt_pct)
        
        # Centro do mapa
        bounds = gdf_mun.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        zoom = 8 if rd_filtro != "TODAS" else 7
        
        if busca_mun.strip() and len(df_view) == 1:
            m_bounds = gdf_mun[gdf_mun['CD_MUN'] == df_view.iloc[0]['CD_MUN']].total_bounds
            if len(m_bounds) == 4 and not any(pd.isna(m_bounds)):
                center_lat = (m_bounds[1] + m_bounds[3]) / 2
                center_lon = (m_bounds[0] + m_bounds[2]) / 2
                zoom = 10
        
        coluna_cor = "votos" if criterio_analise == "Total de Votos (Nominais)" else "pct_votos"
        legenda_mapa = f"Total de Votos de {alvo_nome}" if criterio_analise == "Total de Votos (Nominais)" else f"% Votos de {alvo_nome}"
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")
        
        folium.Choropleth(
            geo_data=gdf_mun.__geo_interface__,
            name="choropleth",
            data=gdf_mun,
            columns=["CD_MUN", coluna_cor],
            key_on="feature.properties.CD_MUN",
            fill_color=scale_folium,
            fill_opacity=0.75,
            line_opacity=0.3,
            legend_name=legenda_mapa
        ).add_to(m)
        
        folium.GeoJson(
            gdf_mun,
            style_function=lambda x: {'fillColor': 'transparent', 'color': '#34495E', 'weight': 1},
            tooltip=folium.GeoJsonTooltip(
                fields=['NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'votos_fmt', 'pct_votos_fmt', 'total_validos_fmt'],
                aliases=['Município:', 'Região:', 'Votos Obtidos:', '% dos Válidos:', 'Válidos no Município:']
            )
        ).add_to(m)
        
        st_folium(
            m,
            key=f"folium_mun_ind_{alvo_nome}_{rd_filtro}_{criterio_analise}_{ano}_{cargo}_{turno}",
            returned_objects=[],
            height=430,
            width="100%"
        )
        
    st.markdown("**Tabela Completa de Resultados por Município**")
    df_table_mun = df_view.copy()
    df_table_mun['Votos Obtidos'] = df_table_mun['votos'].apply(fmt_int)
    df_table_mun['Total Votos Válidos'] = df_table_mun['total_validos'].apply(fmt_int)
    df_table_mun['% Votos Válidos'] = df_table_mun['pct_votos'].apply(fmt_pct)
    
    st.dataframe(
        df_table_mun[['NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'Votos Obtidos', 'Total Votos Válidos', '% Votos Válidos']].rename(columns={
            'NM_MUN': 'Município',
            'REGIAO_DESENVOLVIMENTO': 'Região de Desenvolvimento'
        }),
        use_container_width=True,
        hide_index=True
    )

    cd_mun_foco = None
    nm_mun_foco = None
    if busca_mun.strip() and len(df_view) == 1:
        cd_mun_foco = df_view.iloc[0]['CD_MUN']
        nm_mun_foco = df_view.iloc[0]['NM_MUN']

    from modules.painel_eleitos import render_painel_eleitos
    render_painel_eleitos(
        ano=ano,
        cargo=cargo,
        df_mun_map=df_mun_map,
        cd_mun_selecionado=cd_mun_foco,
        nm_mun_selecionado=nm_mun_foco,
        regiao_selecionada=rd_filtro if rd_filtro != "TODAS" else None,
        tab_origem="mun_indiv"
    )
