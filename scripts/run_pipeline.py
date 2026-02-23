import json
import os
import random
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

import psycopg
from psycopg.rows import dict_row
from psycopg import sql

# MedCAT & Project Imports
from medcat.cat import CAT
from bioctoomop.bioc_parser import parse_bioc_file
from bioctoomop.medcat_runner import run_medcat_single_note
from bioctoomop.omop_tables.note import make_note
from bioctoomop.omop_tables.note_nlp import entities_to_note_nlp
from bioctoomop.bioc_serialize import write_annotated_bioc

# --- CONFIGURATION ---
# get from .env file first, then fallback to hardcoded defaults for development/testing
DOCUMENT_INPUT_PATH = os.getenv("DOCUMENT_INPUT_PATH", "/home/msztr1/Projects/FAIRClinical_NLP_Pipeline/Original")
MEDCAT_MODEL_PATH = os.getenv("MEDCAT_MODEL_PATH", "models/v2_Snomed2025_MIMIC_IV_bbe806e192df009f.zip")
TOKENIZER_MAX_LENGTH = int(os.getenv("TOKENIZER_MAX_LENGTH", 2_000_000))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")


NOTE_BATCH_SIZE = int(os.getenv("NOTE_BATCH_SIZE", 50))
NOTE_NLP_BATCH_SIZE = int(os.getenv("NOTE_NLP_BATCH_SIZE", 5000))
TEST_LIMIT = os.getenv("TEST_LIMIT", None)
if TEST_LIMIT is not None:
    TEST_LIMIT = int(TEST_LIMIT)

# --- FIXED CONCEPT IDS FROM YOUR ETL RULES ---
NLP_DERIVED_MEAS_TYPE_ID = int(os.getenv("NLP_DERIVED_MEAS_TYPE_ID", 32423)) # "NLP derived" measurement type
NLP_DERIVED_CONDITION_TYPE_ID = int(os.getenv("NLP_DERIVED_CONDITION_TYPE_ID", 32424)) # "NLP derived" condition type
NLP_DERIVED_PROCEDURE_TYPE_ID = int(os.getenv("NLP_DERIVED_PROCEDURE_TYPE_ID", 32425)) # "NLP derived" procedure type
NLP_DERIVED_DRUG_TYPE_ID = int(os.getenv("NLP_DERIVED_DRUG_TYPE_ID", 32426)) # "NLP derived" drug type
NLP_DERIVED_OBSERVATION_TYPE_ID = int(os.getenv("NLP_DERIVED_OBSERVATION_TYPE_ID", 32445)) # "NLP derived" observation type
CLINICAL_DOC_TYPE_ID = int(os.getenv("CLINICAL_DOC_TYPE_ID", 4309829)) # "Clinical document" type concept
UTF8_ENCODING_ID = int(os.getenv("UTF8_ENCODING_ID", 32678)) # "UTF-8"
ENGLISH_LANGUAGE_ID = int(os.getenv("ENGLISH_LANGUAGE_ID", 4180186)) # "English language"

# ================= DEMOGRAPHICS =================

def get_default_demo_values(note_year: int):
    return {
        "year_of_birth": note_year - 40,
        "gender_concept_id": 8551,
        "race_concept_id": 4090518,
        "ethnicity_concept_id": 759814,
    }

def get_processed_files(conn) -> dict:
    processed_dict: dict[str, set[str]] = {}
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT note_source_value FROM note")
        rows = cur.fetchall()
    if rows:
        # populate a set of already processed file names to skip during processing
        for row in rows:
            pmcid, file_name = row[0].split("::")
            if pmcid not in processed_dict:
                processed_dict[pmcid] = set()
            processed_dict[pmcid].add(file_name)
    return processed_dict

def get_pmcid_person_id_map(conn) -> dict:
    pmcid_map: dict[str, int] = {}
    with conn.cursor() as cur:
        cur.execute("SELECT person_id, SPLIT_PART(note_source_value, '::', 1) AS PMCID FROM note")
        rows = cur.fetchall()
    if rows:
        for row in rows:
            person_id, pmcid = row
            pmcid_map[pmcid] = person_id
    return pmcid_map


def safe_parse_age(val):
    try:
        return int(float(val))
    except Exception:
        return None
    
def ensure_date(value):
    if isinstance(value, datetime.date):
        return value

    if isinstance(value, datetime.datetime):
        return value.date()

    if isinstance(value, str):
        # Try ISO format first
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            pass

        # Fallback common formats
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(value, fmt).date()
            except ValueError:
                continue

    raise ValueError(f"Cannot convert {value} to date")



