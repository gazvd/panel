import streamlit as st
import pandas as pd
import plotly.express as px
from config import CORES_PARTIDOS, COR_PADRAO, fmt_int, fmt_pct, get_cores_foco, get_contrast_color, normalize_text
from modules.data_loader import (
    get_eleitos_prefeitos,
    get_eleitos_vereadores,
    get_eleitos_parlamentares
)

def get_cor_partido(sigla: str) -> str:
    """Retorna a cor oficial do partido a partir da sigla."""
    if not sigla:
        return COR_PADRAO
    s_clean = sigla.strip().upper()
    if s_clean in CORES_PARTIDOS:
        return CORES_PARTIDOS[s_clean]
    if "PSD" in s_clean:
        return "#9B59B6"
    cor, _, _ = get_cores_foco(sigla_partido=s_clean)
    return cor

def _render_painel_prefeitos(ano: int, df_mun_map: pd.DataFrame, regiao_selecionada: str = None, tab_origem: str = "mun"):
    """Renderiza o quadro de prefeitos eleitos por partido."""
    df_pref = get_eleitos_prefeitos(ano)
    if len(df_pref) == 0:
        st.info(f"Nenhum dado de prefeitos eleitos disponível para o ano {ano}.")
        return

    df_map_clean = df_mun_map[['CD_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO']].copy()
    df_map_clean['CD_MUN'] = df_map_clean['CD_MUN'].astype(int)
    df_merged = df_pref.merge(df_map_clean, left_on='id_municipio', right_on='CD_MUN', how='left')

    is_filtrado_reg = regiao_selecionada and regiao_selecionada != "TODAS"
    if is_filtrado_reg:
        df_view = df_merged[df_merged['REGIAO_DESENVOLVIMENTO'].str.upper() == regiao_selecionada.upper()].copy()
        subtitulo_reg = f"na Região {regiao_selecionada}"
    else:
        df_view = df_merged.copy()
        subtitulo_reg = "em Pernambuco"

    total_pref = len(df_view)
    if total_pref == 0:
        st.info(f"Nenhuma prefeitura encontrada para a seleção informada em {ano}.")
        return

    bancada = df_view['sigla_partido'].value_counts().reset_index()
    bancada.columns = ['sigla_partido', 'total_prefeitos']
    bancada['pct'] = (100.0 * bancada['total_prefeitos'] / total_pref).round(1)

    st.markdown(f"### 🏛️ Prefeituras Conquistadas por Partido — Eleições {ano} ({subtitulo_reg})")
    st.caption(f"Distribuição partidária dos **{total_pref} prefeitos eleitos** {subtitulo_reg}.")

    badges = []
    for _, r in bancada.iterrows():
        p_sigla = r['sigla_partido']
        p_cnt = r['total_prefeitos']
        p_pct = r['pct']
        bg_c = get_cor_partido(p_sigla)
        fg_c = get_contrast_color(bg_c)
        badges.append(
            f"<span style='background-color: {bg_c}; color: {fg_c}; padding: 4px 10px; border-radius: 12px; margin-right: 8px; font-weight: bold; font-size: 0.9rem;'>"
            f"{p_sigla}: {p_cnt} ({p_pct}%)"
            f"</span>"
        )
    st.markdown(f"**Bancada de Prefeituras:** {' '.join(badges)}", unsafe_allow_html=True)
    st.write("")

    col_g, col_t = st.columns([1.2, 0.8])
    with col_g:
        cor_map = {row['sigla_partido']: get_cor_partido(row['sigla_partido']) for _, row in bancada.iterrows()}
        fig = px.bar(
            bancada.sort_values('total_prefeitos', ascending=True),
            x='total_prefeitos',
            y='sigla_partido',
            orientation='h',
            color='sigla_partido',
            color_discrete_map=cor_map,
            text='total_prefeitos',
            labels={'total_prefeitos': 'Prefeituras Eleitas', 'sigla_partido': 'Partido'}
        )
        fig.update_layout(height=380, margin=dict(l=0, r=10, t=10, b=0), showlegend=False)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    with col_t:
        st.markdown(f"**Ranking de Prefeituras ({ano})**")
        df_rank_display = bancada.rename(columns={
            'sigla_partido': 'Partido',
            'total_prefeitos': 'Prefeituras',
            'pct': '% do Total'
        })
        df_rank_display['% do Total'] = df_rank_display['% do Total'].apply(fmt_pct)
        st.dataframe(df_rank_display, use_container_width=True, hide_index=True)

    with st.expander(f"📋 Ver Lista Completa dos {total_pref} Prefeitos Eleitos ({ano})", expanded=False):
        busca_p = st.text_input("🔍 Filtrar prefeito ou município:", placeholder="Ex: Recife, Caruaru, João...", key=f"busca_pref_{ano}_{tab_origem}")
        df_show = df_view[['NM_MUN', 'REGIAO_DESENVOLVIMENTO', 'nome_urna', 'sigla_partido', 'total_votos', 'turno']].copy()
        if busca_p.strip():
            q_p = normalize_text(busca_p)
            df_show = df_show[
                df_show['NM_MUN'].apply(lambda x: q_p in normalize_text(x)) |
                df_show['nome_urna'].apply(lambda x: q_p in normalize_text(x)) |
                df_show['sigla_partido'].apply(lambda x: q_p in normalize_text(x))
            ]
        df_show['Votos'] = df_show['total_votos'].apply(fmt_int)
        df_show['Turno'] = df_show['turno'].apply(lambda t: f"{t}º Turno")
        df_show = df_show.rename(columns={
            'NM_MUN': 'Município',
            'REGIAO_DESENVOLVIMENTO': 'Região',
            'nome_urna': 'Prefeito(a) Eleito(a)',
            'sigla_partido': 'Partido'
        }).sort_values('Município')
        st.dataframe(df_show[['Município', 'Região', 'Prefeito(a) Eleito(a)', 'Partido', 'Votos', 'Turno']], use_container_width=True, hide_index=True)

