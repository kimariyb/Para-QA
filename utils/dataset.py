"""
This file contains the implementation of creating 
the QA dataset for the SABRE-RAG model.
"""
import re
import pymupdf

from typing import List, Tuple


class PDFProcessor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.noise_patterns = [
            r'\bReferences\b.*',  # 参考文献区块
            r'\bAcknowledgements\b.*',  # 附录
            r'\bAuthor Information\b.*',  # 作者信息
            r'\bAssociated Content\b.*',  # 附录 ASSOCIATED CONTENT
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 邮箱
            r'$?\d{4}$?[\s\-]?(?:[a-zA-Z]+\s?){1,3}\d*\.',  # 引用标记
            r'Fig\.?\s*\d+[.:]?',  # 图表标注
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\$\$,]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'  # URL
        ]
        
    def extract_structured_text(self) -> List[Tuple]:
        """基于版面分析提取带结构的文本"""
        with pymupdf.open(self.pdf_path) as pdf:
            blocks = []
            for page in pdf.pages:
                # 提取带坐标的文本块
                words = page.extract_words(x_tolerance=2, y_tolerance=1)
                current_block = []
                prev_y = None
                
                for word in words:
                    # 基于垂直坐标合并同行文本
                    if prev_y is None or abs(word['top'] - prev_y) < 3:
                        current_block.append(word['text'])
                    else:
                        blocks.append((' '.join(current_block), prev_y))
                        current_block = [word['text']]
                    prev_y = word['top']
                
                if current_block:
                    blocks.append((' '.join(current_block), prev_y))
            return blocks

    def filter_sections(self, blocks: List[Tuple], target_sections: List[str]) -> str:
        """智能识别目标章节"""
        section_keywords = {
            'methods': ['method', 'experiment', 'implementation', 'procedure'],
            'results': ['result', 'finding', 'observation', 'data'],
            'discussion': ['discussion', 'conclusion', 'implication', 'limitation']
        }
        
        # 定位章节起始点
        section_boundaries = {}
        current_section = None
        for idx, (text, _) in enumerate(blocks):
            text_lower = text.lower()
            for sec, keywords in section_keywords.items():
                if any(kw in text_lower for kw in keywords) and len(text.split()) < 8:
                    current_section = sec
                    section_boundaries.setdefault(sec, [idx, idx])
                elif current_section:
                    section_boundaries[current_section][1] = idx
        
        # 提取目标内容
        filtered_text = []
        for sec in target_sections:
            if sec in section_boundaries:
                start, end = section_boundaries[sec]
                filtered_text.extend([b[0] for b in blocks[start:end+1]])
        
        return self._clean_text(' '.join(filtered_text))

    def _clean_text(self, text: str) -> str:
        """多层次文本清洗"""
        # 移除噪声模式
        for pattern in self.noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # 处理分栏排版
        text = re.sub(r'-\n(\w+)', r'\1', text)  # 修复换行连字符
        text = re.sub(r'\n{2,}', '\n', text)    # 合并多余空行
        
        return text.strip()