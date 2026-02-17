import sys
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
import gc

# -------------------------
# CONFIG
# -------------------------
DB_URI = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
CDM_SCHEMA = "omop_cdm"
VOCAB_SCHEMA = "omop_cdm"
SYNTHEA_CSV_DIR = "/mnt/sda2/Projects/BioCToOMOP/scripts/synthea_csv_data"

CSV_CHUNKSIZE = 50_000  # Smaller chunks to be safe
SQL_CHUNKSIZE = 500     # Increased slightly for better throughput

PERSON_ID_OFFSET = 1_000_000
VISIT_ID_OFFSET = 2_000_000

engine = create_engine(DB_URI)

# =========================
# HELPERS
# =========================
def get_total_rows(file_path):
    """Counts lines in CSV for the progress bar without loading it."""
    return sum(1 for _ in open(file_path, 'r')) - 1

def get_max_id(engine, table, id_col):
    """
    Returns the current maximum ID from a specific table to prevent 
    Primary Key violations during incremental loads.
    """
    query = text(f"SELECT MAX({id_col}) FROM {CDM_SCHEMA}.{table}")
    with engine.connect() as conn:
        result = conn.execute(query).scalar()
        return result if result is not None else 0

# =========================
# 1. PERSON (Chunked)
# =========================
print("--- Processing PERSON ---")
gender_map = {"M": 8507, "F": 8532}
patient_id_map = {} # To store mapping for visits/conditions
total_pats = get_total_rows(f"{SYNTHEA_CSV_DIR}/patients.csv")

with tqdm(total=total_pats, desc="Patients") as pbar:
    for i, chunk in enumerate(pd.read_csv(f"{SYNTHEA_CSV_DIR}/patients.csv", chunksize=CSV_CHUNKSIZE)):
        # Generate IDs
        chunk["person_id"] = range(PERSON_ID_OFFSET + (i * CSV_CHUNKSIZE), 
                                   PERSON_ID_OFFSET + (i * CSV_CHUNKSIZE) + len(chunk))
        
        # Store mapping in memory (IDs are small, but we only keep what's needed)
        for _, row in chunk.iterrows():
            patient_id_map[row["Id"]] = row["person_id"]

        person = pd.DataFrame({
            "person_id": chunk["person_id"],
            "gender_concept_id": chunk["GENDER"].map(gender_map).fillna(0).astype(int),
            "year_of_birth": pd.to_datetime(chunk["BIRTHDATE"]).dt.year,
            "month_of_birth": pd.to_datetime(chunk["BIRTHDATE"]).dt.month,
            "day_of_birth": pd.to_datetime(chunk["BIRTHDATE"]).dt.day,
            "race_concept_id": 0,
            "ethnicity_concept_id": 0,
            "person_source_value": chunk["Id"]
        })

        person.to_sql("person", engine, schema=CDM_SCHEMA, if_exists="append", index=False, chunksize=SQL_CHUNKSIZE)
        pbar.update(len(chunk))

# =========================
# 2. VISIT_OCCURRENCE (Chunked)
# =========================
print("\n--- Processing VISIT_OCCURRENCE ---")
visit_id_map = {}
total_enc = get_total_rows(f"{SYNTHEA_CSV_DIR}/encounters.csv")

with tqdm(total=total_enc, desc="Visits") as pbar:
    for i, chunk in enumerate(pd.read_csv(f"{SYNTHEA_CSV_DIR}/encounters.csv", chunksize=CSV_CHUNKSIZE)):
        chunk["visit_occurrence_id"] = range(VISIT_ID_OFFSET + (i * CSV_CHUNKSIZE), 
                                            VISIT_ID_OFFSET + (i * CSV_CHUNKSIZE) + len(chunk))
        
        # Map back to Person ID
        chunk["person_id"] = chunk["PATIENT"].map(patient_id_map)
        
        # Store encounter mapping for Conditions
        for _, row in chunk.iterrows():
            visit_id_map[row["Id"]] = row["visit_occurrence_id"]

        visit = pd.DataFrame({
            "visit_occurrence_id": chunk["visit_occurrence_id"],
            "person_id": chunk["person_id"],
            "visit_concept_id": 9201,
            "visit_start_date": pd.to_datetime(chunk["START"]).dt.date,
            "visit_start_datetime": pd.to_datetime(chunk["START"]),
            "visit_end_date": pd.to_datetime(chunk["STOP"]).dt.date,
            "visit_end_datetime": pd.to_datetime(chunk["STOP"]),
            "visit_type_concept_id": 44818517,
            "visit_source_value": chunk["Id"]
        })
        
        # Drop rows where person_id couldn't be mapped (data integrity)
        visit = visit.dropna(subset=["person_id"])
        
        visit.to_sql("visit_occurrence", engine, schema=CDM_SCHEMA, if_exists="append", index=False, chunksize=SQL_CHUNKSIZE)
        pbar.update(len(chunk))

