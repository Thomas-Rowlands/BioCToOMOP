from datetime import date, datetime
from pathlib import Path
import json

# ---- NOTE TABLE ----
def create_note_row(note_id: int, person_id: int, note_text: str, note_source: str, note_type: int, note_class: int, encoding: int, language: int, note_date:str = "") -> dict:
    return {
        "note_id": note_id,
        "person_id": person_id,
        "note_source_value": note_source[:50],  # Truncate to 50 chars if needed
        "note_text": note_text,
        "note_date": note_date if note_date else date.today(),
        "note_class_concept_id": note_class,  # clinical document
        "note_type_concept_id": note_type,   # clinical document
        "encoding_concept_id": encoding,      # UTF-8
        "language_concept_id": language,    # English
    }

# ---- NOTE NLP TABLE ----
def create_note_nlp_row(note_nlp_id, note_id, ent, text, source_concept_id=None, mapping=None):
    return {
        "note_nlp_id": note_nlp_id,
        "note_id": note_id,
        "snippet": _trim_snippet(text, 250),
        "offset": f"{ent['start_offset']}:{ent['end_offset']}",
        "lexical_variant": ent.get("lexical_variant"),
        "note_nlp_concept_id": mapping["standard_concept_id"],
        "note_nlp_source_concept_id": int(source_concept_id) if int(source_concept_id) < 2147483647 else None, # prevent overflow
        "nlp_system": "MedCAT",
        "nlp_date": date.today(),
        "nlp_datetime": datetime.now(),
        "term_modifiers": json.dumps(__get_term_modifiers(ent)),
    }

def __get_term_modifiers(ent):
    return {
        "annotation_id": ent.get("annotation_id"),
        "pretty_name": ent.get("pretty_name"),
        "accuracy": ent.get("acc"),
        "context_similarity": ent.get("context_similarity"),
        "cui": ent.get("cui"),
        "ontology": "SNOMED CT",
    }

def _trim_snippet(snippet, max_length=250):
    if len(snippet) <= max_length:
        return snippet
    return snippet[:max_length]

# ---- END NOTE NLP TABLE ----

# ---- PERSON TABLE ----
def create_person_row(person_id: int, gender: int, year_of_birth: str, race: int, ethnicity: int) -> dict:
    if isinstance(year_of_birth, int):
        year_of_birth = str(year_of_birth)
    return {
        "person_id": person_id,
        "gender_concept_id": gender,  # Default to "Unknown"
        "year_of_birth": int(year_of_birth) if year_of_birth.isdigit() else random_year_of_birth(),  # Default to a random year of birth if not provided or invalid
        "race_concept_id": race,  # Default to "Unknown"
        "ethnicity_concept_id": ethnicity  # Default to "Ethnic group unknown"
        }

def random_year_of_birth():
    # Generate a random age between 0 and 100
    import random
    return random.randint(18, 90)

# ---- END PERSON TABLE ----
# ---- Condition_Occurrence TABLE ----
def create_condition_occurrence_row(condition_occurrence_id, person_id, condition_concept_id, condition_start_date, condition_type_concept_id=None):
    return {
        "condition_occurrence_id": condition_occurrence_id,
        "person_id": person_id,
        "condition_concept_id": condition_concept_id,
        "condition_start_date": condition_start_date,
        "condition_type_concept_id": condition_type_concept_id
    }

# ---- END Condition_Occurrence TABLE ----
# ---- Measurement TABLE ----
def create_measurement_row(measurement_id, person_id, measurement_concept_id, measurement_date, measurement_type_concept_id=None):
    return {
        "measurement_id": measurement_id,
        "person_id": person_id,
        "measurement_concept_id": measurement_concept_id,
        "measurement_date": measurement_date,
        "measurement_type_concept_id": measurement_type_concept_id
    }

# ---- END Measurement TABLE ----
# ---- Observation TABLE ----
def create_observation_row(observation_id, person_id, observation_concept_id, observation_date, observation_type_concept_id=None):
    return {
        "observation_id": observation_id,
        "person_id": person_id,
        "observation_concept_id": observation_concept_id,
        "observation_date": observation_date,
        "observation_type_concept_id": observation_type_concept_id
    }
# ---- END Observation TABLE ----
# ---- Procedure_Occurrence TABLE ----
def create_procedure_occurrence_row(procedure_occurrence_id, person_id, procedure_concept_id, procedure_date, procedure_type_concept_id=None):
    return {
        "procedure_occurrence_id": procedure_occurrence_id,
        "person_id": person_id,
        "procedure_concept_id": procedure_concept_id,
        "procedure_date": procedure_date,
        "procedure_type_concept_id": procedure_type_concept_id
    }
# ---- END Procedure_Occurrence TABLE ----
# ---- Drug_Exposure TABLE ----
def create_drug_exposure_row(drug_exposure_id, person_id, drug_concept_id, drug_exposure_date, drug_exposure_end_date, drug_type_concept_id=None):
    return {
        "drug_exposure_id": drug_exposure_id,
        "person_id": person_id,
        "drug_concept_id": drug_concept_id,
        "drug_exposure_date": drug_exposure_date,
        "drug_exposure_end_date": drug_exposure_date,  # Assuming same day exposure for simplicity; adjust as needed
        "drug_type_concept_id": drug_type_concept_id
    }
# ---- END Drug_Exposure TABLE ----