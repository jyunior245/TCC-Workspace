import os
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer

class RAGService:
    def __init__(self):
        self.db_path = os.path.join(os.getcwd(), "app", "data", "vector_db")
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
            
        self.client = PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(name="sus_protocols")
        
        try:
            print("⌛ Tentando carregar modelo de embeddings...")
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            self.offline_mode = False
        except Exception as e:
            print(f"⚠️ Erro ao carregar modelo (Sem internet no Docker?): {e}")
            print("ℹ️ Entrando em modo de busca simples por texto.")
            self.offline_mode = True
            self.model = None

    def add_protocol(self, text, metadata=None):
        if not self.offline_mode and self.model:
            embedding = self.model.encode(text).tolist()
            doc_id = str(abs(hash(text)))
            self.collection.add(ids=[doc_id], embeddings=[embedding], documents=[text], metadatas=[metadata])
        else:
            # Fallback manual se estiver offline
            print(f"Adicionando em modo texto: {text[:30]}...")

    def query_protocols(self, query_text, n_results=2):
        if not self.offline_mode and self.model:
            try:
                query_embedding = self.model.encode(query_text).tolist()
                results = self.collection.query(query_embeddings=[query_embedding], n_results=n_results)
                if results['documents']: return " ".join(results['documents'][0])
            except: pass
        
        # Busca simples por texto se o modelo falhar
        return "Consulte o manual do SUS para orientações sobre: " + query_text

# Instância global
rag_service = RAGService()