# =========================
# 3. CONDITION_OCCURRENCE
# =========================
print("\n--- Loading SNOMED Vocabulary ---")
with engine.connect() as conn:
    snomed = pd.read_sql(text(f"SELECT concept_id, concept_code FROM {VOCAB_SCHEMA}.concept WHERE vocabulary_id = 'SNOMED'"), conn)
snomed_map = dict(zip(snomed["concept_code"], snomed["concept_id"]))
del snomed

print("\n--- Processing CONDITION_OCCURRENCE ---")
total_cond = get_total_rows(f"{SYNTHEA_CSV_DIR}/conditions.csv")
cond_id_counter = 1

with tqdm(total=total_cond, desc="Conditions") as pbar:
    for chunk in pd.read_csv(f"{SYNTHEA_CSV_DIR}/conditions.csv", chunksize=CSV_CHUNKSIZE):
        chunk["person_id"] = chunk["PATIENT"].map(patient_id_map)
        chunk["visit_occurrence_id"] = chunk["ENCOUNTER"].map(visit_id_map)
        chunk["condition_concept_id"] = chunk["CODE"].astype(str).map(snomed_map)

        # Filter and assign unique IDs
        chunk = chunk.dropna(subset=["person_id", "condition_concept_id"])
        if chunk.empty:
            pbar.update(CSV_CHUNKSIZE)
            continue
            
        chunk["condition_occurrence_id"] = range(cond_id_counter, cond_id_counter + len(chunk))
        cond_id_counter += len(chunk)

        out = pd.DataFrame({
            "condition_occurrence_id": chunk["condition_occurrence_id"],
            "person_id": chunk["person_id"].astype(int),
            "condition_concept_id": chunk["condition_concept_id"].astype(int),
            "condition_start_date": pd.to_datetime(chunk["START"]).dt.date,
            "condition_start_datetime": pd.to_datetime(chunk["START"]),
            "condition_type_concept_id": 32020,
            "visit_occurrence_id": chunk["visit_occurrence_id"],
            "condition_source_value": chunk["CODE"]
        })

        out.to_sql("condition_occurrence", engine, schema=CDM_SCHEMA, if_exists="append", index=False, chunksize=SQL_CHUNKSIZE)
        pbar.update(len(chunk))
        gc.collect()

# =========================
# 4. DRUG_EXPOSURE
# =========================
print("\n--- Loading RxNorm/Medication Vocabulary ---")
with engine.connect() as conn:
    # Most Synthea medications use RxNorm codes
    rxnorm = pd.read_sql(text(f"""
        SELECT concept_id, concept_code 
        FROM {VOCAB_SCHEMA}.concept 
        WHERE vocabulary_id IN ('RxNorm', 'CVX')
    """), conn)
rx_map = dict(zip(rxnorm["concept_code"].astype(str), rxnorm["concept_id"]))
del rxnorm

print("\n--- Processing DRUG_EXPOSURE ---")
total_meds = get_total_rows(f"{SYNTHEA_CSV_DIR}/medications.csv")
drug_id_counter = 1

with tqdm(total=total_meds, desc="Medications") as pbar:
    for chunk in pd.read_csv(f"{SYNTHEA_CSV_DIR}/medications.csv", chunksize=CSV_CHUNKSIZE):
        # 1. Map IDs
        chunk["person_id"] = chunk["PATIENT"].map(patient_id_map)
        chunk["visit_occurrence_id"] = chunk["ENCOUNTER"].map(visit_id_map)
        chunk["drug_concept_id"] = chunk["CODE"].astype(str).map(rx_map)

        # 2. Filter missing links
        # Fill missing drug concepts with 0 (Unknown) if you want to keep records, 
        # or drop them if you only want mapped data.
        chunk = chunk.dropna(subset=["person_id"])
        chunk["drug_concept_id"] = chunk["drug_concept_id"].fillna(0).astype(int)

        if chunk.empty:
            pbar.update(len(chunk))
            continue

        # 3. Generate Primary Keys
        chunk["drug_exposure_id"] = range(drug_id_counter, drug_id_counter + len(chunk))
        drug_id_counter += len(chunk)

        start_dt = pd.to_datetime(chunk["START"])
        stop_dt = pd.to_datetime(chunk["STOP"])
        stop_dt = stop_dt.combine_first(start_dt)

        # 4. Format for OMOP
        drug_exposure = pd.DataFrame({
            "drug_exposure_id": chunk["drug_exposure_id"],
            "person_id": chunk["person_id"].astype(int),
            "drug_concept_id": chunk["drug_concept_id"],
            "drug_exposure_start_date": start_dt.dt.date,
            "drug_exposure_start_datetime": start_dt,
            "drug_exposure_end_date": stop_dt.dt.date,  # No longer null!
            "drug_exposure_end_datetime": stop_dt,      # No longer null!
            "verbatim_end_date": stop_dt.dt.date,
            "drug_type_concept_id": 32817,
            "visit_occurrence_id": chunk["visit_occurrence_id"],
            "drug_source_value": chunk["CODE"],
            "drug_source_concept_id": 0
        })

        drug_exposure = drug_exposure.dropna(subset=["drug_exposure_end_date"])

        # 5. Load to SQL
        drug_exposure.to_sql(
            "drug_exposure", 
            engine, 
            schema=CDM_SCHEMA, 
            if_exists="append", 
            index=False, 
            chunksize=SQL_CHUNKSIZE
        )
        
        pbar.update(len(chunk))
        del chunk, drug_exposure
        gc.collect()

