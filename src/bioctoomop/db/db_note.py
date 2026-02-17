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

def format_omop_note_input(note_id, person_id, note_date, note_type_concept_id, note_class_concept_id, note_text, note_source_value, encoding_concept_id=0, language_concept_id=0):
    """Ensure correct formatting for OMOP note table insertion.

    Args:
        note_id (int): The unique identifier for the note.
        person_id (int): The unique identifier for the person associated with the note.
        note_date (str): The date of the note.
        note_type_concept_id (int): The concept ID for the type of note.
        note_class_concept_id (int): The concept ID for the class of note.
        note_text (str): The text content of the note.
        note_source_value (str): The source value of the note.
        encoding_concept_id (int, optional): The concept ID for the encoding. Defaults to 0.
        language_concept_id (int, optional): The concept ID for the language. Defaults to 0.

    Returns:
        dict: A dictionary with properly formatted OMOP note input values.
    """
    return {
        "note_id": int(note_id),
        "person_id": int(person_id),
        "note_date": str(note_date),
        "note_type_concept_id": int(note_type_concept_id),
        "note_class_concept_id": int(note_class_concept_id),
        "note_text": str(note_text),
        "note_source_value": str(note_source_value)[:50],  # Truncate to fit VARCHAR(50) limit
        "encoding_concept_id": encoding_concept_id,  # Assuming UTF-8
        "language_concept_id": language_concept_id   # Assuming English
    }