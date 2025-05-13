import os
import re
import requests

from PyPDF2 import DocumentInformation, PdfReader

from magic_pdf.data.data_reader_writer import FileBasedDataReader, FileBasedDataWriter
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod


class PDFProcessor(object):
    def __init__(self):
        self.noise_patterns = [
            r'(?is)^\s*(references|acknowledgements|author information|associated content|supporting information)\b[.:]?.*?(?=^\s*\b\w+|$)',

            r'(?i)\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',  
            r'(?i)\b(http|ftp|https)://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'(?i)\b(www\.)\S+\b',
            
            r'$?\d{4}$?[\s-]?(?:[a-zA-Z]+[\s-]?){0,3}\d*\.?',  # 形如 (2023a) / 2024: 的引用
            r'(?i)\b(?:fig|figure)\s*[\d.]+[a-zA-Z]?(?:[:-].+)?\.?',  
            
            r'(?i)^\s*(?:doi|publisher)\s*:.+$',
            r'\*+\s*Conflict of Interest\s*\*+.*',
        ]
        
        self.doi_patterns = [
            r'doi[\s\.\:]{0,2}(10\.\d{4}[\d\:\.\-\/a-z]+)(?:[\s\n\"<]|$)',
            r'(10\.\d{4}[\d\:\.\-\/a-z]+)(?:[\s\n\"<]|$)',
            r'(10\.\d{4}[\:\.\-\/a-z]+[\:\.\-\d]+)(?:[\s\na-z\"<]|$)',
            r'https?://[ -~]*doi[ -~]*/(10\.\d{4,9}/[-._;()/:a-z0-9]+)(?:[\s\n\"<]|$)'
            r'^(10\.\d{4,9}/[-._;()/:a-z0-9]+)$'
        ]

    @staticmethod
    def get_pdf_info(file) -> None | DocumentInformation:
        r"""
        Get the information of a pdf file.
        
        Parameters
        ----------
        file : str
            The file path of the pdf file.
        
        Returns
        -------
        dict
            The information of the pdf file.
        """
        try:
            pdf = PdfReader(file, strict=False)
        except Exception as e:
            print(f"It was not possible to open the file with PyPDF2. Is this a valid pdf file?: {e}")
            return None
        
        try:
            info = pdf.metadata
        except Exception as e:
            print(f"An error occurred when retrieving the pdf info with PyPDF2: {e}")
            return None
        
        return info
    
