NOTE_NLP_SQL = """
INSERT INTO omop_cdm.note_nlp (
    note_nlp_id,
    note_id,
    section_concept_id,
    snippet,
    \"offset\",
    lexical_variant,
    note_nlp_concept_id,
    note_nlp_source_concept_id,
    nlp_system,
    nlp_date,
    nlp_datetime,
    term_exists,
    term_temporal,
    term_modifiers
) VALUES (
    %(note_nlp_id)s,
    %(note_id)s,
    NULL,
    %(snippet)s,
    %(offset)s,
    %(lexical_variant)s,
    %(note_nlp_concept_id)s,
    %(note_nlp_source_concept_id)s,
    %(nlp_system)s,
    CURRENT_DATE,
    CURRENT_TIMESTAMP,
    NULL,
    NULL,
    %(term_modifiers)s
)
"""
