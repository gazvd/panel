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

@st.cache_data(ttl=3600)
def get_vencedores_municipios(ano: int, turno: int, cargo: str, modo: str = "Candidato"):
    """
    Retorna o 1º colocado (vencedor), 2º colocado, percentuais e margem de vitória
    para todos os 185 municípios de Pernambuco.
    """
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    is_pres = (cargo == "presidente")

    if modo == "Partido":
        q = f"""
        WITH agg AS (
            SELECT 
                id_municipio,
                sigla_partido as nome_display,
                sigla_partido,
                NULL as numero_candidato,
                SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND sigla_partido IS NOT NULL
            GROUP BY id_municipio, sigla_partido
        ),
        ranked AS (
            SELECT 
                id_municipio,
                nome_display,
                sigla_partido,
                numero_candidato,
                votos,
                SUM(votos) OVER (PARTITION BY id_municipio) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY id_municipio ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT 
                id_municipio,
                nome_display as vencedor,
                sigla_partido as partido_vencedor,
                numero_candidato as numero_vencedor,
                votos as votos_vencedor,
                total_validos,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT 
                id_municipio,
                nome_display as segundo,
                sigla_partido as partido_segundo,
                votos as votos_segundo,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.id_municipio,
            f.vencedor,
            f.partido_vencedor,
            f.numero_vencedor,
            f.votos_vencedor,
            f.total_validos,
            f.pct_vencedor,
            COALESCE(s.segundo, '-') as segundo,
            COALESCE(s.partido_segundo, '-') as partido_segundo,
            COALESCE(s.votos_segundo, 0) as votos_segundo,
            COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct,
            (f.votos_vencedor - COALESCE(s.votos_segundo, 0)) as margem_votos
        FROM firsts f
        LEFT JOIN seconds s ON f.id_municipio = s.id_municipio
        ORDER BY f.votos_vencedor DESC
        """
        return con.execute(q).df()

    elif is_pres:
        q = f"""
        WITH agg AS (
            SELECT 
                id_municipio,
                sigla_partido,
                SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND sigla_partido IS NOT NULL
            GROUP BY id_municipio, sigla_partido
        ),
        ranked AS (
            SELECT 
                id_municipio,
                sigla_partido,
                votos,
                SUM(votos) OVER (PARTITION BY id_municipio) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY id_municipio ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT 
                id_municipio,
                sigla_partido as partido_vencedor,
                votos as votos_vencedor,
                total_validos,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT 
                id_municipio,
                sigla_partido as partido_segundo,
                votos as votos_segundo,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.id_municipio,
            f.partido_vencedor,
            f.votos_vencedor,
            f.total_validos,
            f.pct_vencedor,
            COALESCE(s.partido_segundo, '-') as partido_segundo,
            COALESCE(s.votos_segundo, 0) as votos_segundo,
            COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct,
            (f.votos_vencedor - COALESCE(s.votos_segundo, 0)) as margem_votos
        FROM firsts f
        LEFT JOIN seconds s ON f.id_municipio = s.id_municipio
        ORDER BY f.votos_vencedor DESC
        """
        df = con.execute(q).df()
        df['vencedor'] = df['partido_vencedor'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})"))
        df['segundo'] = df['partido_segundo'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})") if s != '-' else '-')
        df['numero_vencedor'] = None
        return df

    else:
        q = f"""
        WITH agg AS (
            SELECT 
                id_municipio,
                nome_urna,
                sigla_partido,
                numero_candidato,
                SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}'
            GROUP BY id_municipio, nome_urna, sigla_partido, numero_candidato
        ),
        ranked AS (
            SELECT 
                id_municipio,
                nome_urna,
                sigla_partido,
                numero_candidato,
                votos,
                SUM(votos) OVER (PARTITION BY id_municipio) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY id_municipio ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT 
                id_municipio,
                nome_urna as vencedor,
                sigla_partido as partido_vencedor,
                numero_candidato as numero_vencedor,
                votos as votos_vencedor,
                total_validos,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT 
                id_municipio,
                nome_urna as segundo,
                sigla_partido as partido_segundo,
                votos as votos_segundo,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.id_municipio,
            f.vencedor,
            f.partido_vencedor,
            f.numero_vencedor,
            f.votos_vencedor,
            f.total_validos,
            f.pct_vencedor,
            COALESCE(s.segundo, '-') as segundo,
            COALESCE(s.partido_segundo, '-') as partido_segundo,
            COALESCE(s.votos_segundo, 0) as votos_segundo,
            COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct,
            (f.votos_vencedor - COALESCE(s.votos_segundo, 0)) as margem_votos
        FROM firsts f
        LEFT JOIN seconds s ON f.id_municipio = s.id_municipio
        ORDER BY f.votos_vencedor DESC
        """
        return con.execute(q).df()

