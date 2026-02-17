from datetime import date

LITERATURE_PERSON_ID = 1

def make_person(person_id: int, gender: str, year_of_birth: str, race: str, ethnicity: str):
    return {
        "person_id": person_id,
        "gender_concept_id": get_gender_concept_id(gender),  # Default to "Unknown"
        "year_of_birth": int(year_of_birth) if year_of_birth.isdigit() else random_year_of_birth(),  # Default to "Unknown"
        "race_concept_id": get_race_concept_id(race),  # Default to "Unknown"
        "ethnicity_concept_id": get_ethnicity_concept_id(ethnicity)  # Default to "Ethnic group unknown"
        }

def random_year_of_birth():
    # Generate a random age between 0 and 100
    import random
    return random.randint(18, 90)

def get_gender_concept_id(gender: str) -> int:
    return 8551

def get_race_concept_id(race: str) -> int:
    return 35820554

def get_ethnicity_concept_id(ethnicity: str) -> int:
    return 759814
