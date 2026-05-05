import os

from tqdm import tqdm


class MarkdownProcessor(object):
    def __init__(self, md_dir, output_dir):
        self.md_dir = md_dir
        self.output_dir = output_dir
        
        self.noise_list = [
            "# AUTHOR INFORMATION",
            "# Supporting Information",
            "# A. Supplementary data",
            "# Appendix A. Supplementary data",
            "# Appendix A. Supplementary material",
            "# Supplementary materials",
            "# ASSOCIATED CONTENT",
            "# ACKNOWLEDGMENTS",
            "# Acknowledgements",
            "# Conflict of Interest",
            "# Author Contributions",
            "# Data Availability Statement",
            "# Data Availability",
            "# ORCID",
            "# References",
            "# REFERENCES",
            "# Notes and references",
            "# Funding",
            "# Declaration of competing interest",
        ]
        
        # 预处理为标准化集合（小写+去空格）
        self.noise_set = {s.strip().lower() for s in self.noise_list}
        
    
    def process_md(self, md_file_name, output_dir): 
        # create mineru directory
        os.makedirs(output_dir, exist_ok=True)
        
        # create mineru file path
        name_without_suff = os.path.splitext(os.path.basename(md_file_name))[0]
        output_path = os.path.join(output_dir, f"{name_without_suff}_cleaned.md")
        
        with open(md_file_name, "r", encoding="utf-8") as infile, \
            open(output_path, "w", encoding="utf-8") as outfile:
        
            for line in infile:
                # 标准化当前行并匹配
                if line.strip().lower() in self.noise_set:
                    break
                
                outfile.write(line)        
        return output_path
    
    def process_md_dir(self):
        cleaned_md_paths = []
        for file_name in tqdm(os.listdir(self.md_dir), desc="Processing MD files"):
            if file_name.endswith(".md"):
                md_file_path = os.path.join(self.md_dir, file_name)
                cleaned_md_file_path = self.process_md(md_file_path, self.output_dir)
                cleaned_md_paths.append(cleaned_md_file_path)
                
        return cleaned_md_paths