import os
import logging
from chromadb import PersistentClient, Settings
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        # No rag_service.py
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
        self.db_path = os.path.join(self.BASE_DIR, "data", "vector_db")
        self.protocols_dir = os.path.join(self.BASE_DIR, "data", "protocols") 
        
        if not os.path.exists(self.db_path): os.makedirs(self.db_path)
        if not os.path.exists(self.protocols_dir): os.makedirs(self.protocols_dir)
            
        self.client = PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False) # Desativa telemetria anônima (Versões mais recentes do ChromaDB)
        )
        self.collection = self.client.get_or_create_collection(name="sus_protocols")
        
        self.offline_mode = False
        
        try:
            logger.info("⌛ Inicializando modelo de embeddings no startup do servidor...")
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"⚙️ Dispositivo selecionado para embeddings: {device.upper()}")
            
            model_name = 'sentence-transformers/all-MiniLM-L6-v2'
            logger.info(f"📥 Carregando modelo '{model_name}' (do cache ou baixando)...")
            self.model = SentenceTransformer(model_name, device=device)
            logger.info("✅ Modelo carregado na memória.")
            
            logger.info("🔥 Executando warmup do modelo na GPU para compilação (aguarde)...")
            self.model.encode("Warmup dummy text para inicializar o contexto CUDA.")
            logger.info("✅ Modelo de embeddings aquecido com sucesso!")
            
            # Carrega os protocolos se o banco estiver vazio
            self.load_pdf_protocols()
        except Exception as e:
            logger.error(f"⚠️ Erro crítico ao carregar modelo de embeddings: {e}", exc_info=True)
            self.offline_mode = True
            self.model = None

    def load_pdf_protocols(self):
        """Lê todos os PDFs na pasta de protocolos e os adiciona ao banco"""
        if self.offline_mode: return
        
        # Verifica se o banco já tem dados para não reprocessar tudo
        if self.collection.count() > 0:
            logger.info("✅ Banco vetorial já contém dados. Pulando carregamento inicial.")
            return

        for filename in os.listdir(self.protocols_dir):
            if filename.endswith(".pdf"):
                path = os.path.join(self.protocols_dir, filename)
                logger.info(f"📄 Processando PDF: {filename}...")
                reader = PdfReader(path)
                
                # Extrai texto por página e adiciona ao banco
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if len(text.strip()) > 100: # Evita páginas quase vazias
                        self.add_protocol(text, {"source": filename, "page": i+1})

    def add_protocol(self, text, metadata=None):
        if not self.offline_mode and self.model:
            # Refinamento de Chunking: 
            # 1. Limpeza básica do texto
            text = text.replace('\n', ' ').replace('  ', ' ')
            
            # 2. Divide em chunks com sobreposição (overlap) para manter o contexto entre pedaços
            chunk_size = 1000
            overlap = 200
            
            chunks = []
            start = 0
            while start < len(text):
                end = start + chunk_size
                # Tenta não cortar frases ao meio (busca o último ponto final no chunk)
                if end < len(text):
                    last_period = text.rfind('. ', start, end)
                    if last_period != -1 and last_period > start + (chunk_size // 2):
                        end = last_period + 1
                
                chunks.append(text[start:end].strip())
                start = end - overlap if end < len(text) else len(text)

            for idx, chunk in enumerate(chunks):
                if len(chunk) < 50: continue # Ignora pedaços irrelevantes
                
                embedding = self.model.encode(chunk).tolist()
                # ID único combinando fonte e índice do chunk
                source_name = metadata.get('source', 'doc').replace(' ', '_')
                doc_id = f"{source_name}_p{metadata.get('page', 0)}_c{idx}"
                
                self.collection.add(
                    ids=[doc_id], 
                    embeddings=[embedding], 
                    documents=[chunk], 
                    metadatas=[metadata]
                )

    def query_protocols(self, query_text, n_results=2):
        if not self.offline_mode and self.model:
            try:
                query_embedding = self.model.encode(query_text).tolist()
                results = self.collection.query(query_embeddings=[query_embedding], n_results=n_results)
                if results['documents']: return " ".join(results['documents'][0])
            except Exception as e:
                logger.error(f"[RAG][ERROR] Falha ao consultar histórico clínico na KB (memória): {e}", exc_info=True)
        # Busca simples por texto se o modelo falhar
        return "Consulte o manual do SUS para orientações sobre: " + query_text

    def query_protocols_with_sources(self, query_text, n_results=2):
        if not self.offline_mode and self.model:
            try:
                query_embedding = self.model.encode(query_text).tolist()
                results = self.collection.query(query_embeddings=[query_embedding], n_results=n_results)
                docs = results.get('documents') or []
                metas = results.get('metadatas') or []
                if docs:
                    context = " ".join(docs[0])
                    sources = []
                    for md in metas[0]:
                        if isinstance(md, dict):
                            src = md.get('source')
                            pg = md.get('page')
                        else:
                            src = None
                            pg = None
                        if src:
                            label = f"{src} (p.{pg})" if pg else f"{src}"
                            if label not in sources:
                                sources.append(label)
                    return context, sources
            except Exception as e:
                logger.error(f"[RAG][ERROR] Falha ao consultar protocolos com fontes na KB: {e}", exc_info=True)
        return "Consulte o manual do SUS para orientações sobre: " + query_text, []

# Instância global
rag_service = RAGService()