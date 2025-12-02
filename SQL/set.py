
from SQL import update as updater


def update(id_to_update, sql_file):
    if not id_to_update:
        return 0

    print(f"ενημέρωση Εγγραφής με ID: {id_to_update}")
    params = {"unique_id": id_to_update}
    # execute SQL (UPDATE) and return affected row count
    result = updater.execute_sql(sql_file, params)
    print(f"Επιτυχής ενημέρωση: {result} Εγγραφή / Εγγραφές")
    return result