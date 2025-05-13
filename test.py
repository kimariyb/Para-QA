import os

from parser.processor import PDFProcessor


if __name__ == '__main__':
    processor = PDFProcessor()
    
    info = processor.get_pdf_info("./data/10.1002_advs.202207112.pdf")

    # get the all of the pdf information
    pdf_dir = "./data"
    pdf_files = os.listdir(pdf_dir)
    for pdf_file in pdf_files:
        if pdf_file.endswith(".pdf"):
            info = processor.get_pdf_info(os.path.join(pdf_dir, pdf_file))
            print(info)