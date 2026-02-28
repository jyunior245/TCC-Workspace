import sys
import os

# Adiciona o diretório atual ao path para conseguir importar o app
sys.path.append(os.getcwd())

from app.services.rag_service import rag_service

def seed_data():
    print("Iniciando alimentação do banco de dados de protocolos (RAG)...")
    
    protocols = [
        {
            "text": "Protocolo de Febre em Idosos (SUS): Em caso de febre leve (até 37.8°C), recomenda-se repouso, hidratação oral constante e monitoramento. Se a febre persistir por mais de 24h ou ultrapassar 38.5°C, deve-se procurar a Unidade Básica de Saúde (UBS) mais próxima.",
            "metadata": {"source": "Manual de Atenção ao Idoso - SUS", "topic": "febre"}
        },
        {
            "text": "Protocolo de Hidratação: Idosos devem ingerir pelo menos 2 litros de água por dia, mesmo sem sentir sede, para evitar desidratação e confusão mental.",
            "metadata": {"source": "Diretrizes de Saúde Preventiva", "topic": "hidratação"}
        },
        {
            "text": "Protocolo de Hipertensão: A pressão arterial ideal para idosos deve ser mantida abaixo de 140/90 mmHg. Em caso de tontura ou dor na nuca, recomenda-se aferir a pressão e evitar o consumo de sal.",
            "metadata": {"source": "Protocolo de Doenças Crônicas", "topic": "pressão"}
        }
    ]

    for p in protocols:
        print(f"➕ Adicionando protocolo sobre: {p['metadata']['topic']}...")
        rag_service.add_protocol(p['text'], p['metadata'])
    
    print("Banco de dados RAG alimentado com sucesso!")

if __name__ == "__main__":
    seed_data()