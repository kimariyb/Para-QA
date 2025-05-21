from parser.processor import PDFProcessor

if __name__ == '__main__':
    pdf_processor = PDFProcessor(
        pdf_dir='./data', 
        output_dir='./mineru', 
        image_subdir='images', 
        simple_output=True
    )
    pdf_processor.process_pdf_dir()