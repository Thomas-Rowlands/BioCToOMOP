from bioc import biocjson, BioCAnnotation, BioCLocation
from pathlib import Path

from bioctoomop.sentence_splitter import apply_sentence_splitting


def write_annotated_bioc(
    input_bioc_path: Path,
    output_bioc_path: Path,
    entities: list,
):
    """
    Writes a copy of the BioC file with MedCAT entity annotations added.
    Assumes entities have NOTE-local offsets.
    """

    with open(input_bioc_path, "r", encoding="utf-8") as f:
        collection = biocjson.load(f)

    collection = apply_sentence_splitting(collection)
    document = collection.documents[0]

    for e in entities:
        ann = BioCAnnotation()
        ann.id = f"T{e['entity_id']}"
        ann.text = e["lexical_variant"]

        ann.add_location(
            BioCLocation(
                offset=e["start_offset"],
                length=e["end_offset"] - e["start_offset"],
            )
        )

        # ---- infons: explicit, flat, MedCAT-faithful ----
        ann.infons["type"] = "MedCAT"
        ann.infons["snomed_id"] = str(e["snomed_id"])
        ann.infons["pretty_name"] = e.get("pretty_name")

        # MedCAT confidence signals (do NOT overinterpret)
        ann.infons["accuracy"] = str(e.get("accuracy"))
        ann.infons["context_similarity"] = str(e.get("context_similarity"))

        # Meta-annotations (may be None)
        ann.infons["negated"] = str(e.get("negated"))
        ann.infons["temporality"] = str(e.get("temporality"))
        ann.infons["experiencer"] = str(e.get("experiencer"))

        # Provenance
        ann.infons["nlp_system"] = e["nlp_system"]

        document.add_annotation(ann)

    output_bioc_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_bioc_path, "w", encoding="utf-8") as f:
        biocjson.dump(collection, f)
