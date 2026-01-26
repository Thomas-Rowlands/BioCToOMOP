from datetime import date


def make_note(note_id: int, parsed_doc: dict):
    return {
        "note_id": note_id,
        "note_source_value": parsed_doc["note_source_value"],
        "note_text": parsed_doc["note_text"],
        "note_date": date.today(),
        "note_class_concept_id": 44814645,  # Clinical note
        "note_type_concept_id": 44814649,   # Published clinical document
    }
