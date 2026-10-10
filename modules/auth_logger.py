"""
Módulo de Auditoria e Registro de Acessos (Auth Logger)
Responsável por persistir o histórico de logins e acessos dos usuários cadastrados.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import streamlit as st

# Timezone padrão para registro de auditoria (Horário de Pernambuco / Brasília)
try:
    from zoneinfo import ZoneInfo
    TZ_RECIFE = ZoneInfo("America/Recife")
except Exception:
    TZ_RECIFE = timezone(timedelta(hours=-3))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "access_logs.sqlite3"


def _get_connection():
    """Garante a pasta data e abre conexão segura com SQLite."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _init_db():
    """Cria a tabela de logs se ainda não existir."""
    try:
        with _get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON access_logs (timestamp DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_username ON access_logs (username);")
    except Exception as e:
        print(f"[auth_logger] Erro ao inicializar banco de logs: {e}")


# Inicializa a tabela no carregamento do módulo
_init_db()


def registrar_login(username: str, acao: str = "Login com sucesso", detalhes: str = "") -> bool:
    """
    Registra um evento de login no banco de auditoria.
    
    Args:
        username: Nome do usuário que tentou ou realizou login.
        acao: Descrição do evento ("Login com sucesso", "Tentativa inválida", etc.).
        detalhes: Informações adicionais opcionais.
    """
    if not username:
        return False

    try:
        ts_str = datetime.now(TZ_RECIFE).strftime("%Y-%m-%d %H:%M:%S")
        with _get_connection() as conn:
            conn.execute(
                "INSERT INTO access_logs (timestamp, username, action, details) VALUES (?, ?, ?, ?);",
                (ts_str, str(username).strip(), str(acao), str(detalhes))
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"[auth_logger] Falha ao registrar log de acesso para {username}: {e}")
        return False


def obter_historico_acessos(limit: int = 200) -> pd.DataFrame:
    """
    Retorna o histórico dos acessos registrados como um DataFrame amigável para exibição.
    """
    try:
        with _get_connection() as conn:
            query = """
                SELECT timestamp AS "Data/Hora",
                       username AS "Usuário",
                       action AS "Ação",
                       details AS "Detalhes"
                FROM access_logs
                ORDER BY id DESC
                LIMIT ?;
            """
            df = pd.read_sql_query(query, conn, params=(limit,))
            if not df.empty and "Data/Hora" in df.columns:
                # Converte para formato brasileiro dd/mm/aaaa hh:mm:ss para exibição
                try:
                    df["Data/Hora"] = pd.to_datetime(df["Data/Hora"]).dt.strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    pass
            return df
    except Exception as e:
        print(f"[auth_logger] Falha ao ler histórico de acessos: {e}")
        return pd.DataFrame(columns=["Data/Hora", "Usuário", "Ação", "Detalhes"])


def is_admin_user(username: str) -> bool:
    """
    Verifica se o usuário logado possui privilégios administrativos para visualizar o painel de auditoria.
    """
    if not username:
        return False

    u = username.lower().strip()

    # Usuários administradores padrão
    admins_padrao = {"admin", "demokratia", "gabriel", "otto", "root"}
    if u in admins_padrao:
        return True

    # Permite especificar administradores customizados via secrets.toml (lista ou string separada por vírgula)
    try:
        admin_cfg = st.secrets.get("admin_users", None)
        if admin_cfg:
            if isinstance(admin_cfg, str):
                admin_list = [a.strip().lower() for a in admin_cfg.split(",")]
            elif isinstance(admin_cfg, list):
                admin_list = [str(a).strip().lower() for a in admin_cfg]
            else:
                admin_list = []
            if u in admin_list:
                return True
    except Exception:
        pass

    return False
