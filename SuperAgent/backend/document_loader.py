"""文档加载和分片服务"""
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader


class DocumentLoader:
    """文档加载和分片服务"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.text_splitter_config = {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "separators": ["\n\n", "\n", "。", "！", "？", "，", "、", " ", ""]
        }
        self.text_splitter = RecursiveCharacterTextSplitter(**self.text_splitter_config)

    def load_document(self, file_path: str, filename: str) -> list[dict]:
        """
        加载单个文档并分片
        :param file_path: 文件路径
        :param filename: 文件名
        :return: 分片后的文档列表
        """
        file_lower = filename.lower()

        if file_lower.endswith(".pdf"):
            doc_type = "PDF"
            loader = PyPDFLoader(file_path)
        elif file_lower.endswith((".docx", ".doc")):
            doc_type = "Word"
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {filename}")

        try:
            raw_docs = loader.load()
            split_docs = self.text_splitter.split_documents(raw_docs)

            documents = []
            for idx, doc in enumerate(split_docs):
                documents.append({
                    "text": doc.page_content.strip(),
                    "filename": filename,
                    "file_path": file_path,
                    "file_type": doc_type,
                    "page_number": doc.metadata.get("page", 0),
                    "chunk_idx": idx
                })
            return documents
        except Exception as e:
            raise Exception(f"处理文档失败: {str(e)}")

    def load_documents_from_folder(self, folder_path: str) -> list[dict]:
        """
        从文件夹加载所有文档并分片
        :param folder_path: 文件夹路径
        :return: 所有分片后的文档列表
        """
        all_documents = []

        for filename in os.listdir(folder_path):
            file_lower = filename.lower()
            if not (file_lower.endswith(".pdf") or file_lower.endswith((".docx", ".doc"))):
                continue

            file_path = os.path.join(folder_path, filename)
            try:
                documents = self.load_document(file_path, filename)
                all_documents.extend(documents)
            except Exception:
                continue

        return all_documents
