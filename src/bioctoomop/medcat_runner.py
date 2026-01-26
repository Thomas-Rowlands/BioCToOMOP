from typing import List, Dict
from medcat.cat import CAT


def run_medcat(cat: CAT, note_id: int, sentences: List[Dict]):
    """
    Runs MedCAT sentence-by-sentence.
    Returns flat list of entity dicts.
    """
    entities = []
    entity_id = 0

    for sent in sentences:
        doc = cat(sent["text"])
        for ent in doc.ents:
            entities.append(
                {
                    "entity_id": entity_id,
                    "note_id": note_id,
                    "sentence_id": sent["sentence_id"],
                    "start_offset": sent["start_offset"] + ent.start_char,
                    "end_offset": sent["start_offset"] + ent.end_char,
                    "lexical_variant": ent.text,
                    "snomed_id": ent._.cui,
                    "confidence": ent._.confidence,
                    "negated": ent._.negex,
                    "temporality": ent._.temporal,
                    "experiencer": ent._.experiencer,
                    "nlp_system": f"MedCAT {cat.config.version}",
                }
            )
            entity_id += 1

    return entities