@st.cache_data(ttl=3600)
def get_vencedores_zonas(ano: int, turno: int, cargo: str, modo: str = "Candidato"):
    """
    Retorna o 1º colocado (vencedor), 2º colocado, percentuais e margem de vitória
    para todas as 209 Zonas Eleitorais de Pernambuco.
    """
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    is_pres = (cargo == "presidente")

    if modo == "Partido":
        q = f"""
        WITH agg AS (
            SELECT 
                id_municipio,
                zona,
                sigla_partido as nome_display,
                sigla_partido,
                SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND sigla_partido IS NOT NULL
            GROUP BY id_municipio, zona, sigla_partido
        ),
        ranked AS (
            SELECT 
                id_municipio,
                zona,
                nome_display,
                sigla_partido,
                votos,
                SUM(votos) OVER (PARTITION BY id_municipio, zona) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY id_municipio, zona ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT 
                id_municipio,
                zona,
                nome_display as vencedor,
                sigla_partido as partido_vencedor,
                votos as votos_vencedor,
                total_validos,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT 
                id_municipio,
                zona,
                nome_display as segundo,
                sigla_partido as partido_segundo,
                votos as votos_segundo,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.id_municipio,
            f.zona,
            f.vencedor,
            f.partido_vencedor,
            f.votos_vencedor,
            f.total_validos,
            f.pct_vencedor,
            COALESCE(s.segundo, '-') as segundo,
            COALESCE(s.partido_segundo, '-') as partido_segundo,
            COALESCE(s.votos_segundo, 0) as votos_segundo,
            COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct,
            (f.votos_vencedor - COALESCE(s.votos_segundo, 0)) as margem_votos
        FROM firsts f
        LEFT JOIN seconds s ON f.id_municipio = s.id_municipio AND f.zona = s.zona
        ORDER BY f.votos_vencedor DESC
        """
        return con.execute(q).df()

    elif is_pres:
        q = f"""
        WITH agg AS (
            SELECT 
                id_municipio,
                zona,
                sigla_partido,
                SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND sigla_partido IS NOT NULL
            GROUP BY id_municipio, zona, sigla_partido
        ),
        ranked AS (
            SELECT 
                id_municipio,
                zona,
                sigla_partido,
                votos,
                SUM(votos) OVER (PARTITION BY id_municipio, zona) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY id_municipio, zona ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT 
                id_municipio,
                zona,
                sigla_partido as partido_vencedor,
                votos as votos_vencedor,
                total_validos,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT 
                id_municipio,
                zona,
                sigla_partido as partido_segundo,
                votos as votos_segundo,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.id_municipio,
            f.zona,
            f.partido_vencedor,
            f.votos_vencedor,
            f.total_validos,
            f.pct_vencedor,
            COALESCE(s.partido_segundo, '-') as partido_segundo,
            COALESCE(s.votos_segundo, 0) as votos_segundo,
            COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct,
            (f.votos_vencedor - COALESCE(s.votos_segundo, 0)) as margem_votos
        FROM firsts f
        LEFT JOIN seconds s ON f.id_municipio = s.id_municipio AND f.zona = s.zona
        ORDER BY f.votos_vencedor DESC
        """
        df = con.execute(q).df()
        df['vencedor'] = df['partido_vencedor'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})"))
        df['segundo'] = df['partido_segundo'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})") if s != '-' else '-')
        df['numero_vencedor'] = None
        return df

    else:
        q = f"""
        WITH agg AS (
            SELECT 
                id_municipio,
                zona,
                nome_urna,
                sigla_partido,
                numero_candidato,
                SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}'
            GROUP BY id_municipio, zona, nome_urna, sigla_partido, numero_candidato
        ),
        ranked AS (
            SELECT 
                id_municipio,
                zona,
                nome_urna,
                sigla_partido,
                numero_candidato,
                votos,
                SUM(votos) OVER (PARTITION BY id_municipio, zona) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY id_municipio, zona ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT 
                id_municipio,
                zona,
                nome_urna as vencedor,
                sigla_partido as partido_vencedor,
                numero_candidato as numero_vencedor,
                votos as votos_vencedor,
                total_validos,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT 
                id_municipio,
                zona,
                nome_urna as segundo,
                sigla_partido as partido_segundo,
                votos as votos_segundo,
                ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.id_municipio,
            f.zona,
            f.vencedor,
            f.partido_vencedor,
            f.numero_vencedor,
            f.votos_vencedor,
            f.total_validos,
            f.pct_vencedor,
            COALESCE(s.segundo, '-') as segundo,
            COALESCE(s.partido_segundo, '-') as partido_segundo,
            COALESCE(s.votos_segundo, 0) as votos_segundo,
            COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct,
            (f.votos_vencedor - COALESCE(s.votos_segundo, 0)) as margem_votos
        FROM firsts f
        LEFT JOIN seconds s ON f.id_municipio = s.id_municipio AND f.zona = s.zona
        ORDER BY f.votos_vencedor DESC
        """
        return con.execute(q).df()

