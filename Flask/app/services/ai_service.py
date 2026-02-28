import os
import requests
import json
from app.services.rag_service import rag_service

class HealthAgent:
    def __init__(self):
        # Localhost para velocidade máxima fora do Docker
        self.ollama_url = "http://localhost:11434/api/generate"
        self.medgemma_url = "http://localhost:8001/analyze" 
        self.llama_model = "llama3.2" # Modelo 3B que cabe na VRAM de 4GB

    def get_response(self, message):
        # 1. Busca RAG Real (ChromaDB com protocolos SUS)
        context_sus = rag_service.query_protocols(message)
        
        # 2. Decisão: Comentado temporariamente para o teste básico (MedGemma offline)
        # if self._needs_medical_analysis(message):
        #     medical_analysis = self._call_medgemma(message)
        #     message = f"Análise Médica Especializada: {medical_analysis}\n\nPergunta Original do Idoso: {message}"

        # 3. Resposta Final via Llama 3 com Contexto SUS
        prompt = f"""
        DIRETRIZES DO SUS (Contexto Oficial): {context_sus}
        
        INSTRUÇÃO PARA O ASSISTENTE:
        Você é um assistente de saúde para idosos. Responda à pergunta abaixo baseando-se estritamente nas diretrizes do SUS fornecidas acima.
        Se as diretrizes não tiverem a resposta, use seu conhecimento geral mas mencione que é uma orientação básica.
        Seja muito atencioso, use linguagem simples e seja empático.
        
        USUÁRIO IDOSO: {message}
        """
        
        return self._call_llama(prompt)

    def _needs_medical_analysis(self, text):
        # Lógica para decidir se chama o MedGemma (pode ser refinada)
        keywords = ['dor', 'febre', 'sintoma', 'remédio', 'pressão', 'ferida', 'inflamação']
        return any(word in text.lower() for word in keywords)

    def _call_medgemma(self, symptoms):
        try:
            # Chama o microserviço em FastAPI
            response = requests.post(self.medgemma_url, json={"symptoms": symptoms}, timeout=10)
            return response.json().get("analysis", "Erro ao processar análise.")
        except:
            return "O serviço de análise médica profunda está offline no momento."

    def _call_llama(self, prompt):
        payload = {"model": self.llama_model, "prompt": prompt, "stream": False}
        try:
            # Aumentado o timeout para 90s por segurança, embora o llama3.2 deva responder em <5s
            res = requests.post(self.ollama_url, json=payload, timeout=90)
            return res.json().get("response", "Desculpe, não consegui gerar uma resposta.")
        except Exception as e:
            print(f"Erro no Llama: {e}")
            return "Erro de conexão com o Llama 3.2 (Ollama). Verifique se ele está rodando."