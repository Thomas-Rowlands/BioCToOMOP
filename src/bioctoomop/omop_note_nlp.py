import json


def entities_to_note_nlp(entities, sentences_by_id):
    rows = []

    for e in entities:
        sentence = sentences_by_id[e["sentence_id"]]

        rows.append(
            {
                "note_id": e["note_id"],
                "offset": e["start_offset"],
                "snippet": sentence["text"],
                "lexical_variant": e["lexical_variant"],
                "note_nlp_source_concept_id": e["snomed_id"],
                "nlp_system": e["nlp_system"],
                "confidence": e["confidence"],
                "term_modifiers": json.dumps(
                    {
                        "negated": e["negated"],
                        "temporality": e["temporality"],
                        "experiencer": e["experiencer"],
                        "entity_id": e["entity_id"],
                    }
                ),
            }
        )

    return rows