def _render_painel_vereadores(ano: int, df_mun_map: pd.DataFrame, cd_mun_selecionado: str = None, nm_mun_selecionado: str = None, regiao_selecionada: str = None, tab_origem: str = "mun"):
    """Renderiza a composição de Câmaras Municipais e o total estadual de vereadores."""
    df_muns_list = df_mun_map[['CD_MUN', 'NM_MUN']].dropna().drop_duplicates().sort_values('NM_MUN')
    muns_dict = dict(zip(df_muns_list['NM_MUN'], df_muns_list['CD_MUN']))
    opcoes_camara = ["TODOS (Visão Estadual de Vereadores)"] + list(muns_dict.keys())

    # Determinar município inicial
    idx_default = 0
    if nm_mun_selecionado and nm_mun_selecionado in opcoes_camara:
        idx_default = opcoes_camara.index(nm_mun_selecionado)
    elif cd_mun_selecionado:
        for nm, cd in muns_dict.items():
            if str(cd) == str(cd_mun_selecionado):
                if nm in opcoes_camara:
                    idx_default = opcoes_camara.index(nm)
                break

    c_sel1, _ = st.columns([1.6, 2.4])
    with c_sel1:
        escolha_camara = st.selectbox(
            "🏛️ Selecione a Câmara Municipal ou Visão Geral:",
            opcoes_camara,
            index=idx_default,
            key=f"sel_camara_{ano}_{tab_origem}"
        )

    # Caso A: Câmara Municipal de uma cidade específica
    if escolha_camara != "TODOS (Visão Estadual de Vereadores)":
        cd_sel = muns_dict[escolha_camara]
        mun_nome_display = escolha_camara
        df_ver_mun = get_eleitos_vereadores(ano, id_municipio=int(cd_sel))

        if len(df_ver_mun) == 0:
            st.info(f"Nenhum vereador eleito registrado para {mun_nome_display} em {ano}.")
            return

        total_cadeiras = len(df_ver_mun)
        bancada_mun = df_ver_mun['sigla_partido'].value_counts().reset_index()
        bancada_mun.columns = ['sigla_partido', 'total_vereadores']
        bancada_mun['pct'] = (100.0 * bancada_mun['total_vereadores'] / total_cadeiras).round(1)

        st.markdown(f"### 🏛️ Composição da Câmara Municipal de {mun_nome_display} — Eleições {ano}")
        st.caption(f"Bancada eleita oficial: **{total_cadeiras} cadeiras** na Câmara Municipal.")

        badges = []
        for _, r in bancada_mun.iterrows():
            p_sigla = r['sigla_partido']
            p_cnt = r['total_vereadores']
            p_pct = r['pct']
            bg_c = get_cor_partido(p_sigla)
            fg_c = get_contrast_color(bg_c)
            badges.append(
                f"<span style='background-color: {bg_c}; color: {fg_c}; padding: 4px 10px; border-radius: 12px; margin-right: 8px; font-weight: bold; font-size: 0.9rem;'>"
                f"{p_sigla}: {p_cnt} {'cadeira' if p_cnt == 1 else 'cadeiras'} ({p_pct}%)"
                f"</span>"
            )
        st.markdown(f"**Bancadas Eleitas:** {' '.join(badges)}", unsafe_allow_html=True)
        st.write("")

        col_g, col_t = st.columns([1.1, 0.9])
        with col_g:
            cor_map = {row['sigla_partido']: get_cor_partido(row['sigla_partido']) for _, row in bancada_mun.iterrows()}
            fig = px.bar(
                bancada_mun.sort_values('total_vereadores', ascending=True),
                x='total_vereadores',
                y='sigla_partido',
                orientation='h',
                color='sigla_partido',
                color_discrete_map=cor_map,
                text='total_vereadores',
                labels={'total_vereadores': 'Cadeiras', 'sigla_partido': 'Partido'}
            )
            fig.update_layout(height=360, margin=dict(l=0, r=10, t=10, b=0), showlegend=False)
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with col_t:
            st.markdown(f"**Lista de Vereadores Eleitos: {mun_nome_display}**")
            df_ver_mun_disp = df_ver_mun[['nome_urna', 'sigla_partido', 'total_votos']].copy()
            df_ver_mun_disp['Votos'] = df_ver_mun_disp['total_votos'].apply(fmt_int)
            df_ver_mun_disp = df_ver_mun_disp.rename(columns={
                'nome_urna': 'Vereador(a) Eleito(a)',
                'sigla_partido': 'Partido'
            })
            st.dataframe(df_ver_mun_disp[['Vereador(a) Eleito(a)', 'Partido', 'Votos']], use_container_width=True, hide_index=True)

    # Caso B: Visão Estadual / Regional de Vereadores
    else:
        df_ver_pe = get_eleitos_vereadores(ano)
        if len(df_ver_pe) == 0:
            st.info(f"Nenhum dado de vereadores eleitos disponível para o ano {ano}.")
            return

        df_map_clean = df_mun_map[['CD_MUN', 'NM_MUN', 'REGIAO_DESENVOLVIMENTO']].copy()
        df_map_clean['CD_MUN'] = df_map_clean['CD_MUN'].astype(int)
        df_merged = df_ver_pe.merge(df_map_clean, left_on='id_municipio', right_on='CD_MUN', how='left')

        is_filtrado_reg = regiao_selecionada and regiao_selecionada != "TODAS"
        if is_filtrado_reg:
            df_view = df_merged[df_merged['REGIAO_DESENVOLVIMENTO'].str.upper() == regiao_selecionada.upper()].copy()
            subtitulo = f"na Região {regiao_selecionada}"
        else:
            df_view = df_merged.copy()
            subtitulo = "em todo o Estado de Pernambuco"

        total_ver = len(df_view)
        bancada_tot = df_view['sigla_partido'].value_counts().reset_index()
        bancada_tot.columns = ['sigla_partido', 'total_vereadores']
        bancada_tot['pct'] = (100.0 * bancada_tot['total_vereadores'] / total_ver).round(1)

        st.markdown(f"### 🗳️ Total de Vereadores Eleitos por Partido — Eleições {ano} ({subtitulo})")
        st.caption(f"Total de **{fmt_int(total_ver)} vereadores eleitos** {subtitulo}.")

        badges = []
        for _, r in bancada_tot.head(10).iterrows():
            p_sigla = r['sigla_partido']
            p_cnt = r['total_vereadores']
            p_pct = r['pct']
            bg_c = get_cor_partido(p_sigla)
            fg_c = get_contrast_color(bg_c)
            badges.append(
                f"<span style='background-color: {bg_c}; color: {fg_c}; padding: 4px 10px; border-radius: 12px; margin-right: 8px; font-weight: bold; font-size: 0.9rem;'>"
                f"{p_sigla}: {fmt_int(p_cnt)} ({p_pct}%)"
                f"</span>"
            )
        st.markdown(f"**Top Bancadas de Vereadores:** {' '.join(badges)}", unsafe_allow_html=True)
        st.write("")

        col_g, col_t = st.columns([1.2, 0.8])
        with col_g:
            top_partidos = bancada_tot.head(15).sort_values('total_vereadores', ascending=True)
            cor_map = {row['sigla_partido']: get_cor_partido(row['sigla_partido']) for _, row in top_partidos.iterrows()}
            fig = px.bar(
                top_partidos,
                x='total_vereadores',
                y='sigla_partido',
                orientation='h',
                color='sigla_partido',
                color_discrete_map=cor_map,
                text='total_vereadores',
                labels={'total_vereadores': 'Vereadores Eleitos', 'sigla_partido': 'Partido'}
            )
            fig.update_layout(height=420, margin=dict(l=0, r=10, t=10, b=0), showlegend=False)
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        with col_t:
            st.markdown(f"**Bancada Total de Vereadores ({ano})**")
            df_table = bancada_tot.rename(columns={
                'sigla_partido': 'Partido',
                'total_vereadores': 'Vereadores Eleitos',
                'pct': '% das Cadeiras'
            })
            df_table['Vereadores Eleitos'] = df_table['Vereadores Eleitos'].apply(fmt_int)
            df_table['% das Cadeiras'] = df_table['% das Cadeiras'].apply(fmt_pct)
            st.dataframe(df_table, use_container_width=True, hide_index=True)