def extract_demographics(entities, route_map, note_date):
    defaults = get_default_demo_values(note_date.year)
    found = {k: None for k in defaults}

    AGE_SNOMED_CODES = {"424144002", "105727008"}

    for ent in entities:
        s_id = str(ent.get("snomed_id"))
        mapping = route_map.get(s_id)
        if not mapping:
            continue

        dom = mapping["domain_id"]
        concept_id = mapping["standard_concept_id"]

        if dom == "Gender" and not found["gender_concept_id"]:
            found["gender_concept_id"] = concept_id
        elif dom == "Race" and not found["race_concept_id"]:
            found["race_concept_id"] = concept_id
        elif dom == "Ethnicity" and not found["ethnicity_concept_id"]:
            found["ethnicity_concept_id"] = concept_id

        if s_id in AGE_SNOMED_CODES:
            age = safe_parse_age(ent.get("value"))
            if age:
                found["year_of_birth"] = note_date.year - age

    return {k: found[k] or defaults[k] for k in defaults}


# ================= ETL MANAGER =================

class OMOPETLManager:
    def __init__(self, conn):
        self.conn = conn

    def get_max_ids(self):
        tables = [
            "note",
            "note_nlp",
            "person",
            "condition_occurrence",
            "measurement",
            "procedure_occurrence",
            "drug_exposure",
            "observation",
        ]

        id_cols = {
            "note": "note_id",
            "note_nlp": "note_nlp_id",
            "person": "person_id",
            "condition_occurrence": "condition_occurrence_id",
            "measurement": "measurement_id",
            "procedure_occurrence": "procedure_occurrence_id",
            "drug_exposure": "drug_exposure_id",
            "observation": "observation_id",
        }

        result = {}
        with self.conn.cursor() as cur:
            for table in tables:
                cur.execute(
                    f"SELECT COALESCE(MAX({id_cols[table]}),0) FROM {table}"
                )
                result[table] = cur.fetchone()[0]

        return result

    def get_routing_map(self, snomed_codes):
        if not snomed_codes:
            return {}

        query = """
        SELECT 
            source.concept_code,
            COALESCE(target.concept_id, source.concept_id) AS standard_concept_id,
            COALESCE(target.domain_id, source.domain_id) AS domain_id
        FROM concept source
        LEFT JOIN concept_relationship cr
            ON source.concept_id = cr.concept_id_1
            AND cr.relationship_id = 'Maps to'
            AND cr.invalid_reason IS NULL
        LEFT JOIN concept target
            ON cr.concept_id_2 = target.concept_id
        WHERE source.concept_code = ANY(%s::text[])
        AND source.vocabulary_id ILIKE 'SNOMED%%';
        """

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (list(set(snomed_codes)),))
            rows = cur.fetchall()

        return {r["concept_code"]: r for r in rows}

    def fast_insert(self, table_name, data):
        if not data:
            return

        cols = list(data[0].keys())
        query = sql.SQL("COPY {} ({}) FROM STDIN").format(
            sql.Identifier(table_name),
            sql.SQL(", ").join(map(sql.Identifier, cols)),
        )

        with self.conn.cursor() as cur:
            with cur.copy(query) as copy:
                for row in data:
                    copy.write_row([row.get(c) for c in cols])


# ================= BATCH PROCESSOR =================

