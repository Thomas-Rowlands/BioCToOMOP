import pandas as pd
from bioc import biocjson

def extract_to_csv(bioc_file, output_csv):
    """
    Extracts annotations into a flat format for WhiteRabbit/Carrot.
    """
    data = []
    with open(bioc_file, 'r') as f:
        bioc_collection = biocjson.load(f)
        for doc in bioc_collection.documents:
            for passage in doc.passages:
                for ann in passage.annotations:
                    # Capture the SNOMED ID and any context
                    snomed_id = ann.infons.get('snomed_id')
                    if snomed_id:
                        data.append({
                            'person_id': doc.id, # Needed for OMOP linkage
                            'snomed_id': snomed_id,
                            'term_text': ann.text,
                            'negation': ann.infons.get('negation', 'present')
                        })
    
    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False)
    print(f"Created source file: {output_csv}")

if __name__ == "__main__":
    bioc_file = '/path/to/your/file.json'
    extract_to_csv(bioc_file, 'source_annotations.csv')