def _render_painel_alepe(ano: int):
    """Renderiza a bancada oficial da ALEPE (49 deputados estaduais)."""
    df_est = get_eleitos_parlamentares(ano, 'deputado estadual')
    if len(df_est) == 0:
        st.info(f"Nenhum deputado estadual eleito disponível para o ano {ano}.")
        return

    total_alepe = len(df_est)
    bancada_alepe = df_est['sigla_partido'].value_counts().reset_index()
    bancada_alepe.columns = ['sigla_partido', 'total_deputados']
    bancada_alepe['pct'] = (100.0 * bancada_alepe['total_deputados'] / total_alepe).round(1)

    st.markdown(f"### 🏛️ Composição Oficial da ALEPE — Eleições {ano} ({total_alepe} Cadeiras)")
    st.caption(f"Distribuição partidária das **{total_alepe} cadeiras** da Assembleia Legislativa de Pernambuco.")

    badges = []
    for _, r in bancada_alepe.iterrows():
        p_sigla = r['sigla_partido']
        p_cnt = r['total_deputados']
        p_pct = r['pct']
        bg_c = get_cor_partido(p_sigla)
        fg_c = get_contrast_color(bg_c)
        badges.append(
            f"<span style='background-color: {bg_c}; color: {fg_c}; padding: 4px 10px; border-radius: 12px; margin-right: 8px; font-weight: bold; font-size: 0.9rem;'>"
            f"{p_sigla}: {p_cnt} ({p_pct}%)"
            f"</span>"
        )
    st.markdown(f"**Bancadas da ALEPE:** {' '.join(badges)}", unsafe_allow_html=True)
    st.write("")

    col_g, col_t = st.columns([1.1, 0.9])
    with col_g:
        cor_map = {row['sigla_partido']: get_cor_partido(row['sigla_partido']) for _, row in bancada_alepe.iterrows()}
        fig = px.bar(
            bancada_alepe.sort_values('total_deputados', ascending=True),
            x='total_deputados',
            y='sigla_partido',
            orientation='h',
            color='sigla_partido',
            color_discrete_map=cor_map,
            text='total_deputados',
            labels={'total_deputados': 'Deputados Eleitos', 'sigla_partido': 'Partido'}
        )
        fig.update_layout(height=380, margin=dict(l=0, r=10, t=10, b=0), showlegend=False)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    with col_t:
        st.markdown("**Quadro de Bancadas na ALEPE**")
        df_alepe_disp = bancada_alepe.rename(columns={
            'sigla_partido': 'Partido',
            'total_deputados': 'Cadeiras',
            'pct': '% da Casa'
        })
        df_alepe_disp['% da Casa'] = df_alepe_disp['% da Casa'].apply(fmt_pct)
        st.dataframe(df_alepe_disp, use_container_width=True, hide_index=True)

    with st.expander("📋 Ver Lista Nominal dos 49 Deputados Estaduais Eleitos", expanded=False):
        df_nom = df_est.copy()
        df_nom['Votação Total em PE'] = df_nom['total_votos'].apply(fmt_int)
        df_nom = df_nom.rename(columns={
            'nome_urna': 'Deputado(a) Eleito(a)',
            'sigla_partido': 'Partido',
            'numero_candidato': 'Número'
        })
        st.dataframe(df_nom[['Deputado(a) Eleito(a)', 'Partido', 'Número', 'Votação Total em PE']], use_container_width=True, hide_index=True)

