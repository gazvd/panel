import geopandas as gpd
import streamlit as st
from config import (
    PATH_GEO_REGIOES,
    PATH_GEO_MUNICIPIOS,
    PATH_GEO_ZONAS,
    PATH_GEO_DISTRITOS,
    PATH_GEO_MOSAICO
)

@st.cache_data(ttl=3600)
def load_regioes_gdf():
    """Carrega as 12 Regiões de Desenvolvimento de PE."""
    return gpd.read_file(PATH_GEO_REGIOES)

@st.cache_data(ttl=3600)
def load_municipios_gdf():
    """Carrega os 185 Municípios de PE."""
    return gpd.read_file(PATH_GEO_MUNICIPIOS)

@st.cache_data(ttl=3600)
def load_zonas_gdf(cd_mun: str = None, regiao: str = None):
    """Carrega as 209 Zonas-Município de PE com suporte a filtro opcional."""
    gdf = gpd.read_parquet(PATH_GEO_ZONAS)

    # Isolar a Zona 4 do Recife para conter apenas a sede municipal no continente (descartando os polígonos de Noronha em latitude > -7.5)
    # Isso evita distorção de enquadramento/zoom no mapa do Recife, mantendo a geometria focada na malha urbana
    if 'Recife_Z4' in gdf['ID_ZONA_MUN'].values:
        idx_z4 = gdf[gdf['ID_ZONA_MUN'] == 'Recife_Z4'].index
        if len(idx_z4) > 0:
            geom = gdf.loc[idx_z4[0], 'geometry']
            if geom.geom_type == 'MultiPolygon':
                from shapely.geometry import MultiPolygon
                parts = [p for p in geom.geoms if p.bounds[1] < -7.5]
                if len(parts) > 0:
                    gdf.loc[idx_z4[0], 'geometry'] = MultiPolygon(parts) if len(parts) > 1 else parts[0]

    if cd_mun:
        gdf = gdf[gdf['CD_MUN'].astype(str) == str(cd_mun)]
    elif regiao and regiao != "TODAS":
        gdf = gdf[gdf['REGIAO_DESENVOLVIMENTO'].str.upper() == regiao.upper()]
    return gdf

@st.cache_data(ttl=3600)
def load_distritos_gdf(cd_mun: str = None):
    """Carrega os distritos municipais (opcionalmente filtrado por município)."""
    gdf = gpd.read_parquet(PATH_GEO_DISTRITOS)
    if cd_mun:
        gdf = gdf[gdf['CD_MUN'].astype(str) == str(cd_mun)]
    return gdf

@st.cache_data(ttl=3600)
def load_mosaico_bairros_gdf(cd_mun: str = None, regiao: str = None):
    """
    Carrega o mosaico territorial de menor agregação (Bairros e Distritos).
    Filtragem sob demanda é fundamental para performance máxima no Folium.
    """
    gdf = gpd.read_parquet(PATH_GEO_MOSAICO)
    if cd_mun:
        gdf = gdf[gdf['CD_MUN'].astype(str) == str(cd_mun)]
    elif regiao and regiao != "TODAS":
        gdf = gdf[gdf['REGIAO_DESENVOLVIMENTO'].str.upper() == regiao.upper()]
    return gdf
