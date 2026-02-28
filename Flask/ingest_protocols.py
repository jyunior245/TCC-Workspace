import sys
import os

# Adiciona o diretório atual ao path para importar os serviços
sys.path.append(os.getcwd())

from app.services.rag_service import rag_service

def ingest():
    print("🚀 Iniciando processamento de protocolos reais do SUS...")
    rag_service.load_pdf_protocols()
    print("✅ Todos os documentos foram indexados no banco vetorial!")

if __name__ == "__main__":
    ingest()