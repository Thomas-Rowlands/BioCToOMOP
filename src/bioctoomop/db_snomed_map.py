def load_snomed_to_omop_map(conn):
    """
    Returns: dict[str SNOMED_code -> int OMOP_concept_id]
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT concept_code, concept_id
            FROM omop_cdm.concept
            WHERE vocabulary_id = 'SNOMED'
        """)
        return {code: cid for code, cid in cur.fetchall()}