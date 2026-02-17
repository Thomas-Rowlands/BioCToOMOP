from bioc import biocjson
from pathlib import Path

from bioctoomop.BioC_CRF_Extractor import extract_crf
from bioctoomop.sentence_splitter import apply_sentence_splitting


def parse_bioc_file(bioc_path: Path):
    """
    One BioC file → one OMOP NOTE.
    Passages are assumed sentence-level.
    """
    # with open(bioc_path, "r", encoding="utf-8") as f:
    #     collection = biocjson.load(f)

    collection = extract_crf(bioc_path)
    if not collection:
        return None
    # Apply sentence splitting if no sentences exist
    collection = apply_sentence_splitting(collection)

    document = collection.documents[0]

    note_text_parts = []
    sentences = []

    sentence_id = 0

    pmc_id = ""
    if "XX" in str(bioc_path.parent.name):
        pmc_id = str(bioc_path.name).replace(".json", "")
    else:
        pmc_id = str(bioc_path.parent.name).replace("_supplementary", "")
    file_name = str(bioc_path.name)

    for passage in document.passages:
        for sentence in passage.sentences:
            text = passage.text or ""
            start_offset = sentence.offset
            end_offset = start_offset + len(text)

            sentences.append(
                {
                    "sentence_id": sentence_id,
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                    "text": text,
                    "section_type": passage.infons.get("section_type"),
                }
            )

            note_text_parts.append(sentence.text)
            sentence_id += 1

    note_text = "".join(note_text_parts)

    return {
        "pmc_id": pmc_id,
        "note_source_value": f"{pmc_id}::{file_name}"[:50],
        "note_text": note_text,
        "sentences": sentences,
        "note_date": collection.date
    }
