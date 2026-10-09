import os
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LAYERS_DIR = BASE_DIR / "layers"

# Caminhos das bases de dados
PATH_RESULTADOS = DATA_DIR / "resultados_eleicoes_pe.parquet"
PATH_LOCAIS_PARQUET = DATA_DIR / "locais_votacao_pe.parquet"
PATH_LOCAIS_CSV = DATA_DIR / "locais_votacao_pe.csv"

# Caminhos das camadas geoespaciais (GeoParquet otimizado + GeoJSON fallback)
PATH_GEO_REGIOES = LAYERS_DIR / "regioes" / "pe_regioes_desenvolvimento.geojson"
PATH_GEO_MUNICIPIOS = LAYERS_DIR / "municipios" / "pe_municipios.geojson"
PATH_GEO_ZONAS = LAYERS_DIR / "zonas" / "pe_zonas_eleitorais.parquet"
PATH_GEO_DISTRITOS = LAYERS_DIR / "distritos" / "pe_distritos.parquet"
PATH_GEO_MOSAICO = LAYERS_DIR / "bairros" / "pe_mosaico_bairros_distritos.parquet"
PATH_GEO_RECIFE_BAIRROS = LAYERS_DIR / "bairros" / "recife_bairros.geojson"

# Lista oficial das 12 Regiões de Desenvolvimento de Pernambuco (com Fernando de Noronha na Metropolitana)
REGIOES_DESENVOLVIMENTO = [
    "METROPOLITANA",
    "MATA NORTE",
    "MATA SUL",
    "AGRESTE CENTRAL",
    "AGRESTE SETENTRIONAL",
    "AGRESTE MERIDIONAL",
    "SERTÃO DO MOXOTÓ",
    "SERTÃO DO PAJEÚ",
    "SERTÃO CENTRAL",
    "SERTÃO DE ITAPARICA",
    "SERTÃO DO ARARIPE",
    "SERTÃO DO SÃO FRANCISCO"
]

# Paleta oficial de cores para partidos
CORES_PARTIDOS = {
    "PT": "#E31A1C",
    "PL": "#002B7F",
    "PSB": "#FEC806",
    "PSDB": "#1F78B4",
    "MDB": "#33A02C",
    "UNIÃO": "#6A3D9A",
    "PP": "#0099FF",
    "PSD": "#9B59B6",
    "REPUBLICANOS": "#0055A5",
    "PODEMOS": "#00C0FF",
    "PDT": "#B15928",
    "SOLIDARIEDADE": "#FF6600",
    "PSOL": "#FFFF33",
    "PC do B": "#800000",
    "CIDADANIA": "#E7298A",
    "AVANTE": "#66A61E",
    "NOVO": "#FF8C00",
    "PRTB": "#006600",
    "REDE": "#00CC99",
    "PV": "#2CA02C"
}
COR_PADRAO = "#4A90E2"

# Mapeamento histórico de presidenciáveis por pleito e partido
PRESIDENTES_NOMES = {
    (2026, "PT"): "Lula",
    (2026, "PL"): "Jair Bolsonaro",
    (2022, "PT"): "Lula",
    (2022, "PL"): "Jair Bolsonaro",
    (2022, "PDT"): "Ciro Gomes",
    (2022, "MDB"): "Simone Tebet",
    (2022, "UNIÃO"): "Soraya Thronicke",
    (2022, "NOVO"): "Felipe d'Avila",
    (2018, "PSL"): "Jair Bolsonaro",
    (2018, "PT"): "Fernando Haddad",
    (2018, "PDT"): "Ciro Gomes",
    (2018, "PSDB"): "Geraldo Alckmin",
    (2018, "NOVO"): "João Amoêdo",
    (2018, "MDB"): "Henrique Meirelles",
    (2018, "REDE"): "Marina Silva",
    (2018, "PSOL"): "Guilherme Boulos",
    (2014, "PT"): "Dilma Rousseff",
    (2014, "PSDB"): "Aécio Neves",
    (2014, "PSB"): "Marina Silva",
    (2014, "PSC"): "Pastor Everaldo",
    (2014, "PV"): "Eduardo Jorge",
    (2014, "PSOL"): "Luciana Genro",
    (2010, "PT"): "Dilma Rousseff",
    (2010, "PSDB"): "José Serra",
    (2010, "PV"): "Marina Silva",
    (2010, "PSOL"): "Plínio de Arruda Sampaio"
}

def fmt_int(val):
    """Formata inteiros com separador de milhar ponto: 1.234.567"""
    if val is None or (hasattr(val, '__iter__') and len(val) == 0):
        return "-"
    try:
        import pandas as pd
        if pd.isna(val): return "-"
        return f"{int(round(float(val))):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(val)

def fmt_pct(val, decimals=2, include_symbol=True):
    """Formata percentuais no padrão brasileiro: 44,82%"""
    if val is None:
        return "-"
    try:
        import pandas as pd
        if pd.isna(val): return "-"
        sym = "%" if include_symbol else ""
        return f"{float(val):.{decimals}f}".replace(".", ",") + sym
    except (ValueError, TypeError):
        return str(val)

def normalize_text(s):
    """Remove acentos e converte para maiúsculas para buscas insensíveis a acentuação e caixa."""
    if s is None:
        return ""
    import unicodedata
    return unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

def wrap_label(text: str, max_chars: int = 26) -> str:
    """Quebra textos longos com <br> para evitar reticências (...) e transbordamento em caixas e gráficos."""
    if not text or len(str(text)) <= max_chars:
        return str(text) if text is not None else ""
    words = str(text).split(" ")
    lines = []
    current_line = []
    current_len = 0
    for w in words:
        if current_len + len(w) + 1 > max_chars and current_line:
            lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
        else:
            current_line.append(w)
            current_len += len(w) + 1
    if current_line:
        lines.append(" ".join(current_line))
    return "<br>".join(lines)