def process_medcat_batch(
    cat,
    etl,
    note_buffer,
    note_texts,
    note_sentences,
    note_nlp_buffer,
    ids
):
    try:
        results = list(cat.get_entities_multi_texts(texts=note_texts, n_process=1))
    except Exception as e:
        try:
            # If the batch processing fails, attempt to process notes individually to isolate problematic records
            results = []
            for note_id_str, text in note_texts:
                try:
                    res = cat.get_entities(text=text)
                    results.append((note_id_str, res))
                except Exception as inner_e:
                    print(f"Error processing note ID {note_id_str}: {inner_e}")
                    results.append((note_id_str, None))  # Append None for failed records
        except Exception as batch_e:
            raise RuntimeError(f"Batch processing failed and individual processing also failed: {batch_e}") from batch_e

    note_lookup = {n["note_id"]: n for n in note_buffer}

    # Collect all SNOMED codes across batch
    all_codes = []
    for _, res in results:
        if res:
            for ent in res["entities"].values():
                if ent.get("cui"):
                    all_codes.append(str(ent.get("cui")))

    route_map = etl.get_routing_map(all_codes)

    person_rows = []
    note_rows = []
    cond_rows = []
    meas_rows = []
    proc_rows = []
    drug_rows = []
    obs_rows = []

    for note_id_str, medcat_result in results:
        if not medcat_result:
            continue
        note_id = int(note_id_str)
        sentences = note_sentences[note_id]
        sentences_by_id = {s["sentence_id"]: s for s in sentences}
        entities = run_medcat_single_note(note_id, sentences, medcat_result)

        # Determine detected dates for this note
        detected_dates = []

        for ent in entities:
            d = ent.get("detected_date")
            if isinstance(d, datetime.date):
                detected_dates.append(d)

        note_info = note_lookup[note_id]
        note_info["note_date"] = ensure_date(note_info["note_date"])

        # PERSON
        if note_info.get("person_id") == 1: # placeholder value indicating person_id not set
            ids["person"] += 1
            person_id = ids["person"]
        else:
            person_id = note_info["person_id"]

        demo = extract_demographics(
            entities, route_map, note_info["note_date"]
        )

        person_rows.append({
            "person_id": person_id,
            "gender_concept_id": demo["gender_concept_id"],
            "year_of_birth": demo["year_of_birth"],
            "race_concept_id": demo["race_concept_id"],
            "ethnicity_concept_id": demo["ethnicity_concept_id"],
        })

        # NOTE
        note_info.update({
            "person_id": person_id,
            "note_type_concept_id": CLINICAL_DOC_TYPE_ID,
            "note_class_concept_id": CLINICAL_DOC_TYPE_ID,
            "encoding_concept_id": UTF8_ENCODING_ID,
            "language_concept_id": ENGLISH_LANGUAGE_ID,
        })

        note_rows.append(note_info)
        

        # ENTITIES
        for ent in entities:
            snomed = str(ent.get("snomed_id"))
            mapping = route_map.get(snomed)
            if not mapping:
                continue

            event_date = ent.get("detected_date") or min(detected_dates) if detected_dates else note_info["note_date"]

            # NOTE_NLP
            ids["note_nlp"] += 1
            note_nlp_id = ids["note_nlp"]

            sent_obj = sentences_by_id.get(ent.get("sentence_id"))
            sentence_text = sent_obj["text"] if sent_obj else None

            term_modifiers = {
                "annotation_id": ent.get("annotation_id"),
                "pretty_name": ent.get("pretty_name"),
                "accuracy": ent.get("acc"),
                "context_similarity": ent.get("context_similarity"),
                "cui": ent.get("cui"),
                "ontology": "SNOMED CT",
            }

            note_nlp_buffer.append({
                "note_nlp_id": note_nlp_id,
                "note_id": note_id,
                "snippet": sentence_text[:250],
                "offset": f"{ent['start_offset']}:{ent['end_offset']}",
                "lexical_variant": ent.get("lexical_variant"),
                "note_nlp_concept_id": mapping["standard_concept_id"],
                "note_nlp_source_concept_id": int(snomed) if int(snomed) < 2147483647 else None, # prevent overflow
                "nlp_system": "MedCAT",
                "nlp_date": datetime.date.today(),
                "nlp_datetime": datetime.datetime.now(),
                "term_modifiers": json.dumps(term_modifiers),
            })

            domain = mapping["domain_id"]

            if domain == "Condition":
                ids["condition_occurrence"] += 1
                cond_rows.append({
                    "condition_occurrence_id": ids["condition_occurrence"],
                    "person_id": person_id,
                    "condition_concept_id": mapping["standard_concept_id"],
                    "condition_start_date": event_date,
                    "condition_type_concept_id": NLP_DERIVED_CONDITION_TYPE_ID,
                })

            elif domain == "Measurement":
                ids["measurement"] += 1
                meas_rows.append({
                    "measurement_id": ids["measurement"],
                    "person_id": person_id,
                    "measurement_concept_id": mapping["standard_concept_id"],
                    "measurement_date": event_date,
                    "measurement_type_concept_id": NLP_DERIVED_MEAS_TYPE_ID,
                })

            elif domain == "Procedure":
                ids["procedure_occurrence"] += 1
                proc_rows.append({
                    "procedure_occurrence_id": ids["procedure_occurrence"],
                    "person_id": person_id,
                    "procedure_concept_id": mapping["standard_concept_id"],
                    "procedure_date": event_date,
                    "procedure_type_concept_id": NLP_DERIVED_PROCEDURE_TYPE_ID,
                })

            elif domain == "Drug":
                ids["drug_exposure"] += 1
                drug_rows.append({
                    "drug_exposure_id": ids["drug_exposure"],
                    "person_id": person_id,
                    "drug_concept_id": mapping["standard_concept_id"],
                    "drug_exposure_start_date": event_date,
                    "drug_exposure_end_date": event_date,
                    "drug_type_concept_id": NLP_DERIVED_DRUG_TYPE_ID,
                })

            elif domain == "Observation":
                ids["observation"] += 1
                obs_rows.append({
                    "observation_id": ids["observation"],
                    "person_id": person_id,
                    "observation_concept_id": mapping["standard_concept_id"],
                    "observation_date": event_date,
                    "observation_type_concept_id": NLP_DERIVED_OBSERVATION_TYPE_ID,
                })


    etl.fast_insert("person", person_rows)
    etl.fast_insert("note", note_rows)
    etl.fast_insert("condition_occurrence", cond_rows)
    etl.fast_insert("measurement", meas_rows)
    etl.fast_insert("procedure_occurrence", proc_rows)
    etl.fast_insert("drug_exposure", drug_rows)
    etl.fast_insert("observation", obs_rows)

    return ids


