from pathlib import Path

from bioctoomop.sentence_splitter import apply_sentence_splitting

from bioc import biocjson

# -----------------------------

# CONFIGURATION

# -----------------------------

FILE_ROOT = "/home/msztr1/Projects/FAIRClinical_NLP_Pipeline/Original"



FILE_TYPE_MAP = {

   "pdf": "PDF",

   "jpg": "Image", "jpeg": "Image", "png": "Image",

   "tif": "Image", "tiff": "Image", "gif": "Image",

   "doc": "Word/Text", "docx": "Word/Text", "rtf": "Word/Text",

   "txt": "Word/Text", "odt": "Word/Text",

   "ppt": "Presentation", "pptx": "Presentation", "odp": "Presentation",

}



def parse_bioc_file(bioc_path: Path, is_supplementary=False):

   """

   One BioC file → one OMOP NOTE.

   Passages are assumed sentence-level.

   """

   if is_supplementary:

     with open(bioc_path, "r", encoding="utf-8") as f:

       collection = biocjson.load(f)

   else:

     return None

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

           "section_type": passage.infons.get("section_type") if not is_supplementary else "supplementary material section",

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



def scan_and_summarise(root_path):

   stats = {}

   total_processed = 0

   

   root = Path(root_path)

   print(f"Scanning for JSON files in: {root_path}...\n")



   # 1. Iterate through all json files recursively

   for json_file in root.rglob("*.json"):
     if json_file.parent.name != "Processed":
       continue

     

     # Ignore "_tables.json" files

     if json_file.name.endswith("_tables.json"):
       continue



     parsed = parse_bioc_file(json_file, is_supplementary=True)

     if not parsed:
       continue



     # 2. Identify file type by removing "_bioc.json"

     # We strip the suffix to find the "original" filename and extension

     original_name = json_file.name.replace("_bioc.json", "")

     

     # Extract the extension from the remaining name (e.g., "supp.pdf" -> "pdf")

     ext = original_name.split(".")[-1].lower() if "." in original_name else "no_ext"

     

     # Categorize based on the map

     file_type = FILE_TYPE_MAP.get(ext, "Other/Unknown")

     

     # Update statistics

     stats[file_type] = stats.get(file_type, 0) + 1

     total_processed += 1



   # 3. Gather stats and print

   print("--- SUPPLEMENTARY FILE TYPE SUMMARY ---")

   if not stats:

     print("No matching files found.")

   else:

     # Sort by count descending

     for ftype, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):

       print(f"{ftype:15}: {count}")

   

   print("-" * 39)

   print(f"Total Files Analyzed: {total_processed}")



if __name__ == "__main__":

   scan_and_summarise(FILE_ROOT)