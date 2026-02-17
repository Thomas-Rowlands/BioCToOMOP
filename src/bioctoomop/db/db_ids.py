def get_max_ids(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(note_id), 0) FROM omop_cdm.note;")
        max_note_id = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(MAX(note_nlp_id), 0) FROM omop_cdm.note_nlp;")
        max_note_nlp_id = cur.fetchone()[0]

    return max_note_id, max_note_nlp_id
