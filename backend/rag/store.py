import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from backend.config import settings

class PolicyStore:
    def __init__(self):
        # We use a local persistent Chroma database
        os.makedirs(settings.CHROMA_PERSIST_DIRECTORY, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
        self.collection_name = "cms_policies"
        self._init_embeddings()
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
        )

    def _init_embeddings(self):
        # Defaulting to open-source embeddings to ensure no cost or API keys required
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        
    def add_documents(self, documents: list[Document]):
        """Add chunked documents to the Chroma store"""
        if documents:
            self.vectorstore.add_documents(documents)
            
    def search(self, query: str, top_k: int = 5, filter_dict: dict = None) -> list[Document]:
        """Search for relevant policy chunks"""
        return self.vectorstore.similarity_search(
            query=query, 
            k=top_k,
            filter=filter_dict
        )
    
    def clear(self):
        """Clear the collection (useful for testing)"""
        try:
            self.client.delete_collection(self.collection_name)
        except ValueError:
            pass # Collection does not exist