def _render_painel_federal(ano: int):
    """Renderiza a bancada federal de PE (25 deputados federais)."""
    df_fed = get_eleitos_parlamentares(ano, 'deputado federal')
    if len(df_fed) == 0:
        st.info(f"Nenhum deputado federal eleito disponível para o ano {ano}.")
        return

    total_fed = len(df_fed)
    bancada_fed = df_fed['sigla_partido'].value_counts().reset_index()
    bancada_fed.columns = ['sigla_partido', 'total_deputados']
    bancada_fed['pct'] = (100.0 * bancada_fed['total_deputados'] / total_fed).round(1)

    st.markdown(f"### 🏛️ Bancada Federal de Pernambuco na Câmara dos Deputados — Eleições {ano} ({total_fed} Cadeiras)")
    st.caption(f"Distribuição partidária das **{total_fed} cadeiras** de Pernambuco no Congresso Nacional.")

    badges = []
    for _, r in bancada_fed.iterrows():
        p_sigla = r['sigla_partido']
        p_cnt = r['total_deputados']
        p_pct = r['pct']
        bg_c = get_cor_partido(p_sigla)
        fg_c = get_contrast_color(bg_c)
        badges.append(
            f"<span style='background-color: {bg_c}; color: {fg_c}; padding: 4px 10px; border-radius: 12px; margin-right: 8px; font-weight: bold; font-size: 0.9rem;'>"
            f"{p_sigla}: {p_cnt} ({p_pct}%)"
            f"</span>"
        )
    st.markdown(f"**Bancada Federal:** {' '.join(badges)}", unsafe_allow_html=True)
    st.write("")

    col_g, col_t = st.columns([1.1, 0.9])
    with col_g:
        cor_map = {row['sigla_partido']: get_cor_partido(row['sigla_partido']) for _, row in bancada_fed.iterrows()}
        fig = px.bar(
            bancada_fed.sort_values('total_deputados', ascending=True),
            x='total_deputados',
            y='sigla_partido',
            orientation='h',
            color='sigla_partido',
            color_discrete_map=cor_map,
            text='total_deputados',
            labels={'total_deputados': 'Deputados Eleitos', 'sigla_partido': 'Partido'}
        )
        fig.update_layout(height=380, margin=dict(l=0, r=10, t=10, b=0), showlegend=False)
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    with col_t:
        st.markdown("**Quadro da Bancada Federal de PE**")
        df_fed_disp = bancada_fed.rename(columns={
            'sigla_partido': 'Partido',
            'total_deputados': 'Cadeiras',
            'pct': '% da Bancada'
        })
        df_fed_disp['% da Bancada'] = df_fed_disp['% da Bancada'].apply(fmt_pct)
        st.dataframe(df_fed_disp, use_container_width=True, hide_index=True)

    with st.expander("📋 Ver Lista Nominal dos 25 Deputados Federais Eleitos", expanded=False):
        df_nom_f = df_fed.copy()
        df_nom_f['Votação Total em PE'] = df_nom_f['total_votos'].apply(fmt_int)
        df_nom_f = df_nom_f.rename(columns={
            'nome_urna': 'Deputado(a) Federal Eleito(a)',
            'sigla_partido': 'Partido',
            'numero_candidato': 'Número'
        })
        st.dataframe(df_nom_f[['Deputado(a) Federal Eleito(a)', 'Partido', 'Número', 'Votação Total em PE']], use_container_width=True, hide_index=True)