# ================= MAIN =================

def main():
    input_root = Path(DOCUMENT_INPUT_PATH)
    cat = CAT.load_model_pack(MEDCAT_MODEL_PATH)
    cat.pipe.tokenizer._nlp.max_length = TOKENIZER_MAX_LENGTH

    conn_str = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"

    with psycopg.connect(conn_str) as conn:
        conn.execute("SET search_path TO omop_cdm")

        processed_files = get_processed_files(conn)

        etl = OMOPETLManager(conn)
        max_ids = etl.get_max_ids()

        person_id_map = get_pmcid_person_id_map(etl.conn)

        ids = {
            "note": max_ids["note"],
            "note_nlp": max_ids["note_nlp"],
            "person": max_ids["person"],
            "condition_occurrence": max_ids["condition_occurrence"],
            "measurement": max_ids["measurement"],
            "procedure_occurrence": max_ids["procedure_occurrence"],
            "drug_exposure": max_ids["drug_exposure"],
            "observation": max_ids["observation"],
        }

        bioc_files = list(input_root.rglob("*.json"))

        if TEST_LIMIT:
            bioc_files = bioc_files[:TEST_LIMIT]

        note_buffer, note_texts, note_sentences, note_nlp_buffer = [], [], {}, []

        for bioc_file in tqdm(bioc_files):
            # skip tables-json BioC files which are unsupported in this pipeline version
            if bioc_file.name.endswith("_tables.json"):
                continue

            # Skip previously processed files based on pmcid and file name

            is_supplementary = False

            if "XX" in str(bioc_file.parent.name):
                pmc_id = str(bioc_file.name).replace(".json", "")
            elif "Processed" in str(bioc_file.parent.name):
                pmc_id = str(bioc_file.parent.parent.name).replace("_supplementary", "")
                is_supplementary = True
            else:
                pmc_id = str(bioc_file.parent.name).replace("_supplementary", "")
                is_supplementary = True

            trimmed_file_name = F"{pmc_id}::{str(bioc_file.name)}"[:50]
            trimmed_file_name = trimmed_file_name.split("::")[1]

            if pmc_id in processed_files and trimmed_file_name in processed_files[pmc_id]:
                continue

            # Extract and parse the BioC file to get note text and sentences

            parsed = parse_bioc_file(bioc_file, is_supplementary=is_supplementary)
            if not parsed:
                continue

            ids["note"] += 1
            note_id = ids["note"]

            note_record = make_note(note_id, parsed)
            
            if person_id_map.get(pmc_id):
                note_record["person_id"] = person_id_map[pmc_id]
            else:
                ids["person"] += 1


            note_buffer.append(note_record)
            note_texts.append((str(note_id),
                               " ".join(s["text"] for s in parsed["sentences"])))
            note_sentences[note_id] = parsed["sentences"]

            if len(note_texts) >= NOTE_BATCH_SIZE:
                ids = process_medcat_batch(
                    cat, etl, note_buffer, note_texts,
                    note_sentences, note_nlp_buffer, ids
                )

                note_buffer.clear()
                note_texts.clear()
                note_sentences.clear()

                if len(note_nlp_buffer) >= NOTE_NLP_BATCH_SIZE:
                    etl.fast_insert("note_nlp", note_nlp_buffer)
                    note_nlp_buffer.clear()

                conn.commit()

        if note_texts:
            ids = process_medcat_batch(
                cat, etl, note_buffer, note_texts,
                note_sentences, note_nlp_buffer, ids
            )
            conn.commit()

        if note_nlp_buffer:
            etl.fast_insert("note_nlp", note_nlp_buffer)
            conn.commit()


if __name__ == "__main__":
    main()