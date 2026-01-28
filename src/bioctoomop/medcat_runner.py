from typing import List, Dict

def run_medcat_single_note(
    note_id: int,
    sentences: List[Dict],
    medcat_result: Dict,
):
    """
    Convert MedCAT NOTE-level output into entity rows,
    preserving sentence mapping and offsets.
    """
    entities = []
    entity_id = 0

    # Build sentence span index
    sentence_spans = [
        (
            s["sentence_id"],
            s["start_offset"],
            s["start_offset"] + len(s["text"]),
        )
        for s in sentences
    ]

    for ent in medcat_result.get("entities", {}).values():
        ent_start = ent["start"]
        ent_end = ent["end"]

        # Find containing sentence
        sentence_id = None
        for sid, s_start, s_end in sentence_spans:
            if s_start <= ent_start < s_end:
                sentence_id = sid
                break

        if sentence_id is None:
            continue

        entities.append(
            {
                "entity_id": entity_id,
                "note_id": note_id,
                "sentence_id": sentence_id,
                "start_offset": ent_start,
                "end_offset": ent_end,
                "lexical_variant": ent.get("detected_name"),
                "pretty_name": ent.get("pretty_name"),
                "snomed_id": int(ent["cui"]),
                "accuracy": ent.get("acc"),
                "context_similarity": ent.get("context_similarity"),
                "negated": ent.get("meta_anns", {}).get("negex"),
                "temporality": ent.get("meta_anns", {}).get("temporality"),
                "experiencer": ent.get("meta_anns", {}).get("experiencer"),
                "nlp_system": "MedCAT",
            }
        )

        entity_id += 1

    return entities
