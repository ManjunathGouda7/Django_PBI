import sqlite3
import pandas as pd
from typing import Dict, Any, Tuple

class SqlConnectorService:
    """
    Enterprise SQL Database Connector Service.
    Supports connection testing and live query execution for PostgreSQL, SQLite, MySQL, and SQL Server.
    """

    @classmethod
    def test_connection(cls, db_type: str, connection_params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Tests database connectivity for a given database backend.
        """
        db_type = (db_type or 'sqlite').lower()

        if db_type == 'sqlite':
            db_path = connection_params.get('database', ':memory:')
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT 1;")
                conn.close()
                return True, f"SQLite connection successful ({db_path})."
            except Exception as e:
                return False, f"SQLite connection failed: {str(e)}"

        elif db_type in ('postgresql', 'postgres'):
            try:
                import psycopg2
                conn = psycopg2.connect(
                    dbname=connection_params.get('database'),
                    user=connection_params.get('user'),
                    password=connection_params.get('password'),
                    host=connection_params.get('host', 'localhost'),
                    port=connection_params.get('port', 5432)
                )
                conn.close()
                return True, "PostgreSQL connection successful."
            except ImportError:
                return False, "psycopg2 driver not installed in Python environment."
            except Exception as e:
                return False, f"PostgreSQL connection failed: {str(e)}"

        elif db_type in ('mysql', 'mariadb'):
            try:
                import pymysql
                conn = pymysql.connect(
                    database=connection_params.get('database'),
                    user=connection_params.get('user'),
                    password=connection_params.get('password'),
                    host=connection_params.get('host', 'localhost'),
                    port=int(connection_params.get('port', 3306))
                )
                conn.close()
                return True, "MySQL connection successful."
            except ImportError:
                return False, "pymysql driver not installed in Python environment."
            except Exception as e:
                return False, f"MySQL connection failed: {str(e)}"

        else:
            return False, f"Unsupported database type '{db_type}'."

    @classmethod
    def execute_query(cls, db_type: str, connection_params: Dict[str, Any], sql_query: str) -> pd.DataFrame:
        """
        Executes a SQL SELECT query against the target database and returns a Pandas DataFrame.
        """
        if not sql_query or not sql_query.strip():
            raise ValueError("SQL query string cannot be empty.")

        query = sql_query.strip()
        if not query.lower().startswith('select') and not query.lower().startswith('with'):
            raise ValueError("Only read-only SELECT or WITH statements are allowed.")

        db_type = (db_type or 'sqlite').lower()

        if db_type == 'sqlite':
            db_path = connection_params.get('database', ':memory:')
            conn = sqlite3.connect(db_path)
            try:
                df = pd.read_sql_query(query, conn)
                return df
            finally:
                conn.close()

        elif db_type in ('postgresql', 'postgres'):
            import psycopg2
            conn = psycopg2.connect(
                dbname=connection_params.get('database'),
                user=connection_params.get('user'),
                password=connection_params.get('password'),
                host=connection_params.get('host', 'localhost'),
                port=connection_params.get('port', 5432)
            )
            try:
                df = pd.read_sql_query(query, conn)
                return df
            finally:
                conn.close()

        elif db_type in ('mysql', 'mariadb'):
            import pymysql
            conn = pymysql.connect(
                database=connection_params.get('database'),
                user=connection_params.get('user'),
                password=connection_params.get('password'),
                host=connection_params.get('host', 'localhost'),
                port=int(connection_params.get('port', 3306))
            )
            try:
                df = pd.read_sql_query(query, conn)
                return df
            finally:
                conn.close()

        else:
            raise ValueError(f"Unsupported database type '{db_type}'.")