def get_cores_foco(nome_candidato=None, sigla_partido=None):
    """
    Retorna (cor_hex, escala_plotly, escala_folium) de acordo com a identidade visual:
    - João Campos / PSB: Amarelo (#FEC806 / YlOrRd)
    - Raquel Lyra / PSD: Roxo Claro (#9B59B6 / Purples)
    - PT / Lula: Vermelho (#E31A1C / Reds)
    - PL / Bolsonaro / Gilson: Azul (#002B7F / Blues)
    """
    import unicodedata
    def _norm(s):
        if not s: return ""
        return unicodedata.normalize('NFKD', str(s)).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

    c_norm = _norm(nome_candidato)
    p_norm = _norm(sigla_partido)
    
    # Se sigla_partido não foi informada mas nome_candidato for a sigla ou contiver (PARTIDO)
    if not p_norm and c_norm:
        p_clean = c_norm.replace("(PARTIDO)", "").replace("(LEGENDA)", "").replace("PARTIDO", "").strip()
        p_norm = p_clean

    # 1. Candidatos com identidade visual marcante
    if any(k in c_norm for k in ["JOAO CAMPOS", "DANILO CABRAL"]):
        return "#FEC806", ["#FFFDE7", "#FFF59D", "#FEC806", "#F57F17", "#E65100"], "YlOrRd"
        
    if "RAQUEL LYRA" in c_norm:
        return "#9B59B6", ["#F3E5F5", "#CE93D8", "#9B59B6", "#7B1FA2", "#4A148C"], "Purples"
        
    if "MARILIA ARRAES" in c_norm:
        if p_norm == "PT":
            return "#E31A1C", ["#FFCDD2", "#E53935", "#B71C1C"], "Reds"
        else:
            return "#FF6600", ["#FFE0B2", "#FB8C00", "#E65100"], "Oranges"
            
    if any(k in c_norm for k in ["LULA", "HUMBERTO COSTA", "TERESA LEITAO"]):
        return "#E31A1C", ["#FFCDD2", "#E53935", "#B71C1C"], "Reds"
        
    if any(k in c_norm for k in ["GILSON MACHADO", "BOLSONARO", "ANDERSON FERREIRA", "MANO MEDEIROS"]):
        return "#002B7F", ["#BBDEFB", "#1976D2", "#0D47A1"], "Blues"
        
    if "MIGUEL COELHO" in c_norm or "SIMAO DURANDO" in c_norm:
        return "#6A3D9A", ["#E1BEE7", "#8E24AA", "#4A148C"], "Purples"
        
    if "DANIEL COELHO" in c_norm:
        return "#0099FF", ["#B3E5FC", "#03A9F4", "#01579B"], "PuBu"
        
    # 2. Por Partido
    if p_norm in ["PT", "PC DO B", "PCO", "PSTU"]:
        return "#E31A1C", ["#FFCDD2", "#E53935", "#B71C1C"], "Reds"
        
    if p_norm in ["PSB"]:
        return "#FEC806", ["#FFFDE7", "#FFF59D", "#FEC806", "#F57F17", "#E65100"], "YlOrRd"

    if p_norm in ["PSD"]:
        return "#9B59B6", ["#F3E5F5", "#CE93D8", "#9B59B6", "#7B1FA2", "#4A148C"], "Purples"

    if p_norm in ["PSOL"]:
        return "#FFFF33", ["#FFFDE7", "#FFF59D", "#FFFF33", "#FBC02D"], "YlOrRd"
        
    if p_norm in ["PL", "REPUBLICANOS", "PP", "PODEMOS", "PRTB"]:
        return "#002B7F", ["#BBDEFB", "#1976D2", "#0D47A1"], "Blues"
        
    if p_norm in ["UNIÃO", "UNIAO"]:
        return "#6A3D9A", ["#E1BEE7", "#8E24AA", "#4A148C"], "Purples"
        
    if p_norm in ["PSDB", "CIDADANIA"]:
        return "#1F78B4", ["#BBDEFB", "#1976D2", "#0D47A1"], "Blues"
        
    if p_norm in ["MDB", "PV", "AVANTE", "REDE"]:
        return "#27AE60", ["#C8E6C9", "#43A047", "#1B5E20"], "Greens"
        
    if p_norm in ["SOLIDARIEDADE", "NOVO"]:
        return "#FF6600", ["#FFE0B2", "#FB8C00", "#E65100"], "Oranges"
        
    if p_norm == "PDT":
        return "#B15928", ["#D7CCC8", "#8D6E63", "#4E342E"], "YlOrBr"
        
    # Padrão suave
    return "#2980B9", ["#BBDEFB", "#1976D2", "#0D47A1"], "Blues"

def get_contrast_color(hex_bg):
    """
    Retorna '#FFFFFF' ou '#1A1A1A' de acordo com a luminância relativa (WCAG 2.1),
    assegurando conformidade AA (>= 4.5:1) ou AAA (>= 7.0:1) para texto sobre fundo colorido.
    """
    if not hex_bg or not isinstance(hex_bg, str) or not hex_bg.startswith("#"):
        return "#FFFFFF"
    try:
        h = hex_bg.lstrip("#")
        if len(h) != 6:
            return "#FFFFFF"
        r, g, b = [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
        def adjust(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        lum = 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)
        cr_white = 1.05 / (lum + 0.05)
        cr_black = (lum + 0.05) / 0.06
        return "#FFFFFF" if cr_white >= cr_black else "#1A1A1A"
    except Exception:
        return "#FFFFFF"