@st.cache_data(ttl=3600)
def get_vencedores_regioes(ano: int, turno: int, cargo: str, modo: str = "Candidato", df_mun_map: pd.DataFrame = None):
    """
    Retorna o 1º colocado (vencedor), 2º colocado, percentuais e margem de vitória
    para as 12 Regiões de Desenvolvimento de Pernambuco.
    """
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    is_pres = (cargo == "presidente")

    if modo == "Partido":
        q = f"""
        SELECT id_municipio, sigla_partido as nome_display, sigla_partido, SUM(total_votos) as votos
        FROM '{res_path}'
        WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND sigla_partido IS NOT NULL
        GROUP BY id_municipio, sigla_partido
        """
        df_base = con.execute(q).df()
    elif is_pres:
        q = f"""
        SELECT id_municipio, sigla_partido, SUM(total_votos) as votos
        FROM '{res_path}'
        WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND sigla_partido IS NOT NULL
        GROUP BY id_municipio, sigla_partido
        """
        df_base = con.execute(q).df()
        df_base['nome_display'] = df_base['sigla_partido'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})"))
    else:
        q = f"""
        SELECT id_municipio, nome_urna as nome_display, sigla_partido, SUM(total_votos) as votos
        FROM '{res_path}'
        WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}'
        GROUP BY id_municipio, nome_urna, sigla_partido
        """
        df_base = con.execute(q).df()

    df_base['CD_MUN'] = df_base['id_municipio'].astype(str)
    
    # Merge com mapeamento de regiões
    if df_mun_map is not None:
        map_reg = df_mun_map[['CD_MUN', 'REGIAO_DESENVOLVIMENTO']].drop_duplicates()
    else:
        from modules.geo_loader import load_municipios_gdf
        gdf_m = load_municipios_gdf()
        map_reg = gdf_m[['CD_MUN', 'REGIAO_DESENVOLVIMENTO']].drop_duplicates()
        map_reg['CD_MUN'] = map_reg['CD_MUN'].astype(str)

    df_merged = df_base.merge(map_reg, on='CD_MUN', how='inner')
    
    # Agregar por RD e candidato/partido
    df_agg = df_merged.groupby(['REGIAO_DESENVOLVIMENTO', 'nome_display', 'sigla_partido'])['votos'].sum().reset_index()
    
    # Calcular totais válidos e ranking por RD
    df_agg['total_validos'] = df_agg.groupby('REGIAO_DESENVOLVIMENTO')['votos'].transform('sum')
    df_agg['pct_votos'] = (100.0 * df_agg['votos'] / df_agg['total_validos'].replace(0, 1)).round(2)
    df_agg['rk'] = df_agg.groupby('REGIAO_DESENVOLVIMENTO')['votos'].rank(ascending=False, method='first')
    
    firsts = df_agg[df_agg['rk'] == 1].rename(columns={
        'nome_display': 'vencedor',
        'sigla_partido': 'partido_vencedor',
        'votos': 'votos_vencedor',
        'pct_votos': 'pct_vencedor'
    })
    
    seconds = df_agg[df_agg['rk'] == 2].rename(columns={
        'nome_display': 'segundo',
        'sigla_partido': 'partido_segundo',
        'votos': 'votos_segundo',
        'pct_votos': 'pct_segundo'
    })
    
    res = firsts[['REGIAO_DESENVOLVIMENTO', 'vencedor', 'partido_vencedor', 'votos_vencedor', 'total_validos', 'pct_vencedor']].merge(
        seconds[['REGIAO_DESENVOLVIMENTO', 'segundo', 'partido_segundo', 'votos_segundo', 'pct_segundo']],
        on='REGIAO_DESENVOLVIMENTO',
        how='left'
    )
    res['segundo'] = res['segundo'].fillna('-')
    res['partido_segundo'] = res['partido_segundo'].fillna('-')
    res['votos_segundo'] = res['votos_segundo'].fillna(0).astype(int)
    res['pct_segundo'] = res['pct_segundo'].fillna(0.0)
    res['margem_pct'] = (res['pct_vencedor'] - res['pct_segundo']).round(2)
    res['margem_votos'] = res['votos_vencedor'] - res['votos_segundo']
    
    return res.sort_values('votos_vencedor', ascending=False).reset_index(drop=True)

