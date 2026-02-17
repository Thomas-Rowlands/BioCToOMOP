from datetime import date
from pathlib import Path

LITERATURE_PERSON_ID = 1

def make_note(note_id: int, parsed_doc: dict) -> dict:
    return {
        "note_id": note_id,
        "person_id": LITERATURE_PERSON_ID,
        "note_source_value": parsed_doc["note_source_value"],
        "note_text": parsed_doc["note_text"],
        "note_date": parsed_doc.get("note_date", date.today()),
        "note_class_concept_id": 4309829,  # clinical document
        "note_type_concept_id": 4309829,   # clinical document
        "encoding_concept_id": 32678,      # UTF-8
        "language_concept_id": 4093769,    # English
    }
