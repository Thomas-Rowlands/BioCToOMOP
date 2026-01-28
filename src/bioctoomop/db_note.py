NOTE_SQL = """
INSERT INTO omop_cdm.note (
    note_id,
    person_id,
    note_date,
    note_datetime,
    note_type_concept_id,
    note_class_concept_id,
    note_text,
    note_source_value,
    encoding_concept_id,
    language_concept_id
) VALUES (
    %(note_id)s,
    %(person_id)s,
    %(note_date)s,
    NULL,
    %(note_type_concept_id)s,
    %(note_class_concept_id)s,
    %(note_text)s,
    %(note_source_value)s,
    %(encoding_concept_id)s,
    %(language_concept_id)s
)
"""
