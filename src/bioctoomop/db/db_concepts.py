import psycopg
from psycopg.rows import dict_row
from functools import lru_cache
from typing import List, Dict, Any, Optional

class OMOPMapper:
    def __init__(self, conn_info: str, schema: str = "public"):
        self.conn_info = conn_info
        self.schema = schema
        self.conn = None
        # Maps Domain to CDM table
        self.DOMAIN_MAP = {
            'Condition': 'condition_occurrence',
            'Procedure': 'procedure_occurrence',
            'Measurement': 'measurement',
            'Observation': 'observation',
            'Drug': 'drug_exposure',
            'Device': 'device_exposure',
            'Specimen': 'specimen',
            'Gender': 'person',
            'Race': 'person'
        }

    def __enter__(self):
        """Allows use of 'with OMOPMapper(...) as mapper:'"""
        self.conn = psycopg.connect(self.conn_info, row_factory=dict_row)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    @lru_cache(maxsize=1024)
    def get_single_routing(self, snomed_code: str) -> Optional[Dict[str, Any]]:
        """Cached lookup for individual codes (good for recurring terms)."""
        results = self.get_batch_routing([snomed_code])
        return results.get(snomed_code)

    def get_batch_routing(self, snomed_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        High-performance batch lookup. 
        Returns a dict keyed by the input SNOMED code.
        """
        if not snomed_codes:
            return {}

        sql = f"""
        SELECT 
            source.concept_code AS original_code,
            target.concept_id AS standard_concept_id,
            target.domain_id,
            target.concept_name
        FROM {self.schema}.concept source
        LEFT JOIN {self.schema}.concept_relationship cr 
            ON source.concept_id = cr.concept_id_1 
            AND cr.relationship_id = 'Maps to'
            AND cr.invalid_reason IS NULL
        LEFT JOIN {self.schema}.concept target 
            ON COALESCE(cr.concept_id_2, source.concept_id) = target.concept_id
        WHERE source.concept_code = ANY(%s) 
          AND source.vocabulary_id = 'SNOMED';
        """

        with self.conn.cursor() as cur:
            cur.execute(sql, (list(set(snomed_codes)),))
            rows = cur.fetchall()
            
            mapping_results = {}
            for row in rows:
                row['target_table'] = self.DOMAIN_MAP.get(row['domain_id'], 'observation')
                mapping_results[row['original_code']] = row
                
            return mapping_results

# --- How to use this in your project ---
if __name__ == "__main__":
    DB_URI = "postgresql://postgres:password@localhost:5432/my_omop"
    
    # 1. Use a context manager to ensure the connection closes
    with OMOPMapper(DB_URI) as mapper:
        # 2. Batch process your MedCAT output for speed
        medcat_codes = ['44054006', '22298006', 'invalid_code']
        routing_table = mapper.get_batch_routing(medcat_codes)
        
        for code in medcat_codes:
            info = routing_table.get(code)
            if info:
                print(f"Code {code} -> Store in {info['target_table']}")
            else:
                print(f"Code {code} -> Not found in OMOP Vocabulary")