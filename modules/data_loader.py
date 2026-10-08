import duckdb
import pandas as pd
import streamlit as st
from config import PATH_RESULTADOS, PATH_LOCAIS_PARQUET, PRESIDENTES_NOMES

def get_connection():
    return duckdb.connect()

@st.cache_data(ttl=3600)
def get_metadata_filtros():
    """Retorna os anos disponíveis, e para cada ano os cargos e turnos."""
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    df = con.execute(f"""
        SELECT DISTINCT ano, turno, cargo
        FROM '{res_path}'
        ORDER BY ano DESC, turno ASC, cargo ASC
    """).df()
    return df

@st.cache_data(ttl=3600)
def get_ranking_candidatos(ano: int, turno: int, cargo: str, id_municipio: int = None, zona: int = None, limit: int = 50):
    """Retorna ranking de candidatos mais votados no filtro selecionado."""
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    
    where_clauses = [f"ano = {ano}", f"turno = {turno}", f"cargo = '{cargo}'"]
    if id_municipio:
        where_clauses.append(f"id_municipio = {id_municipio}")
    if zona:
        where_clauses.append(f"zona = {zona}")
        
    where_str = " AND ".join(where_clauses)
    
    if cargo == "presidente":
        query = f"""
            SELECT 
                NULL as numero_candidato,
                sigla_partido,
                NULL as resultado,
                SUM(total_votos) as total_votos
            FROM '{res_path}'
            WHERE {where_str} AND sigla_partido IS NOT NULL
            GROUP BY sigla_partido
            ORDER BY total_votos DESC
            LIMIT {limit}
        """
        df = con.execute(query).df()
        df['nome_urna'] = df['sigla_partido'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})"))
        return df
    
    query = f"""
        SELECT 
            numero_candidato,
            nome_urna,
            sigla_partido,
            resultado,
            SUM(total_votos) as total_votos
        FROM '{res_path}'
        WHERE {where_str}
        GROUP BY numero_candidato, nome_urna, sigla_partido, resultado
        ORDER BY total_votos DESC
        LIMIT {limit}
    """
    return con.execute(query).df()

@st.cache_data(ttl=3600)
def get_ranking_partidos(ano: int, turno: int, cargo: str, id_municipio: int = None, zona: int = None):
    """Retorna ranking de partidos no filtro selecionado."""
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    
    where_clauses = [f"ano = {ano}", f"turno = {turno}", f"cargo = '{cargo}'"]
    if id_municipio:
        where_clauses.append(f"id_municipio = {id_municipio}")
    if zona:
        where_clauses.append(f"zona = {zona}")
        
    where_str = " AND ".join(where_clauses)
    
    query = f"""
        SELECT 
            sigla_partido,
            SUM(total_votos) as total_votos
        FROM '{res_path}'
        WHERE {where_str}
        GROUP BY sigla_partido
        ORDER BY total_votos DESC
    """
    return con.execute(query).df()

@st.cache_data(ttl=3600)
def get_votos_municipios(ano: int, turno: int, cargo: str, partido: str = None, numero_candidato: int = None):
    """Retorna total de votos por id_municipio e percentual sobre o total de válidos no município."""
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    
    where_clauses = [f"ano = {ano}", f"turno = {turno}", f"cargo = '{cargo}'"]
    
    # 1. Total válidos por município
    query_total = f"""
        SELECT id_municipio, SUM(total_votos) as total_validos_mun
        FROM '{res_path}'
        WHERE {' AND '.join(where_clauses)}
        GROUP BY id_municipio
    """
    
    # 2. Votos do filtro (partido ou candidato)
    where_item = list(where_clauses)
    if numero_candidato:
        where_item.append(f"numero_candidato = {numero_candidato}")
    elif partido:
        where_item.append(f"sigla_partido = '{partido}'")
        
    query_item = f"""
        SELECT id_municipio, SUM(total_votos) as votos_filtro
        FROM '{res_path}'
        WHERE {' AND '.join(where_item)}
        GROUP BY id_municipio
    """
    
    query_join = f"""
        WITH t_tot AS ({query_total}),
             t_item AS ({query_item})
        SELECT 
            t_tot.id_municipio,
            COALESCE(t_item.votos_filtro, 0) as votos,
            t_tot.total_validos_mun as total_validos,
            ROUND(100.0 * COALESCE(t_item.votos_filtro, 0) / NULLIF(t_tot.total_validos_mun, 0), 2) as pct_votos
        FROM t_tot
        LEFT JOIN t_item ON t_tot.id_municipio = t_item.id_municipio
    """
    return con.execute(query_join).df()

@st.cache_data(ttl=3600)
def get_votos_zonas(ano: int, turno: int, cargo: str, partido: str = None, numero_candidato: int = None, id_municipio: int = None):
    """Retorna total de votos por zona (e id_municipio)."""
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    
    where_clauses = [f"ano = {ano}", f"turno = {turno}", f"cargo = '{cargo}'"]
    if id_municipio:
        where_clauses.append(f"id_municipio = {id_municipio}")
        
    query_total = f"""
        SELECT id_municipio, zona, SUM(total_votos) as total_validos_zona
        FROM '{res_path}'
        WHERE {' AND '.join(where_clauses)}
        GROUP BY id_municipio, zona
    """
    
    where_item = list(where_clauses)
    if numero_candidato:
        where_item.append(f"numero_candidato = {numero_candidato}")
    elif partido:
        where_item.append(f"sigla_partido = '{partido}'")
        
    query_item = f"""
        SELECT id_municipio, zona, SUM(total_votos) as votos_filtro
        FROM '{res_path}'
        WHERE {' AND '.join(where_item)}
        GROUP BY id_municipio, zona
    """
    
    query_join = f"""
        WITH t_tot AS ({query_total}),
             t_item AS ({query_item})
        SELECT 
            t_tot.id_municipio,
            t_tot.zona,
            COALESCE(t_item.votos_filtro, 0) as votos,
            t_tot.total_validos_zona as total_validos,
            ROUND(100.0 * COALESCE(t_item.votos_filtro, 0) / NULLIF(t_tot.total_validos_zona, 0), 2) as pct_votos
        FROM t_tot
        LEFT JOIN t_item ON t_tot.id_municipio = t_item.id_municipio AND t_tot.zona = t_item.zona
    """
    return con.execute(query_join).df()

@st.cache_data(ttl=3600)
def get_locais_votacao_base():
    """Retorna a base completa de locais de votação de PE (3.406 colégios)."""
    return pd.read_parquet(PATH_LOCAIS_PARQUET)
