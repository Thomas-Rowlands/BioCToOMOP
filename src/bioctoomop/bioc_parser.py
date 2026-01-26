from bioc import biocxml
from pathlib import Path


def parse_bioc_file(bioc_path: Path, pmc_id: str):
    """
    One BioC file → one OMOP NOTE.
    Passages are assumed sentence-level.
    """
    with open(bioc_path, "r", encoding="utf-8") as f:
        collection = biocxml.load(f)

    document = collection.documents[0]

    note_text_parts = []
    sentences = []

    cursor = 0
    sentence_id = 0

    for passage in document.passages:
        text = passage.text or ""
        start_offset = cursor
        end_offset = cursor + len(text)

        sentences.append(
            {
                "sentence_id": sentence_id,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "text": text,
                "section_type": passage.infons.get("section_type"),
            }
        )

        note_text_parts.append(text)
        cursor = end_offset
        sentence_id += 1

    note_text = "".join(note_text_parts)

    return {
        "pmc_id": pmc_id,
        "note_source_value": f"{pmc_id}::{bioc_path.stem}",
        "note_text": note_text,
        "sentences": sentences,
    }
