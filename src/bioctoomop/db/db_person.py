NOTE_SQL = """
INSERT INTO omop_cdm.person (
    person_id,
    gender_concept_id,
    year_of_birth,
    race_concept_id,
    ethnicity_concept_id
)
VALUES (
    %(person_id)s,
    %(gender_concept_id)s,
    %(year_of_birth)s,
    %(race_concept_id)s,
    %(ethnicity_concept_id)s
);
"""