print("\n--- Processing MEASUREMENT ---")
total_obs = get_total_rows(f"{SYNTHEA_CSV_DIR}/observations.csv")
meas_id_counter = get_max_id(engine, "measurement", "measurement_id") + 1

with tqdm(total=total_obs, desc="Measurements") as pbar:
    for chunk in pd.read_csv(f"{SYNTHEA_CSV_DIR}/observations.csv", chunksize=CSV_CHUNKSIZE):
        # We only want numeric results for the Measurement table
        meas_chunk = chunk[pd.to_numeric(chunk['VALUE'], errors='coerce').notnull()].copy()
        
        if meas_chunk.empty:
            pbar.update(len(chunk))
            continue

        meas_chunk["person_id"] = meas_chunk["PATIENT"].map(patient_id_map)
        meas_chunk["visit_occurrence_id"] = meas_chunk["ENCOUNTER"].map(visit_id_map)
        # Mapping to LOINC concepts (common for labs)
        meas_chunk["measurement_concept_id"] = meas_chunk["CODE"].map(snomed_map).fillna(0).astype(int)

        meas_chunk["measurement_id"] = range(meas_id_counter, meas_id_counter + len(meas_chunk))
        meas_id_counter += len(meas_chunk)

        measurement = pd.DataFrame({
            "measurement_id": meas_chunk["measurement_id"],
            "person_id": meas_chunk["person_id"],
            "measurement_concept_id": meas_chunk["measurement_concept_id"],
            "measurement_date": pd.to_datetime(meas_chunk["DATE"]).dt.date,
            "measurement_datetime": pd.to_datetime(meas_chunk["DATE"]),
            "measurement_type_concept_id": 32817,
            "value_as_number": pd.to_numeric(meas_chunk["VALUE"]),
            "unit_source_value": meas_chunk["UNITS"],
            "measurement_source_value": meas_chunk["CODE"],
            "visit_occurrence_id": meas_chunk["visit_occurrence_id"]
        }).dropna(subset=["person_id"])

        measurement.to_sql("measurement", engine, schema=CDM_SCHEMA, if_exists="append", index=False, chunksize=SQL_CHUNKSIZE)
        pbar.update(len(chunk))
        del meas_chunk, measurement
        gc.collect()

print("\n--- Processing OBSERVATION ---")
# Resetting generator to process the same file but for non-numeric data
obs_id_counter = get_max_id(engine, "observation", "observation_id") + 1

with tqdm(total=total_obs, desc="Observations") as pbar:
    for chunk in pd.read_csv(f"{SYNTHEA_CSV_DIR}/observations.csv", chunksize=CSV_CHUNKSIZE):
        # We take what we skipped in Measurements (non-numeric)
        obs_chunk = chunk[pd.to_numeric(chunk['VALUE'], errors='coerce').isnull()].copy()
        
        if obs_chunk.empty:
            pbar.update(len(chunk))
            continue

        obs_chunk["person_id"] = obs_chunk["PATIENT"].map(patient_id_map)
        obs_chunk["visit_occurrence_id"] = obs_chunk["ENCOUNTER"].map(visit_id_map)
        
        obs_chunk["observation_id"] = range(obs_id_counter, obs_id_counter + len(obs_chunk))
        obs_id_counter += len(obs_chunk)

        observation = pd.DataFrame({
            "observation_id": obs_chunk["observation_id"],
            "person_id": obs_chunk["person_id"],
            "observation_concept_id": obs_chunk["CODE"].map(snomed_map).fillna(0).astype(int),
            "observation_date": pd.to_datetime(obs_chunk["DATE"]).dt.date,
            "observation_datetime": pd.to_datetime(obs_chunk["DATE"]),
            "observation_type_concept_id": 32817,
            "value_as_string": obs_chunk["VALUE"].astype(str).str.slice(0, 60),  # Truncate to 60 chars
            "observation_source_value": obs_chunk["CODE"].astype(str).str.slice(0, 50),
            "visit_occurrence_id": obs_chunk["visit_occurrence_id"]
        }).dropna(subset=["person_id"])

        observation.to_sql("observation", engine, schema=CDM_SCHEMA, if_exists="append", index=False, chunksize=SQL_CHUNKSIZE)
        pbar.update(len(chunk))
        del obs_chunk, observation
        gc.collect()

print("\n✅ Synthea → OMOP load complete")