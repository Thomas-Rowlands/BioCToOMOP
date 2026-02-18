from pathlib import Path
import sys
from bioc import BioCCollection, BioCPassage, biocjson
import logging

logger = logging.getLogger("BioC CRF Extractor")

def extract_crf(article_file: Path) -> BioCCollection | None:
    """
    Extracts and returns a BioCCollection containing only the CRF (Case Report Form) passages
    from the given BioC-formatted article file. The function searches for passages whose type
    includes "title" and whose text contains either "case presentation" or "case report".
    If such passages are found, they are collected into a new BioCCollection with recalculated
    passage offsets. If no matching passages are found or the file cannot be opened, None is returned.
    Args:
        article_file (Path): Path to the BioC-formatted article file to process.
    Returns:
        BioCCollection | None: A BioCCollection containing only the matching CRF passages,
        or None if no matching passages are found or the file cannot be opened.
    """
    article_bioc: BioCCollection = None
    try:
        with article_file.open(encoding="utf-8") as f_in:
            article_bioc = biocjson.load(f_in)
    except:
        logger.error(f"Error attempting to open: {article_file.name}, skipping")
        return None
    
    # copy embedded CRF passages ready to form a new BioCCollection/file
    matching_passages: list[tuple[int, BioCPassage]] = []
    try:
        for idx, passage in enumerate(article_bioc.documents[0].passages):
            # check for potential CRF title passages
            if "title" in passage.infons["type"].lower():
                p_text = passage.text.lower()
                if "case presentation" == p_text or "case report" == p_text:
                    matching_passages.append((idx, passage))
            # check for CRF content passages, they must follow on from a previous CRF passage.
            elif "section_type" in passage.infons.keys() and "CASE" == passage.infons["section_type"]:
                if matching_passages and idx == (matching_passages[-1][0] + 1):
                    matching_passages.append((idx, passage))
    except:
        logger.error(f"Error processing passages in: {article_file.name}, skipping")
        return None

    if matching_passages:
        # Set new article passages to be only the matching CRF passages
        article_bioc.documents[0].passages = [p for idx, p in matching_passages]

        # recalculate passage offsets
        offset = 0
        for passage in article_bioc.documents[0].passages:
            passage.offset = offset
            offset += len(passage.text)

        return article_bioc
    else:
        logger.info(f"No matching passages found in {article_file.name}")
        return None
    

def main():
    parent_input_folder = Path(sys.argv[1])
    output_folder = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("Output")

    if not parent_input_folder.exists() or not parent_input_folder.is_dir():
        raise FileExistsError("Please check the input directory exists and is a valid directory")

    if not output_folder.exists():
        output_folder.mkdir(parents=True)
        logger.info("Output path created")

    for article_file in parent_input_folder.rglob("*.json"):
        logger.info(f"Extracting CRF from {article_file.name}")
        extracted_crf: BioCCollection | None = extract_crf(article_file)

        if not extracted_crf:
            continue

        article_set_folder = article_file.parent

        # output to the provided output directory with the _CRF name alteration.
        output_path = output_folder / article_set_folder.name / article_file.name.replace(".json", "_CRF.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f_out:
            biocjson.dump(extracted_crf, f_out, indent=4)


if __name__ == "__main__":
    main()