import os

from tqdm import tqdm

from magic_pdf.data.data_reader_writer import FileBasedDataReader, FileBasedDataWriter
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

from langchain.text_splitter import MarkdownHeaderTextSplitter


class PDFProcessor(object):
    def __init__(self, pdf_dir, output_dir, image_subdir, simple_output=True):
        self.pdf_dir = pdf_dir
        self.output_dir = output_dir
        self.image_subdir = image_subdir
        self.simple_output = simple_output
    
    def process_pdf_dir(self):
        r"""
        Process all PDF files in a directory and extract text and images.
        """
        md_file_paths = []
        for file_name in tqdm(os.listdir(self.pdf_dir), desc="Processing PDF files"):
            if file_name.endswith(".pdf"):
                pdf_file_path = os.path.join(self.pdf_dir, file_name)
                md_file_path = self.process_pdf(pdf_file_path, self.output_dir, self.image_subdir, self.simple_output)
                md_file_paths.append(md_file_path)
                
        return md_file_paths
    

    def process_pdf(self, pdf_file_name, output_dir, image_subdir, simple_output=True):
        r"""
        Process a PDF file and extract text and images.
        
        Parameters
        ----------
        pdf_file_name : str
            The path of the PDF file to be processed.
        output_dir : str
            The directory to store the extracted text and images.
        image_subdir : str
            The subdirectory to store the extracted images.
        simple_output : bool, optional
            Whether to output the extracted text in a simple format. Default is True.
        
        Returns
        -------
        str
            The path of the generated markdown file.
        """
        # 获取不带后缀的文件名
        name_without_suff = os.path.splitext(os.path.basename(pdf_file_name))[0]
   
        # 创建输出子目录名
        output_subdir = f"{name_without_suff}"

        # 构建图片目录和 markdown 目录的路径
        local_image_dir = os.path.join(output_dir, output_subdir, image_subdir)
        local_md_dir = os.path.join(output_dir, output_subdir)

        # 创建必要的目录
        os.makedirs(local_image_dir, exist_ok=True)
        os.makedirs(local_md_dir, exist_ok=True)
        
        # 构建 markdown 文件的完整路径
        md_file_path = os.path.join(os.getcwd(), local_md_dir, f"{name_without_suff}.md")
        abs_md_file_path = os.path.abspath(md_file_path)

        # 读取 PDF 文件
        image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)
        # 创建文件读取器并读取 PDF 文件
        reader1 = FileBasedDataReader("")
        pdf_bytes = reader1.read(pdf_file_name)
        
        # 创建数据集对象
        ds = PymuDocDataset(pdf_bytes)
        # 根据 PDF 类型选择处理方式
        if ds.classify() == SupportedPdfParseMethod.OCR:
            # 使用 OCR 模式处理
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            # 使用文本模式处理
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
        
        if simple_output: 
            # 简单输出模式：只输出 markdown 和内容列表
            pipe_result.dump_md(md_writer, f"{name_without_suff}.md", os.path.basename(local_image_dir))
            pipe_result.dump_content_list(md_writer, f"{name_without_suff}_content_list.json",
                                        os.path.basename(local_image_dir))
            return abs_md_file_path
        else:
            # 完整输出模式：输出所有内容
            pipe_result.dump_md(md_writer, f"{name_without_suff}.md", os.path.basename(local_image_dir))
            pipe_result.dump_content_list(md_writer, f"{name_without_suff}_content_list.json",
                                            os.path.basename(local_image_dir))
        
        # 生成可视化文件
        infer_result.draw_model(os.path.join(local_md_dir, f"{name_without_suff}_model.pdf"))
        pipe_result.draw_layout(os.path.join(local_md_dir, f"{name_without_suff}_layout.pdf"))
        pipe_result.draw_span(os.path.join(local_md_dir, f"{name_without_suff}_spans.pdf"))

        return abs_md_file_path
    

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
        # create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # create output file path
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