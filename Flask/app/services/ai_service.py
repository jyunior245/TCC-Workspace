import os
import requests
import json
from datetime import date, datetime
from app.services.rag_service import rag_service
from app.models.chat_history import ChatHistory
from app.models.daily_report import DailyReport
from app.models.patient import Patient
from app.extensions.sql_alchemy import db

class HealthAgent:
    def __init__(self):
        ollama_env = os.getenv("OLLAMA_URL")
        if ollama_env:
            self.ollama_url = ollama_env
        elif os.getenv("RUNNING_IN_DOCKER"):
            self.ollama_url = "http://ollama:11434/api/generate"
        else:
            self.ollama_url = "http://localhost:11434/api/generate"
        self.llama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    def get_response(self, message, user_id=None):
        # 1. CLASSIFICAÇÃO DE INTENÇÃO
        intent = self._classify_intent(message)
        
        # 2. MEMÓRIA DE LONGO PRAZO (Busca no Postgres)
        persistent_history = ""
        if user_id:
            # Pega as últimas 5 mensagens do usuário
            last_chats = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).limit(5).all()
            persistent_history = "\n".join([f"Paciente: {c.message}\nVocê: {c.response}" for c in reversed(last_chats)])
            print(f"[AI][MEMÓRIA] Recuperadas {len(last_chats)} interações anteriores do banco.")
            if persistent_history:
                print("--- HISTÓRICO INJETADO ---")
                print(persistent_history)
                print("--------------------------")

        # 3. BUSCA RAG (Apenas se a intenção for de saúde)
        context_sus = ""
        sources = []
        if intent in ["HEALTH_QUERY", "EMERGENCY"]:
            try:
                context_sus, sources = rag_service.query_protocols_with_sources(message)
            except AttributeError:
                context_sus = rag_service.query_protocols(message)
                sources = []
        rag_hit = bool(context_sus) and not context_sus.startswith("Consulte o manual do SUS")
        print(f"[AI][RAG] intent={intent} hit={rag_hit} fontes={sources}")

        # 4. CONSTRUÇÃO DO PROMPT FINAL
        prompt = self._build_prompt(message, intent, context_sus, persistent_history, sources)
        
        # 5. GERA RESPOSTA
        response = self._call_llama(prompt)
        
        # 6. PERSISTE NO BANCO DE DADOS
        if user_id:
            new_chat = ChatHistory(user_id=user_id, message=message, response=response, intent=intent)
            db.session.add(new_chat)
            db.session.commit()
            
        return response

    def generate_daily_report(self, patient_id, target_date=None):
        """Gera um relatório diário das interações do paciente para o ACS visualizar"""
        if not target_date:
            target_date = date.today()

        # Busca histórico do dia específico
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        chats_today = ChatHistory.query.filter(
            ChatHistory.user_id == patient_id,
            ChatHistory.timestamp >= start_of_day,
            ChatHistory.timestamp <= end_of_day
        ).order_by(ChatHistory.timestamp.asc()).all()

        if not chats_today:
            return None, "O paciente não teve interações com a IA neste dia."

        # Transcreve a conversa
        conversation_transcript = "\n".join([
            f"[{c.timestamp.strftime('%H:%M')}] Paciente ({c.intent}): {c.message}\nIA: {c.response}\n" 
            for c in chats_today
        ])

        # Prompt para sumarização clínica
        summary_prompt = f"""
Você é um sistema de sumarização clínica projetado para ajudar Agentes Comunitários de Saúde (ACS).
Analise o seguinte histórico de chat de um paciente hoje e crie um Relatório Diário conciso e estruturado.

Diretrizes para o Relatório:
1. FOCO NA SAÚDE: Destaque quaisquer sintomas relatados, dores, medicamentos mencionados ou queixas.
2. SINAIS DE ALERTA: Se houver indícios de gravidade (emergências, dores agudas, confusão), inicie o relatório com um [ALERTA] bem claro.
3. CONTEXTO SOCIAL: Mencione brevemente o estado emocional ou necessidades sociais, se o paciente relatou.
4. FORMATO: Use Markdown (bullet points, **negrito** para termos chave) para facilitar a leitura rápida do ACS.

Histórico das Conversas de Hoje:
{conversation_transcript}

Gere o Relatório Diário de Saúde agora:
"""
        
        report_content = self._call_llama(summary_prompt)

        # Salva ou atualiza no banco
        try:
            existing_report = DailyReport.query.filter_by(patient_id=patient_id, date=target_date).first()
            if existing_report:
                existing_report.content = report_content
                existing_report.updated_at = datetime.utcnow()
            else:
                new_report = DailyReport(patient_id=patient_id, date=target_date, content=report_content)
                db.session.add(new_report)
            
            db.session.commit()
            return report_content, "Relatório gerado com sucesso."
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao salvar relatório diário: {str(e)}")
            return report_content, f"Relatório gerado, mas erro ao salvar no banco: {str(e)}"

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

    def _build_prompt(self, message, intent, context, history, sources=None):
        system_rules = "Você é um assistente de saúde empático para idosos."

        if intent == "EMERGENCY":
            system_rules += " ATENÇÃO: Possível emergência. Oriente o paciente a buscar ajuda imediata (SAMU/UBS) e avalie sinais de risco."
        elif intent == "GREETING":
            system_rules += " Responda cordialmente a saudações e incentive o autocuidado."

        if intent in ("HEALTH_QUERY", "EMERGENCY"):
            rag_guidance = (
                "Regras de Resposta (priorizar RAG):\n"
                "- Responda dúvidas médicas exclusivamente com base no CONTEXTO-BASE (Protocolos do SUS).\n"
                "- Se o CONTEXTO-BASE não trouxer a resposta para a dúvida de saúde, diga que não encontrou nos protocolos e recomende procurar a UBS.\n"
                "- Não invente informações médicas nem dê diagnósticos; forneça orientações gerais e seguras.\n"
            )
        else:
            rag_guidance = (
                "Regras de Resposta (assunto geral):\n"
                "- Seja útil, direto e mantenha o papo agradável.\n"
            )

        fontes_instruction = ""
        if sources:
            fontes_str = ", ".join(sources)
            fontes_instruction = f'Ao final da resposta, inclua a linha: "Fontes: {fontes_str}"'

        history_section = ""
        if history:
            history_section = f"\nLembre-se do CONTEXTO da conversa até agora:\n{history}\n"

        return f"""
        {system_rules}

        {rag_guidance}

        CONTEXTO-BASE (Protocolos do SUS):
        {context or '[Nenhum protocolo específico para esta mensagem]'}
        {history_section}
        O paciente enviou uma nova mensagem. Responda diretamente ao paciente em 2–5 frases, mantendo a continuidade do assunto se for uma pergunta de seguimento.
        IMPORTANTE: Não escreva 'Você:', 'Assistente:', 'Paciente:' nem qualquer outro prefixo na sua resposta. Comece a frase diretamente.

        Nova mensagem do Paciente: {message}
        Sua Resposta:"""


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
            return "Erro de conexão com o Llama 3.2:3b (Ollama). Verifique se ele está rodando."