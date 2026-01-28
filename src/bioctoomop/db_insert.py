from .db_note import NOTE_SQL
from .db_note_nlp import NOTE_NLP_SQL


def insert_notes(conn, notes):
    if not notes:
        return
    with conn.cursor() as cur:
        cur.executemany(NOTE_SQL, notes)
    conn.commit()

def trim_snippet(note_nlp_row, max_length=250):
    snippet = note_nlp_row["snippet"]
    if len(snippet) <= max_length:
        return note_nlp_row
    note_nlp_row["snippet"] = snippet[:max_length]
    return note_nlp_row

def insert_note_nlp(conn, note_nlp_rows):
    if not note_nlp_rows:
        return
    note_nlp_rows = [trim_snippet(x) for x in note_nlp_rows]
    with conn.cursor() as cur:
        cur.executemany(NOTE_NLP_SQL, note_nlp_rows)
    conn.commit()

