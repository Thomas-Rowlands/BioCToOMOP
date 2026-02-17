import psycopg
from psycopg.rows import dict_row
from typing import List, Dict, Any

class ClinicalRouter:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn
        # Map OMOP Domains to clinical tables
        self.TABLE_MAP = {
            'Condition': 'condition_occurrence',
            'Procedure': 'procedure_occurrence',
            'Measurement': 'measurement',
            'Observation': 'observation',
            'Drug': 'drug_exposure',
            'Device': 'device_exposure'
        }

    def get_domain_mappings(self, snomed_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """Finds the Standard Concept and Domain for a list of SNOMED codes."""
        if not snomed_codes:
            return {}

        sql = """
        SELECT 
            source.concept_code AS snomed_code,
            target.concept_id AS standard_concept_id,
            target.domain_id
        FROM concept source
        LEFT JOIN concept_relationship cr ON source.concept_id = cr.concept_id_1 
            AND cr.relationship_id = 'Maps to' AND cr.invalid_reason IS NULL
        LEFT JOIN concept target ON COALESCE(cr.concept_id_2, source.concept_id) = target.concept_id
        WHERE source.concept_code = ANY(%s) AND source.vocabulary_id = 'SNOMED'
        """
        
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (list(set(snomed_codes)),))
            return {row['snomed_code']: row for row in cur.fetchall()}