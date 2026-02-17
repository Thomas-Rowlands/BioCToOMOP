import json

def entities_to_note_nlp(entities, sentences_by_id, start_note_nlp_id, snomed_to_omop):
    rows = []
    note_nlp_id = start_note_nlp_id

    for e in entities:
        sentence = sentences_by_id[e["sentence_id"]]

        rows.append(
            {
                "note_nlp_id": note_nlp_id,
                "note_id": e["note_id"],
                # NOTE-local character offset
                "offset": e["start_offset"],
                # OMOP expects a snippet, not necessarily the exact span
                "snippet": trim_snippet(sentence["text"]),
                "lexical_variant": e["lexical_variant"],
                "note_nlp_concept_id": snomed_to_omop.get(
                    str(e["snomed_id"]),
                    0,  # OMOP convention: unmapped
                ),
                # Source concept (SNOMED from MedCAT)
                "note_nlp_source_concept_id": e["snomed_id"],
                # Provenance
                "nlp_system": e["nlp_system"],
                # MedCAT-specific signals live here
                "term_modifiers": json.dumps(
                    {
                        "entity_id": e["entity_id"],
                        "pretty_name": e.get("pretty_name"),
                        "accuracy": e.get("accuracy"),
                        "context_similarity": e.get("context_similarity"),
                        "negated": e.get("negated"),
                        "temporality": e.get("temporality"),
                        "experiencer": e.get("experiencer"),
                    }
                ),
            }
        )

        note_nlp_id += 1

    return rows, note_nlp_id

def trim_snippet(snippet, max_length=250):
    if len(snippet) <= max_length:
        return snippet
    return snippet[:max_length]
