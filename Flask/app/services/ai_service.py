import os
import requests
import json
from app.services.rag_service import rag_service
from app.models.chat_history import ChatHistory
from app.extensions.sql_alchemy import db

class HealthAgent:
    def __init__(self):
        # Localhost para velocidade máxima fora do Docker
        self.ollama_url = "http://localhost:11434/api/generate"
        self.llama_model = "llama3.2"

    def get_response(self, message, user_id=None):
        # 1. CLASSIFICAÇÃO DE INTENÇÃO
        intent = self._classify_intent(message)
        
        # 2. MEMÓRIA DE LONGO PRAZO (Busca no Postgres)
        persistent_history = ""
        if user_id:
            # Pega as últimas 5 mensagens do usuário
            last_chats = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).limit(5).all()
            persistent_history = "\n".join([f"U: {c.message}\nA: {c.response}" for c in reversed(last_chats)])

        # 3. BUSCA RAG (Apenas se a intenção for de saúde)
        context_sus = ""
        if intent in ["HEALTH_QUERY", "EMERGENCY"]:
            context_sus = rag_service.query_protocols(message)

        # 4. CONSTRUÇÃO DO PROMPT FINAL
        prompt = self._build_prompt(message, intent, context_sus, persistent_history)
        
        # 5. GERA RESPOSTA
        response = self._call_llama(prompt)
        
        # 6. PERSISTE NO BANCO DE DADOS
        if user_id:
            new_chat = ChatHistory(user_id=user_id, message=message, response=response, intent=intent)
            db.session.add(new_chat)
            db.session.commit()
            
        return response

    def _classify_intent(self, message):
        """Usa o Llama para classificar o que o idoso quer"""
        classification_prompt = f"""
        Classifique a intenção da mensagem do usuário em UMA ÚNICA PALAVRA:
        - GREETING: Se for apenas um 'olá', 'bom dia', etc.
        - HEALTH_QUERY: Se for uma dúvida comum de saúde ou sintomas leves.
        - EMERGENCY: Se for um relato de dor aguda, falta de ar ou risco de vida.
        - OTHER: Qualquer outro assunto.

        Mensagem: "{message}"
        Intenção:"""
        
        intent = self._call_llama(classification_prompt).strip().upper()
        # Limpeza para garantir que venha apenas a palavra
        for category in ["GREETING", "HEALTH_QUERY", "EMERGENCY"]:
            if category in intent: return category
        return "OTHER"

    def _build_prompt(self, message, intent, context, history):
        system_rules = "Você é um assistente de saúde empático para idosos."
        
        if intent == "EMERGENCY":
            system_rules += " ATENÇÃO: O usuário pode estar em emergência. Recomende socorro imediato!"
        elif intent == "GREETING":
            system_rules += " Seja gentil e pergunte como o usuário se sente hoje."

        return f"""
        {system_rules}
        
        MEMÓRIA ANTERIOR:
        {history}
        
        CONTEXTO SUS (Protocolos):
        {context}
        
        USUÁRIO: {message}
        ASSISTENTE:"""

    def _call_llama(self, prompt):
        payload = {"model": self.llama_model, "prompt": prompt, "stream": False}
        try:
            res = requests.post(self.ollama_url, json=payload, timeout=90)
            return res.json().get("response", "...")
        except Exception as e:
            return f"Erro de conexão: {str(e)}"

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