def render_painel_eleitos(
    ano: int,
    cargo: str,
    df_mun_map: pd.DataFrame,
    cd_mun_selecionado: str = None,
    nm_mun_selecionado: str = None,
    regiao_selecionada: str = None,
    tab_origem: str = "mun"
):
    """
    Renderiza o quadro analítico completo de mandatos eleitos por partido:
    - Prefeito: Prefeituras conquistadas no estado ou na macrorregião (com expander de vereadores).
    - Vereador: Composição da Câmara Municipal selecionada ou visão estadual (com expander de prefeitos).
    - Deputado Estadual: Bancada oficial da ALEPE (49 deputados).
    - Deputado Federal: Bancada oficial de PE na Câmara Federal (25 deputados).
    - Governador/Senador/Presidente: Bancadas eleitas da ALEPE e Câmara Federal do mesmo pleito.
    """
    st.markdown("---")

    # 1. CARGO: PREFEITO
    if cargo == "prefeito":
        _render_painel_prefeitos(ano, df_mun_map, regiao_selecionada, tab_origem)
        with st.expander(f"🗳️ Ver Composição das Câmaras de Vereadores ({ano})", expanded=False):
            _render_painel_vereadores(ano, df_mun_map, cd_mun_selecionado, nm_mun_selecionado, regiao_selecionada, f"{tab_origem}_exp_ver")

    # 2. CARGO: VEREADOR
    elif cargo == "vereador":
        _render_painel_vereadores(ano, df_mun_map, cd_mun_selecionado, nm_mun_selecionado, regiao_selecionada, tab_origem)
        with st.expander(f"🏛️ Ver Prefeituras Conquistadas por Partido ({ano})", expanded=False):
            _render_painel_prefeitos(ano, df_mun_map, regiao_selecionada, f"{tab_origem}_exp_pref")

    # 3. CARGO: DEPUTADO ESTADUAL
    elif cargo == "deputado estadual":
        _render_painel_alepe(ano)

    # 4. CARGO: DEPUTADO FEDERAL
    elif cargo == "deputado federal":
        _render_painel_federal(ano)

    # 5. ELEIÇÕES GERAIS (GOVERNADOR, SENADOR, PRESIDENTE)
    elif cargo in ["governador", "senador", "presidente"]:
        st.markdown(f"### 🏛️ Força Parlamentar Eleita em PE — Eleições {ano}")
        st.caption("Distribuição partidária das bancadas eleitas no pleito estadual (ALEPE e Câmara Federal).")
        tab_alepe, tab_fed = st.tabs(["🏛️ ALEPE (49 Deputados Estaduais)", "🇧🇷 Bancada Federal de PE (25 Deputados)"])
        with tab_alepe:
            _render_painel_alepe(ano)
        with tab_fed:
            _render_painel_federal(ano)
