from pathlib import Path
from medcat.cat import CAT
from tqdm import tqdm
import os

from bioctoomop.bioc_parser import parse_bioc_file
from bioctoomop.db_snomed_map import load_snomed_to_omop_map
from bioctoomop.medcat_runner import run_medcat_single_note
from bioctoomop.omop_note import make_note
from bioctoomop.omop_note_nlp import entities_to_note_nlp
from bioctoomop.db import get_conn
from bioctoomop.db_insert import insert_notes, insert_note_nlp
from bioctoomop.db_ids import get_max_ids
from bioctoomop.bioc_serialize import write_annotated_bioc


NOTE_BATCH_SIZE = 50          # notes per MedCAT batch
NOTE_NLP_BATCH_SIZE = 5000     # rows per DB insert


def main():
    input_root = Path("/mnt/sda2/Projects/FAIRClinical_Docs")
    output_bioc_root = Path("/mnt/sda2/Projects/FAIRClinical_Docs_Annotated")

    cat = CAT.load_model_pack(
        "models/v2_Snomed2025_MIMIC_IV_bbe806e192df009f.zip"
    )

    with get_conn(
        host="localhost",
        port=5432,
        dbname="postgres",
        user="postgres",
        password="postgres",
    ) as conn:

        # ---- ID bootstrap ----
        max_note_id, max_note_nlp_id = get_max_ids(conn)
        next_note_id = max_note_id + 1
        next_note_nlp_id = max_note_nlp_id + 1

        snomed_to_omop = load_snomed_to_omop_map(conn)

        bioc_files = [p for p in input_root.rglob("*.json") if not p.is_dir()]

        note_buffer = []
        note_texts = []              # [(note_id, full_text)]
        note_sentences = {}          # note_id -> sentences
        note_files = {}              # note_id -> (bioc_file, pmc_id)
        note_nlp_buffer = []

        for bioc_file in tqdm(bioc_files, desc="Parsing BioC files"):
            pmc_id = bioc_file.parent.name

            if any(
                ["Raw" in x.name or "Processed" in x.name for x in bioc_file.parents]
            ):
                pmc_id = pmc_id.replace("_supplementary", "")
            else:
                pmc_id = bioc_file.name.replace(".json", "")

            parsed = parse_bioc_file(bioc_file, pmc_id)

            note_id = next_note_id
            next_note_id += 1

            # ---- NOTE ----
            note = make_note(note_id, parsed)
            note_buffer.append(note)

            # ---- Prepare MedCAT input ----
            full_text = " ".join(s["text"] for s in parsed["sentences"])
            note_texts.append((str(note_id), full_text))
            note_sentences[note_id] = parsed["sentences"]
            note_files[note_id] = (bioc_file, pmc_id)

            # ---- Process batch ----
            if len(note_texts) >= NOTE_BATCH_SIZE:
                next_note_nlp_id = process_medcat_batch(
                    cat,
                    conn,
                    note_buffer,
                    note_texts,
                    note_sentences,
                    note_files,
                    note_nlp_buffer,
                    next_note_nlp_id,
                    snomed_to_omop,
                    output_bioc_root,
                )

                note_buffer.clear()
                note_texts.clear()
                note_sentences.clear()
                note_files.clear()

        # ---- Final batch ----
        if note_texts:
            process_medcat_batch(
                cat,
                conn,
                note_buffer,
                note_texts,
                note_sentences,
                note_files,
                note_nlp_buffer,
                next_note_nlp_id,
                snomed_to_omop,
                output_bioc_root,
            )

        # ---- Final NOTE_NLP flush ----
        if note_nlp_buffer:
            insert_note_nlp(conn, note_nlp_buffer)


def process_medcat_batch(
    cat,
    conn,
    note_buffer,
    note_texts,
    note_sentences,
    note_files,
    note_nlp_buffer,
    next_note_nlp_id,
    snomed_to_omop,
    output_bioc_root,
):
    # ---- Insert NOTES ----
    insert_notes(conn, note_buffer)

    # ---- Run MedCAT in parallel ----
    results = cat.get_entities_multi_texts(
        texts=note_texts,
        only_cui=False,
        n_process=1,
        batch_size_chars=200_000,
    )

    for note_id_str, medcat_result in results:
        note_id = int(note_id_str)
        sentences = note_sentences[note_id]

        entities = run_medcat_single_note(
            note_id,
            sentences,
            medcat_result,
        )

        # ---- Write annotated BioC ----
        bioc_file, pmc_id = note_files[note_id]
        output_bioc_path = (
            output_bioc_root
            / pmc_id
            / f"{bioc_file.stem}.annotated.json"
        )

        write_annotated_bioc(
            input_bioc_path=bioc_file,
            output_bioc_path=output_bioc_path,
            entities=entities,
        )

        # ---- NOTE_NLP ----
        sentences_by_id = {s["sentence_id"]: s for s in sentences}

        note_nlp_rows, next_note_nlp_id = entities_to_note_nlp(
            entities,
            sentences_by_id,
            next_note_nlp_id,
            snomed_to_omop,
        )

        note_nlp_buffer.extend(note_nlp_rows)

        if len(note_nlp_buffer) >= NOTE_NLP_BATCH_SIZE:
            insert_note_nlp(conn, note_nlp_buffer)
            note_nlp_buffer.clear()

    return next_note_nlp_id


if __name__ == "__main__":
    main()
