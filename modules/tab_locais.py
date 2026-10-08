import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from modules.data_loader import get_locais_votacao_base
import duckdb
from config import PATH_RESULTADOS, fmt_int, fmt_pct, get_cores_foco, normalize_text

def render_tab_locais(ano, turno, cargo, modo, partido_selecionado, cand_selecionado, df_mun_map):
    st.markdown("### 🏫 Locais de Votação (3.406 Colégios Eleitorais)")
    st.caption("Mapeamento pontual dos locais de votação com densidade de votos e detalhes de seções.")
    
    # Seletor de Município e Critério
    muns_nomes = sorted(df_mun_map['NM_MUN'].unique().tolist())
    recife_idx = muns_nomes.index("Recife") if "Recife" in muns_nomes else 0
    
    c1, c2, c3 = st.columns([1.1, 1.3, 1.6])
    with c1:
        mun_nome_sel = st.selectbox("Escolha o Município:", muns_nomes, index=recife_idx, key="locais_mun_sel")
    with c2:
        criterio_analise = st.radio("Critério de Ordenação:", ["Total de Votos (Nominais)", "Percentual (%)"], horizontal=True, key="crit_locais")
    with c3:
        busca_local = st.text_input("🔍 Pesquisar Escola, Zona ou Seção:", placeholder="Ex: 125, Paulo Freire, Zona 4, Boa Viagem...", key="busca_local")
        
    mun_info = df_mun_map[df_mun_map['NM_MUN'] == mun_nome_sel].iloc[0]
    cd_mun_sel = int(mun_info['CD_MUN'])
    
    # Carregar locais de votação do município
    df_locais = get_locais_votacao_base()
    locais_mun = df_locais[df_locais['municipio'].str.upper() == mun_nome_sel.upper()].copy()
    
    if len(locais_mun) == 0:
        st.warning(f"Nenhum colégio eleitoral encontrado para {mun_nome_sel}.")
        return
        
    c_num = cand_selecionado['numero_candidato'] if (cand_selecionado is not None and pd.notna(cand_selecionado.get('numero_candidato'))) else None
    p_sigla = partido_selecionado if modo == "Partido" else (cand_selecionado.get('sigla_partido') if (c_num is None and cand_selecionado is not None) else None)
    alvo_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else (partido_selecionado if partido_selecionado else "Total")
    
    cand_nome = cand_selecionado['nome_urna'] if cand_selecionado is not None else None
    partido_nome = partido_selecionado if modo == "Partido" else (cand_selecionado.get('sigla_partido') if cand_selecionado else None)
    hex_cor, scale_plotly, scale_folium = get_cores_foco(cand_nome, partido_nome)
    
    # Consultar votos das seções desse município via DuckDB
    con = duckdb.connect()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    
    where_base = f"ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND id_municipio = {cd_mun_sel}"
    
    # Total válidos por seção
    q_tot = f"""
        SELECT zona, secao, SUM(total_votos) as total_validos
        FROM '{res_path}'
        WHERE {where_base}
        GROUP BY zona, secao
    """
    
    # Votos do candidato/partido por seção
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
    
    # Cruzar com locais_mun
    locais_com_votos = locais_mun.merge(votos_secoes, on=['zona', 'secao'], how='left')
    locais_com_votos['votos'] = locais_com_votos['votos'].fillna(0).astype(int)
    locais_com_votos['total_validos'] = locais_com_votos['total_validos'].fillna(0).astype(int)
    
    # Agregar por Colégio Eleitoral (id_local)
    locais_agg = locais_com_votos.groupby(['id_local', 'zona', 'codigo_local', 'nome_local', 'bairro', 'endereco', 'cep', 'latitude', 'longitude']).agg(
        qtd_secoes=('secao', 'count'),
        secoes_lista=('secao', lambda x: ', '.join(map(str, sorted(x)))),
        aptos=('aptos', 'sum'),
        votos=('votos', 'sum'),
        total_validos=('total_validos', 'sum')
    ).reset_index()
    
    locais_agg['pct_votos'] = (100.0 * locais_agg['votos'] / locais_agg['total_validos'].replace(0, 1)).round(2)
    
    df_loc_view = locais_agg.copy()
    if busca_local.strip():
        q_l = normalize_text(busca_local)
        q_digits = "".join(filter(str.isdigit, q_l))
        
        def match_colegio(row):
            # 1. Match por texto (nome da escola, bairro, endereço)
            if (q_l in normalize_text(row['nome_local'])) or (q_l in normalize_text(row['bairro'])) or (q_l in normalize_text(row['endereco'])):
                return True
            # 2. Match por seção exata (ex: se o usuário digitou "125" ou "seção 125")
            if q_digits:
                secoes = [s.strip() for s in str(row['secoes_lista']).split(',')]
                if q_digits in secoes:
                    return True
                # Match por zona
                if str(row['zona']) == q_digits:
                    return True
                # Match por código do local
                if str(row['codigo_local']) == q_digits:
                    return True
            return False
            
        df_loc_view = df_loc_view[df_loc_view.apply(match_colegio, axis=1)].reset_index(drop=True)
        
        if len(df_loc_view) == 1:
            loc_s = df_loc_view.iloc[0]
            secao_aviso = f" (contém a Seção #{q_digits})" if q_digits and q_digits in [s.strip() for s in str(loc_s['secoes_lista']).split(',')] else ""
            st.success(
                f"🎯 **{loc_s['nome_local']}**{secao_aviso} — "
                f"Zona {loc_s['zona']} | Bairro: {loc_s['bairro']} | "
                f"**{fmt_int(loc_s['votos'])} votos** ({fmt_pct(loc_s['pct_votos'])}) de {alvo_nome} | "
                f"Seções ({loc_s['qtd_secoes']}): {loc_s['secoes_lista']}"
            )
        elif len(df_loc_view) == 0:
            outros_locais = df_locais[df_locais.apply(lambda r: (q_l in normalize_text(r['nome_local'])) or (q_digits and str(r['secao']) == q_digits), axis=1)]
            if len(outros_locais) > 0:
                muns_achados = ", ".join(outros_locais['municipio'].str.title().unique().tolist()[:3])
                st.info(f"💡 Não encontrado em **{mun_nome_sel}**, mas foi localizado em: **{muns_achados}**! Selecione esse município para visualizá-lo.")
            else:
                st.warning(f"Nenhum colégio eleitoral ou seção encontrada para '{busca_local}' em {mun_nome_sel}.")
    
    if criterio_analise == "Total de Votos (Nominais)":
        df_loc_view = df_loc_view.sort_values('votos', ascending=False).reset_index(drop=True)
    else:
        df_loc_view = df_loc_view.sort_values('pct_votos', ascending=False).reset_index(drop=True)
    
    # KPIs rápidos
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Colégios Exibidos", f"{len(df_loc_view)}")
    col2.metric("Total de Seções", fmt_int(df_loc_view['qtd_secoes'].sum()))
    col3.metric("Eleitores Aptos", fmt_int(df_loc_view['aptos'].sum()))
    col4.metric(f"Votos de {alvo_nome}", fmt_int(df_loc_view['votos'].sum()))
    
    st.divider()
    
    # Mapa Folium com pontos
    loc_geo = df_loc_view.dropna(subset=['latitude', 'longitude']).copy()
    loc_geo = loc_geo[(loc_geo['latitude'] != 0) & (loc_geo['longitude'] != 0)]
    
    if len(loc_geo) > 0:
        center_lat = loc_geo['latitude'].mean()
        center_lon = loc_geo['longitude'].mean()
        zoom = 12
        if busca_local.strip() and len(df_loc_view) == 1:
            center_lat = loc_geo.iloc[0]['latitude']
            center_lon = loc_geo.iloc[0]['longitude']
            zoom = 16
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")
        
        max_votos = max(1, loc_geo['votos'].max())
        max_pct = max(1.0, loc_geo['pct_votos'].max())
        
        for _, row in loc_geo.iterrows():
            pct = row['pct_votos']
            votos_loc = row['votos']
            tot_loc = row['total_validos']
            aptos_loc = row['aptos']
            
            if criterio_analise == "Total de Votos (Nominais)":
                ratio = votos_loc / max_votos
                radius = min(max(5, ratio * 20), 22)
                opacity = min(0.95, max(0.40, ratio))
                tooltip_txt = f"{row['nome_local']} ({fmt_int(votos_loc)} votos)"
            else:
                ratio = pct / max_pct
                radius = min(max(5, (pct / 100.0) * 20), 20)
                opacity = min(0.95, max(0.40, pct / 70.0))
                tooltip_txt = f"{row['nome_local']} ({fmt_pct(pct)} dos válidos)"
                
            popup_html = f"""
            <div style="font-family: sans-serif; font-size: 12px; width: 250px;">
                <b style="color: #2C3E50;">{row['nome_local']}</b><br>
                <b>Bairro:</b> {row['bairro']}<br>
                <b>Zona:</b> {row['zona']} | <b>Código:</b> {row['codigo_local']}<br>
                <b>Endereço:</b> {row['endereco']}<br>
                <hr style="margin: 5px 0;">
                <b>Eleitores Aptos:</b> {fmt_int(aptos_loc)}<br>
                <b>Votos de {alvo_nome}:</b> {fmt_int(votos_loc)} ({fmt_pct(pct)})<br>
                <b>Total Válidos:</b> {fmt_int(tot_loc)}<br>
                <b>Seções ({row['qtd_secoes']}):</b> {row['secoes_lista']}<br>
            </div>
            """
            
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=radius,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=tooltip_txt,
                color="#2C3E50",
                fill=True,
                fill_color=hex_cor,
                fill_opacity=opacity,
                weight=1.2
            ).add_to(m)
            
        st_folium(m, height=450, width="100%")
    else:
        st.info("Nenhum colégio eleitoral com coordenadas válidas para exibir no mapa deste município.")
        
    st.markdown(f"**Tabela dos Colégios Eleitorais de {mun_nome_sel}**")
    df_table_loc = df_loc_view.copy()
    df_table_loc['Aptos'] = df_table_loc['aptos'].apply(fmt_int)
    df_table_loc['Votos Obtidos'] = df_table_loc['votos'].apply(fmt_int)
    df_table_loc['Total Válidos'] = df_table_loc['total_validos'].apply(fmt_int)
    df_table_loc['% Válidos'] = df_table_loc['pct_votos'].apply(fmt_pct)
    
    st.dataframe(
        df_table_loc[['nome_local', 'bairro', 'zona', 'qtd_secoes', 'Aptos', 'Votos Obtidos', 'Total Válidos', '% Válidos']].rename(columns={
            'nome_local': 'Nome do Colégio',
            'bairro': 'Bairro / Localidade',
            'zona': 'Zona',
            'qtd_secoes': 'Seções'
        }),
        use_container_width=True,
        hide_index=True
    )
