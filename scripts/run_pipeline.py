from pathlib import Path
from medcat.cat import CAT

from bioctoomop.bioc_parser import parse_bioc_file
from bioctoomop.medcat_runner import run_medcat
from bioctoomop.omop_note import make_note
from bioctoomop.omop_note_nlp import entities_to_note_nlp


def main():
    input_root = Path("input_bioc")
    note_id = 1

    cat = CAT.load_model_pack("models/v2_Snomed2025_MIMIC_IV_bbe806e192df009f.zip")

    all_notes = []
    all_note_nlp = []

    for pmc_dir in input_root.iterdir():
        if not pmc_dir.is_dir():
            continue

        pmc_id = pmc_dir.name

        for bioc_file in pmc_dir.glob("*.xml"):
            parsed = parse_bioc_file(bioc_file, pmc_id)
            note = make_note(note_id, parsed)

            entities = run_medcat(
                cat,
                note_id,
                parsed["sentences"],
            )

            sentences_by_id = {
                s["sentence_id"]: s for s in parsed["sentences"]
            }

            note_nlp = entities_to_note_nlp(
                entities,
                sentences_by_id,
            )

            all_notes.append(note)
            all_note_nlp.extend(note_nlp)

            note_id += 1

    # Write CSVs / Parquet / direct DB load here


if __name__ == "__main__":
    main()
