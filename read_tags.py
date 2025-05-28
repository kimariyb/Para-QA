import os
import pathlib
import pandas as pd

from tqdm import tqdm


def parse_data(tags_file):
    """
    This function reads the tags file and returns a dictionary of tags.

    title: Hyperpolarization of Nitrile Compounds Using Signal Amplification by Reversible Exchange
    tags: ['SABRE', 'nitrile compounds', 'hyperpolarization', 'parahydrogen', 'NMR', 'polarization transfer', 'magnetic fields']
    """
    data = {
        "title": "",
        "tags": []
    }
    
    with open(tags_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("title:"):
                data["title"] = line.strip().split(":")[1].strip()
            elif line.startswith("tags:"):
                tags_str = line.split(":")[1].strip()
                try:
                    data["tags"] = eval(tags_str)
                except:
                    data["tags"] = tags_str.split(", ")
    return data


if __name__ == "__main__":
    tags_folder = "D:\\project\\SABRE-RAG\\tags"
    
    paper_info = {
        "filename": "",
        "title": "",
        "tags": []
    }
    
    paper_info_list = []
    
    for file in tqdm(os.listdir(tags_folder)):
        if file.endswith(".txt"):
            data = parse_data(os.path.join(tags_folder, file))
            
            paper_info["filename"] = pathlib.Path(file).name
            paper_info["title"] = data["title"]
            paper_info["tags"] = data["tags"]
            
            paper_info_list.append(paper_info.copy())

    # pandas
    df = pd.DataFrame(paper_info_list)
    df.to_csv("tagged_paper_info.csv", index=False)