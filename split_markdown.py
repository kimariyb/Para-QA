from langchain.text_splitter import MarkdownHeaderTextSplitter

def main(text: str) -> dict:
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[('#', 'header 1')])
    
    documents = splitter.split_text(text)

    chunks = []
    for doc in documents:
        chunks.append(doc.page_content)
    
    return {"result": chunks}
    
    
if __name__ == '__main__':
    with open("./selected/10.1002_advs.202207112_cleaned.md", "r", encoding="utf-8") as f:
        text = f.read()
    result = main(text)['result']

    for i, chunk in enumerate(result):
        print(f"Chunk {i}:")
        print(chunk)
    