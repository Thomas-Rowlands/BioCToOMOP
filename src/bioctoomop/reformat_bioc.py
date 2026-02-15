from bioc import biocjson
from pathlib import Path

def move_doc_annotations_to_passages(in_json, out_json):
    try:
        with open(in_json, "r", encoding="utf-8") as f:
            collection = biocjson.load(f)
    except Exception as e:
        print(f"Error loading {in_json}: {e}")
        return

    for doc in collection.documents:
        if not doc.annotations:
            continue

        passages = doc.passages

        remaining_doc_annotations = []

        for ann in doc.annotations:
            # BioC annotations can have multiple locations,
            # but most NER-style ones have exactly one
            moved = False
            for loc in ann.locations:
                ann_start = loc.offset
                ann_end = loc.offset + loc.length

                for passage in passages:
                    p_start = passage.offset
                    p_end = passage.offset + len(passage.text)

                    if ann_start >= p_start and ann_end <= p_end:
                        passage.annotations.append(ann)
                        moved = True
                        break

                if moved:
                    break

            if not moved:
                # Keep it at document level if no passage matched
                remaining_doc_annotations.append(ann)

        doc.annotations = remaining_doc_annotations

    with open(out_json, "w", encoding="utf-8") as f:
        biocjson.dump(collection, f)


def remove_annotations(in_json, out_json):
    try:
        with open(in_json, "r", encoding="utf-8") as f:
            collection = biocjson.load(f)
    except Exception as e:
        print(f"Error loading {in_json}: {e}")
        return

    for doc in collection.documents:
        doc.annotations = []
        for passage in doc.passages:
            passage.annotations = []

    # if folders don't exist, create them
    out_json.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_json, "w", encoding="utf-8") as f:
        biocjson.dump(collection, f)

if __name__ == "__main__":
    for in_doc in Path("/mnt/sda2/Projects/FAIRClinical_Docs_Annotated/").rglob("*.json"):
        # out_doc = in_doc.parent / f"{in_doc.stem}_passage.json"
        # move_doc_annotations_to_passages(
        #     in_doc,
        #     out_doc
        # )
        out_doc = Path("/mnt/sda2/Projects/FAIRClinical_NLP_Data") / in_doc.parent.name / f"{in_doc.stem}.json"
        remove_annotations(
            in_doc,
            out_doc
        )