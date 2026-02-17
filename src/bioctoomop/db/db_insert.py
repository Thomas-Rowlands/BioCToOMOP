from .db_note import NOTE_SQL, format_omop_note_input
from .db_note_nlp import NOTE_NLP_SQL

def insert_notes(conn, notes):
    if not notes:
        return
    else:
        notes = [format_omop_note_input(**x) for x in notes]
    with conn.cursor() as cur:
        cur.executemany(NOTE_SQL, notes)
    conn.commit()

def insert_note_nlp(conn, note_nlp_rows):
    if not note_nlp_rows:
        return
    with conn.cursor() as cur:
        cur.executemany(NOTE_NLP_SQL, note_nlp_rows)
    conn.commit()