@st.cache_data(ttl=3600)
def get_vencedores_secoes_mun(ano: int, turno: int, cargo: str, id_municipio: int, modo: str = "Candidato"):
    """
    Retorna o vencedor e 2º colocado por seção eleitoral de um determinado município.
    """
    con = get_connection()
    res_path = str(PATH_RESULTADOS).replace("\\", "/")
    is_pres = (cargo == "presidente")

    if modo == "Partido":
        q = f"""
        WITH agg AS (
            SELECT 
                zona, secao, sigla_partido as nome_display, sigla_partido, SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND id_municipio = {id_municipio} AND sigla_partido IS NOT NULL
            GROUP BY zona, secao, sigla_partido
        ),
        ranked AS (
            SELECT 
                zona, secao, nome_display, sigla_partido, votos,
                SUM(votos) OVER (PARTITION BY zona, secao) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY zona, secao ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT zona, secao, nome_display as vencedor, sigla_partido as partido_vencedor, votos as votos_vencedor, total_validos,
                   ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT zona, secao, nome_display as segundo, sigla_partido as partido_segundo, votos as votos_segundo,
                   ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.zona, f.secao, f.vencedor, f.partido_vencedor, f.votos_vencedor, f.total_validos, f.pct_vencedor,
            COALESCE(s.segundo, '-') as segundo, COALESCE(s.partido_segundo, '-') as partido_segundo,
            COALESCE(s.votos_segundo, 0) as votos_segundo, COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct
        FROM firsts f
        LEFT JOIN seconds s ON f.zona = s.zona AND f.secao = s.secao
        """
        return con.execute(q).df()

    elif is_pres:
        q = f"""
        WITH agg AS (
            SELECT 
                zona, secao, sigla_partido, SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND id_municipio = {id_municipio} AND sigla_partido IS NOT NULL
            GROUP BY zona, secao, sigla_partido
        ),
        ranked AS (
            SELECT 
                zona, secao, sigla_partido, votos,
                SUM(votos) OVER (PARTITION BY zona, secao) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY zona, secao ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT zona, secao, sigla_partido as partido_vencedor, votos as votos_vencedor, total_validos,
                   ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT zona, secao, sigla_partido as partido_segundo, votos as votos_segundo,
                   ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.zona, f.secao, f.partido_vencedor, f.votos_vencedor, f.total_validos, f.pct_vencedor,
            COALESCE(s.partido_segundo, '-') as partido_segundo, COALESCE(s.votos_segundo, 0) as votos_segundo,
            COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct
        FROM firsts f
        LEFT JOIN seconds s ON f.zona = s.zona AND f.secao = s.secao
        """
        df = con.execute(q).df()
        df['vencedor'] = df['partido_vencedor'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})"))
        df['segundo'] = df['partido_segundo'].apply(lambda s: PRESIDENTES_NOMES.get((ano, s), f"Presidenciável ({s})") if s != '-' else '-')
        return df

    else:
        q = f"""
        WITH agg AS (
            SELECT 
                zona, secao, nome_urna, sigla_partido, SUM(total_votos) as votos
            FROM '{res_path}'
            WHERE ano = {ano} AND turno = {turno} AND cargo = '{cargo}' AND id_municipio = {id_municipio}
            GROUP BY zona, secao, nome_urna, sigla_partido
        ),
        ranked AS (
            SELECT 
                zona, secao, nome_urna, sigla_partido, votos,
                SUM(votos) OVER (PARTITION BY zona, secao) as total_validos,
                ROW_NUMBER() OVER (PARTITION BY zona, secao ORDER BY votos DESC) as rk
            FROM agg
        ),
        firsts AS (
            SELECT zona, secao, nome_urna as vencedor, sigla_partido as partido_vencedor, votos as votos_vencedor, total_validos,
                   ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_vencedor
            FROM ranked WHERE rk = 1
        ),
        seconds AS (
            SELECT zona, secao, nome_urna as segundo, sigla_partido as partido_segundo, votos as votos_segundo,
                   ROUND(100.0 * votos / NULLIF(total_validos, 0), 2) as pct_segundo
            FROM ranked WHERE rk = 2
        )
        SELECT 
            f.zona, f.secao, f.vencedor, f.partido_vencedor, f.votos_vencedor, f.total_validos, f.pct_vencedor,
            COALESCE(s.segundo, '-') as segundo, COALESCE(s.partido_segundo, '-') as partido_segundo,
            COALESCE(s.votos_segundo, 0) as votos_segundo, COALESCE(s.pct_segundo, 0.0) as pct_segundo,
            ROUND(f.pct_vencedor - COALESCE(s.pct_segundo, 0.0), 2) as margem_pct
        FROM firsts f
        LEFT JOIN seconds s ON f.zona = s.zona AND f.secao = s.secao
        """
        return con.execute(q).df()

