NOTE_SQL = """
INSERT INTO omop_cdm.person (
    person_id,
    gender_concept_id,
    year_of_birth,
    race_concept_id,
    ethnicity_concept_id
)
VALUES (
    1,
    0,
    1900,
    0,
    0
);
"""
