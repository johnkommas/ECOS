# sql_execute.py (π.χ. νέο αρχείο, ή βάλε το δίπλα στο get_sql_data)

import os
import logging
from sqlalchemy import text
from SQL import sql_connect

logging.basicConfig(level=logging.INFO)


def execute_sql(
    sql_file: str,
    params: dict | None = None,
    connection=None,
) -> int:
    """
    Executes a SQL statement (INSERT/UPDATE/DELETE) from a file.
    Returns the number of affected rows.
    """
    if connection is None:
        connection = sql_connect.connect()

    def get_query_from_file(sfile):
        script_directory = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(script_directory, sfile)
        try:
            with open(full_path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            logging.error("File not found: %s", full_path)
        except Exception as e:
            logging.exception("Error reading SQL file: %s", e)

    query = get_query_from_file(sql_file)
    if not query:
        return 0

    try:
        # engine = connection (since connect() returns engine)
        engine = connection
        # open a transaction
        with engine.begin() as conn:
            result = conn.execute(text(query), params or {})
            # rowcount = πόσες γραμμές άλλαξε
            return result.rowcount
    except Exception as e:
        logging.exception("Error executing SQL statement: %s", e)
        return 0