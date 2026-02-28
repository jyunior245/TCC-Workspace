import sys
import os

# Adiciona o diretório atual ao path para importar os serviços
sys.path.append(os.getcwd())

from app.services.ai_service import HealthAgent
from app.services.rag_service import rag_service

def main():
    print("🤖 Inicializando Agente de Saúde (Llama 3.2 + RAG)...")
    agent = HealthAgent()
    print("✅ Agente pronto! Digite sua dúvida ou 'sair' para encerrar.\n")

    while True:
        user_input = input("👴 Usuário: ")
        
        if user_input.lower() in ['sair', 'exit', 'quit']:
            break
            
        print("🔍 Buscando no RAG...")
        context = rag_service.query_protocols(user_input)
        print(f"📖 Contexto encontrado: {context[:200]}...") # Mostra o começo do contexto
        
        print("⌛ Pensando na resposta final...")
        response = agent.get_response(user_input)
        
        print(f"\n🤖 Assistente: {response}\n")
        print("-" * 50)

if __name__ == "__main__":
    main()