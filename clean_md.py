from utils.parser import MarkdownProcessor

if __name__ == '__main__':
    md_processor = MarkdownProcessor(
        md_dir='./output', 
        output_dir='./cleaned', 
    )
    md_processor.process_md_dir()