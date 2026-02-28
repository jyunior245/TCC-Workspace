import os
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

class RAGService:
    def __init__(self):
        self.db_path = os.path.join(os.getcwd(), "app", "data", "vector_db")
        self.protocols_dir = os.path.join(os.getcwd(), "app", "data", "protocols")
        
        if not os.path.exists(self.db_path): os.makedirs(self.db_path)
        if not os.path.exists(self.protocols_dir): os.makedirs(self.protocols_dir)
            
        self.client = PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(name="sus_protocols")
        
        try:
            print("⌛ Carregando modelo de embeddings...")
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            self.offline_mode = False
        except Exception as e:
            print(f"⚠️ Erro ao carregar modelo: {e}")
            self.offline_mode = True
            self.model = None

    def load_pdf_protocols(self):
        """Lê todos os PDFs na pasta de protocolos e os adiciona ao banco"""
        if self.offline_mode: return
        
        for filename in os.listdir(self.protocols_dir):
            if filename.endswith(".pdf"):
                path = os.path.join(self.protocols_dir, filename)
                print(f"📄 Processando PDF: {filename}...")
                reader = PdfReader(path)
                
                # Extrai texto por página e adiciona ao banco
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if len(text.strip()) > 100: # Evita páginas quase vazias
                        self.add_protocol(text, {"source": filename, "page": i+1})

    def add_protocol(self, text, metadata=None):
        if not self.offline_mode and self.model:
            # Divide o texto em pedaços menores (chunks) para melhor precisão
            chunks = [text[i:i+1000] for i in range(0, len(text), 800)]
            for idx, chunk in enumerate(chunks):
                embedding = self.model.encode(chunk).tolist()
                doc_id = f"{metadata.get('source', 'doc')}_{metadata.get('page', 0)}_{idx}"
                self.collection.add(ids=[doc_id], embeddings=[embedding], documents=[chunk], metadatas=[metadata])

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