import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd
from modules.geo_loader import load_regioes_gdf
from modules.data_loader import get_votos_municipios
from config import CORES_PARTIDOS, COR_PADRAO, fmt_int, fmt_pct, get_cores_foco, get_contrast_color, normalize_text, wrap_label

def render_tab_macrorregioes(ano, turno, cargo, modo, partido_selecionado, cand_selecionado, df_mun_map, modo_todos=None):
    if modo_todos is None:
        modo_todos = (cand_selecionado is None and partido_selecionado is None)

    if modo_todos:
        st.markdown("### 🌍 Macrorregiões — Mapa de Vencedores (12 Regiões de Desenvolvimento)")
        st.caption("Liderança eleitoral e placar de vitórias em cada uma das 12 Macrorregiões de Pernambuco.")
        
        from modules.data_loader import get_vencedores_regioes
        df_venc = get_vencedores_regioes(ano, turno, cargo, modo=modo, df_mun_map=df_mun_map)
        
        if len(df_venc) == 0:
            st.warning("Nenhum dado encontrado para os filtros selecionados.")
            return

        # Placar de vitórias por candidato/partido
        venc_counts = df_venc['vencedor'].value_counts()
        lider_cand = venc_counts.index[0]
        lider_vitorias = venc_counts.iloc[0]
        
        # Maior e menor margem
        df_sorted_margem = df_venc.sort_values('margem_pct', ascending=False)
        top_margem = df_sorted_margem.iloc[0]
        menor_margem = df_sorted_margem.iloc[-1]
        
        # KPIs Rápidos
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Regiões Analisadas", f"{len(df_venc)}")
        col2.metric("Líder em Regiões", f"{lider_cand} ({lider_vitorias} de {len(df_venc)})")
        col3.metric("Maior Margem", f"+{fmt_pct(top_margem['margem_pct'])} ({top_margem['REGIAO_DESENVOLVIMENTO']})")
        col4.metric("Disputa Mais Acirrada", f"+{fmt_pct(menor_margem['margem_pct'])} ({menor_margem['REGIAO_DESENVOLVIMENTO']})")
        
        # Placar de Vitórias e Filtro Clicável por Vencedor
        cand_part_map = dict(zip(df_venc['vencedor'], df_venc['partido_vencedor']))
        cands_ordenados_reg = list(venc_counts.index)

        # Gerenciamento de Estado no session_state com callbacks
        sb_macro_key = f"sb_venc_macro_{ano}_{cargo}_{turno}"
        if sb_macro_key not in st.session_state:
            st.session_state[sb_macro_key] = "TODAS"

        if st.session_state[sb_macro_key] != "TODAS" and st.session_state[sb_macro_key] not in cands_ordenados_reg:
            st.session_state[sb_macro_key] = "TODAS"

        def _set_filtro_venc_macro(cand_nome):
            st.session_state[sb_macro_key] = cand_nome

        # 1. Controles de Seleção (Dropdown com busca + Botão Reset)
        c_sel_macro, c_btn_limpar_m = st.columns([3.8, 1.2])

        opcoes_select_m = ["TODAS"] + cands_ordenados_reg
        def format_select_reg(c):
            if c == "TODAS":
                return f"🌐 TODAS AS REGIÕES (Visão Geral — {len(df_venc)} regiões)"
            cnt = venc_counts.get(c, 0)
            pct = 100.0 * cnt / len(df_venc) if len(df_venc) > 0 else 0
            part = cand_part_map.get(c, "")
            part_str = f" ({part})" if part and part != '-' else ""
            idx = cands_ordenados_reg.index(c) + 1
            medal = "🥇 " if idx == 1 else ("🥈 " if idx == 2 else ("🥉 " if idx == 3 else f"#{idx} "))
            return f"{medal}{c}{part_str} — {cnt} {'região' if cnt == 1 else 'regiões'} ({pct:.1f}%)"

        with c_sel_macro:
            cand_filtro_clique = st.selectbox(
                "🎯 Filtrar e Isolar Regiões Conquistadas por um Vencedor:",
                opcoes_select_m,
                format_func=format_select_reg,
                key=sb_macro_key
            )

        with c_btn_limpar_m:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.button(
                "🔄 Ver Todas",
                key=f"btn_reset_venc_macro_{ano}_{cargo}_{turno}",
                use_container_width=True,
                disabled=(cand_filtro_clique == "TODAS"),
                on_click=_set_filtro_venc_macro,
                args=("TODAS",)
            )

        # 2. Quick-Click Buttons para Top Candidatos
        if len(cands_ordenados_reg) > 1:
            top_quick_m = cands_ordenados_reg[:min(5, len(cands_ordenados_reg))]
            cols_quick_m = st.columns(len(top_quick_m) + 1)
            with cols_quick_m[0]:
                st.button(
                    "🌐 Todas",
                    key=f"qk_macro_todas_{ano}_{cargo}_{turno}",
                    use_container_width=True,
                    type="primary" if cand_filtro_clique == "TODAS" else "secondary",
                    on_click=_set_filtro_venc_macro,
                    args=("TODAS",)
                )
            for idx_qm, cqm in enumerate(top_quick_m):
                with cols_quick_m[idx_qm + 1]:
                    cnt_qm = venc_counts.get(cqm, 0)
                    label_qm = f"{cqm.split()[0]} ({cnt_qm})"
                    is_qm_active = (cand_filtro_clique == cqm)
                    st.button(
                        label_qm,
                        key=f"qk_macro_{idx_qm}_{ano}_{cargo}_{turno}",
                        use_container_width=True,
                        type="primary" if is_qm_active else "secondary",
                        on_click=_set_filtro_venc_macro,
                        args=(cqm,)
                    )

        # 3. Badges Coloridos Oficiais
        badges = []
        for cand, cnt in venc_counts.items():
            bg_c = get_cores_foco(cand, cand_part_map.get(cand))[0]
            fg_c = get_contrast_color(bg_c)
            is_ativo = (cand_filtro_clique == cand)

            if cand_filtro_clique == "TODAS":
                opacity = "1.0"
                border = f"1px solid {bg_c}"
                box_shadow = "none"
            elif is_ativo:
                opacity = "1.0"
                border = "3px solid #1A252F"
                box_shadow = f"0 0 10px {bg_c}"
            else:
                opacity = "0.40"
                border = "1px solid #D5D8DC"
                box_shadow = "none"

            badges.append(
                f"<span style='display: inline-block; background-color: {bg_c}; color: {fg_c}; "
                f"padding: 4px 10px; border-radius: 12px; margin: 3px 6px 3px 0; font-weight: bold; font-size: 0.88rem; "
                f"opacity: {opacity}; border: {border}; box-shadow: {box_shadow}; transition: all 0.2s;'>"
                f"{'⭐ ' if is_ativo else ''}{cand}: {cnt} {'região' if cnt == 1 else 'regiões'} ({cnt/len(df_venc)*100:.1f}%)"
                f"</span>"
            )
        placar_html = " ".join(badges)
        st.markdown(f"**Placar de Regiões Conquistadas:**<br>{placar_html}", unsafe_allow_html=True)

        if cand_filtro_clique and cand_filtro_clique != "TODAS":
            st.info(f"🎯 **Filtro Ativo:** Exibindo as regiões onde **{cand_filtro_clique} ({cand_part_map.get(cand_filtro_clique, '')})** foi o mais votado. Clique em 'Ver Todas' para ver o mapa geral.")

        st.divider()
        
        # Atribuir cores dos vencedores para plotagem
        df_venc['cor'] = df_venc.apply(lambda r: get_cores_foco(r['vencedor'], r['partido_vencedor'])[0], axis=1)
        df_venc['pct_vencedor_fmt'] = df_venc['pct_vencedor'].apply(fmt_pct)
        df_venc['pct_segundo_fmt'] = df_venc['pct_segundo'].apply(fmt_pct)
        df_venc['margem_pct_fmt'] = df_venc['margem_pct'].apply(lambda v: f"+{fmt_pct(v)}")
        df_venc['votos_vencedor_fmt'] = df_venc['votos_vencedor'].apply(fmt_int)
        df_venc['votos_segundo_fmt'] = df_venc['votos_segundo'].apply(fmt_int)
        df_venc['total_validos_fmt'] = df_venc['total_validos'].apply(fmt_int)
        
        c_map, c_chart = st.columns([1.1, 0.9])
        
        with c_chart:
            st.markdown("**Margem de Vitória do Vencedor por Região (p.p.)**")
            df_plot = df_venc.sort_values('margem_pct', ascending=True).copy()
            df_plot['rotulo_barra'] = df_plot.apply(
                lambda r: wrap_label(f"{r['vencedor']}: +{fmt_pct(r['margem_pct'])} (sobre {r['segundo']})", 26), axis=1
            )
            color_map = {row['vencedor']: row['cor'] for _, row in df_venc.iterrows()}
            
            fig = px.bar(
                df_plot,
                x='margem_pct',
                y='REGIAO_DESENVOLVIMENTO',
                orientation='h',
                color='vencedor',
                color_discrete_map=color_map,
                text='rotulo_barra',
                labels={'margem_pct': 'Margem de Vitória (p.p.)', 'REGIAO_DESENVOLVIMENTO': 'Região', 'vencedor': 'Vencedor'}
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
            st.markdown("**Mapa de Vencedores por Macrorregião**")
            gdf_regioes = load_regioes_gdf().copy()
            gdf_regioes = gdf_regioes.merge(df_venc, on='REGIAO_DESENVOLVIMENTO', how='left')
            
            m = folium.Map(location=[-8.35, -37.8], zoom_start=7, tiles="OpenStreetMap")
            
            # Polígonos coloridos pela cor do vencedor com destaque para o filtro ativo
            def style_fn(feature):
                venc = feature['properties'].get('vencedor')
                cor = feature['properties'].get('cor') or '#2980B9'
                if cand_filtro_clique and cand_filtro_clique != "TODAS":
                    if venc == cand_filtro_clique:
                        return {
                            'fillColor': cor,
                            'color': '#1A252F',
                            'weight': 2.5,
                            'fillOpacity': 0.90
                        }
                    else:
                        return {
                            'fillColor': '#EAEDED',
                            'color': '#BDC3C7',
                            'weight': 0.8,
                            'fillOpacity': 0.20
                        }
                return {
                    'fillColor': cor,
                    'color': '#2C3E50',
                    'weight': 1.5,
                    'fillOpacity': 0.75
                }
                
            folium.GeoJson(
                gdf_regioes,
                style_function=style_fn,
                tooltip=folium.GeoJsonTooltip(
                    fields=['REGIAO_DESENVOLVIMENTO', 'vencedor', 'pct_vencedor_fmt', 'segundo', 'pct_segundo_fmt', 'margem_pct_fmt', 'total_validos_fmt'],
                    aliases=['Região:', '🥇 1º Colocado:', '% 1º Lugar:', '🥈 2º Colocado:', '% 2º Lugar:', 'Margem de Vitória:', 'Total Válidos:']
                )
            ).add_to(m)
            
            st_folium(
                m,
                key=f"folium_macro_{cand_filtro_clique}_{ano}_{cargo}_{turno}",
                returned_objects=[],
                height=430,
                width="100%"
            )
            
        st.markdown("**Tabela Completa de Vencedores por Macrorregião**")
        df_tbl_view = df_venc if (not cand_filtro_clique or cand_filtro_clique == "TODAS") else df_venc[df_venc['vencedor'] == cand_filtro_clique]
        df_tbl = df_tbl_view[[
            'REGIAO_DESENVOLVIMENTO', 'vencedor', 'partido_vencedor', 'pct_vencedor_fmt', 'votos_vencedor_fmt',
            'segundo', 'partido_segundo', 'pct_segundo_fmt', 'margem_pct_fmt', 'total_validos_fmt'
        ]].rename(columns={
            'REGIAO_DESENVOLVIMENTO': 'Região de Desenvolvimento',
            'vencedor': '1º Colocado (Vencedor)',
            'partido_vencedor': 'Part. Venc.',
            'pct_vencedor_fmt': '% Vencedor',
            'votos_vencedor_fmt': 'Votos Vencedor',
            'segundo': '2º Colocado',
            'partido_segundo': 'Part. 2º',
            'pct_segundo_fmt': '% 2º Lugar',
            'margem_pct_fmt': 'Margem (p.p.)',
            'total_validos_fmt': 'Total Válidos'
        })
        st.dataframe(df_tbl, use_container_width=True, hide_index=True)
        from modules.painel_eleitos import render_painel_eleitos
        render_painel_eleitos(ano, cargo, df_mun_map, tab_origem="macro_todos")
        return

    # MODO INDIVIDUAL (Candidato ou Partido Específico)
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
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending', 'tickfont': dict(size=9), 'automargin': True},
            height=420,
            margin=dict(l=0, r=0, t=10, b=0),
            uniformtext=dict(minsize=8, mode='show')
        )
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
        
        folium.GeoJson(
            gdf_regioes,
            style_function=lambda x: {'fillColor': 'transparent', 'color': '#2C3E50', 'weight': 1.5},
            tooltip=folium.GeoJsonTooltip(
                fields=['REGIAO_DESENVOLVIMENTO', 'votos_fmt', 'pct_votos_fmt', 'total_validos_fmt'],
                aliases=['Região:', 'Votos Obtidos:', '% Votos:', 'Total Válidos:']
            )
        ).add_to(m)
        
        st_folium(
            m,
            key=f"folium_macro_ind_{alvo_nome}_{criterio_analise}_{ano}_{cargo}_{turno}",
            returned_objects=[],
            height=420,
            width="100%"
        )
        
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
    from modules.painel_eleitos import render_painel_eleitos
    render_painel_eleitos(ano, cargo, df_mun_map, tab_origem="macro_indiv")
