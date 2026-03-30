import os
import requests
import json
import time
from datetime import date, datetime
from app.services.rag_service import rag_service
from app.models.chat_history import ChatHistory
from app.models.daily_report import DailyReport
from app.models.patient import Patient
from app.models.patient_context import PatientContext
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
        start_total = time.time()
        print(f"\n[AI][DEBUG] === INÍCIO DO PROCESSAMENTO ===", flush=True)
        print(f"[AI][USER] Mensagem: '{message}'", flush=True)

        # 1. CLASSIFICAÇÃO DE INTENÇÃO
        start_step = time.time()
        intent = self._classify_intent(message)
        print(f"[AI][TIME] 1. Classificação de Intenção: {time.time() - start_step:.2f}s (Intent: {intent})", flush=True)
        
        # 2. MEMÓRIA DE CURTO PRAZO (Reduzida para evitar redundância com a KB)
        start_step = time.time()
        last_chats = []
        if user_id:
            # Reduzimos de 5 para 2 mensagens para economizar tokens e focar na Janela de Contexto (KB)
            recent_chats = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).limit(2).all()
            last_chats = list(reversed(recent_chats))
        print(f"[AI][TIME] 2. Busca de Memória (Curto Prazo): {time.time() - start_step:.2f}s", flush=True)

        # 3. BUSCA RAG
        start_step = time.time()
        context_sus = ""
        sources = []
        if intent in ["HEALTH_QUERY", "EMERGENCY"]:
            try:
                context_sus, sources = rag_service.query_protocols_with_sources(message)
            except Exception as e:
                print(f"[AI][ERROR] Falha no RAG: {e}")
        rag_hit = bool(context_sus) and not context_sus.startswith("Consulte o manual do SUS")
        print(f"[AI][TIME] 3. Busca RAG (Embeddings): {time.time() - start_step:.2f}s", flush=True)
        
        # 4. CONSTRUÇÃO DO PROMPT
        start_step = time.time()
        messages = self._build_chat_messages(message, intent, context_sus, last_chats, sources, user_id)
        print(f"[AI][TIME] 4. Montagem do Template: {time.time() - start_step:.2f}s", flush=True)
        
        # 5. GERA RESPOSTA
        start_step = time.time()
        print(f"[AI][PROCESSANDO] Gerando resposta no LLM...", flush=True)
        response = self._call_llama_chat(messages)
        print(f"[AI][TIME] 5. Geração Llama Chat: {time.time() - start_step:.2f}s", flush=True)

        # 6. PERSISTE NO BANCO
        start_step = time.time()
        if user_id:
            new_chat = ChatHistory(user_id=user_id, message=message, response=response, intent=intent)
            db.session.add(new_chat)
            db.session.commit()
        print(f"[AI][TIME] 6. Persistência DB: {time.time() - start_step:.2f}s", flush=True)
        
        print(f"[AI][DEBUG] === FIM DO PROCESSAMENTO ({time.time() - start_total:.2f}s total) ===\n", flush=True)
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

    def update_patient_context(self, patient_id):
        """Resume o histórico recente do paciente em um dicionário estruturado e salva no banco de dados (Janela de Contexto)."""
        chats = ChatHistory.query.filter_by(user_id=patient_id).order_by(ChatHistory.timestamp.asc()).all()
        if not chats:
            return None
        
        conversation_transcript = "\n".join([
            f"Paciente: {c.message}\nIA: {c.response}\n" 
            for c in chats
        ])

        summary_prompt = f"""
Você é um sistema de auditoria e memória de longo prazo para um Agente de Saúde Inteligente.
Sua tarefa é analisar todo o histórico de conversas do paciente e extrair um **JSON estruturado** com as informações vitais.
Esse JSON será usado como a Janela de Contexto (Knowledge Base) para que o agente inteligente de saúde se lembre do paciente nas próximas conversas.

Histórico completo:
{conversation_transcript}

INSTRUÇÃO OBRIGATÓRIA DE FORMATO:
Você DEVE retornar APENAS um objeto JSON válido, sem nenhum outro texto antes ou depois. 
IMPORTANTE: Use caracteres acentuados diretamente (ex: "cabeça", "paciência") no JSON, NÃO use sequências de escape unicode (ex: "\u00e7").
Siga EXATAMENTE esta estrutura:
{{
  "nome_do_paciente": "Extrair se o paciente informou o nome, senão omitir ou null",
  "data_ultima_conversa": "{date.today().isoformat()}",
  "sintomas_relatados": ["Lista de sintomas extraídos", "..."],
  "medicacoes_relatadas": ["Lista de medicações que o paciente disse tomar", "..."],
  "acoes_recomendadas_pela_ia": ["Principais ações que a IA recomendou no passado"],
  "observacoes_adicionais": "Observações relevantes, histórico social, etc"
}}
"""
        response_text = self._call_llama(summary_prompt).strip()
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx+1]
                context_dict = json.loads(json_str)
                
                existing_context = PatientContext.query.filter_by(patient_id=patient_id).first()
                if existing_context:
                    existing_context.context_data = context_dict
                    existing_context.updated_at = datetime.utcnow()
                else:
                    new_context = PatientContext(patient_id=patient_id, context_data=context_dict)
                    db.session.add(new_context)
                db.session.commit()
                print(f"[AI CONTEXT] Contexto Atualizado com Sucesso para paciente {patient_id}.")
                return context_dict
            else:
                print(f"[AI CONTEXT ERROR] JSON não encontrado na resposta.")
        except Exception as e:
            db.session.rollback()
            print(f"[AI CONTEXT ERROR] Falha ao extrair ou salvar contexto: {e}\nResposta Bruta: {response_text}")
        return None

    def _classify_intent(self, message):
        """Usa o Llama para classificar o que o idoso quer"""
        classification_prompt = f"""
        Classifique a intenção da mensagem do usuário em UMA ÚNICA PALAVRA:
        - GREETING: Se for apenas um 'olá', 'bom dia', 'oi', 'tudo bem?', etc.
        - HEALTH_QUERY: Se for uma dúvida comum de saúde, sintomas leves ou relato de hábitos.
        - EMERGENCY: Se for um relato de dor aguda, falta de ar ou risco de vida.
        - OTHER: Qualquer outro assunto.
        
        Mensagem: "{message}"
        Intenção:"""
        
        intent = self._call_llama(classification_prompt).strip().upper()
        # Limpeza para garantir que venha apenas a palavra
        for category in ["GREETING", "HEALTH_QUERY", "EMERGENCY"]:
            if category in intent: return category
        return "OTHER"

    def analyze_patient_triage(self, patient_history_text):
        """Analisa os relatórios do paciente e retorna JSON de prioridade (ALTA, MÉDIA, BAIXA) com justificativa."""
        triage_prompt = f"""
Você é um sistema de Triagem Clínica Inteligente projetado para ajudar Agentes Comunitários de Saúde (ACS).
Sua tarefa é analisar os relatórios recentes de um paciente e definir o nível de prioridade para visita domiciliar ou atenção primária.

Regras de Classificação:
- ALTA: Relatos de sintomas graves (dor no peito, falta de ar severa, confusão mental), emergências não solucionadas, risco de vida iminente ou desestabilização grave de doenças crônicas.
- MÉDIA: Presença de sintomas moderados, dúvidas importantes sobre nova medicação, piora leve de condição crônica, dor moderada persistente.
- BAIXA: Rotina normal, checagem padrão, sintomas leves resolvidos, sem queixas urgentes recentes.

INSTRUÇÃO OBRIGATÓRIA DE FORMATO:
Você DEVE retornar APENAS um objeto JSON válido, sem nenhum outro texto antes ou depois, seguindo EXATAMENTE esta estrutura:
{{
  "nivel": "ALTA" ou "MÉDIA" ou "BAIXA",
  "justificativa": "Uma explicação em um parágrafo claro, objetivo e clínico do porquê esse nível de prioridade foi escolhido, mencionando os pontos chave do histórico lido. Indique o aconselhamento ou os riscos."
}}

Histórico Recente de Relatórios do Paciente:
{patient_history_text}

JSON gerado:
"""
        response_text = self._call_llama(triage_prompt).strip()
        
        # Tentativa de extrair o JSON caso o Llama inclua texto em volta (ex: "Aqui está o JSON: ...")
        try:
            # Encontra o primeiro { e o último }
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx+1]
                triage_data = json.loads(json_str)
                # Garante que as chaves existem
                if "nivel" not in triage_data or "justificativa" not in triage_data:
                    raise ValueError("Faltam chaves no JSON da triagem.")
                    
                # Padroniza nivel
                nivel = str(triage_data["nivel"]).upper()
                if "ALTA" in nivel: nivel = "ALTA"
                elif "MÉDIA" in nivel or "MEDIA" in nivel: nivel = "MÉDIA"
                else: nivel = "BAIXA"
                
                triage_data["nivel"] = nivel
                return triage_data
            else:
                raise ValueError("Nenhum JSON encontrado na resposta da IA.")
        except json.JSONDecodeError as e:
            print(f"[AI TRIAGE ERROR] Falha ao parsear JSON: {e}\nResposta Bruta: {response_text}")
            return {"nivel": "BAIXA", "justificativa": "Erro ao tentar ler o formato devolvido pela Inteligência Artificial. Recomendável ver os relatórios manualmente."}
        except Exception as e:
            print(f"[AI TRIAGE ERROR] Erro inesperado: {e}")
            return {"nivel": "BAIXA", "justificativa": "Erro interno no processamento com a Inteligência Artificial."}

    
    def _build_chat_messages(self, message, intent, context, last_chats, sources=None, user_id=None):
        system_rules = "Você é um assistente de saúde empático para idosos."

        # Injeção de Janela de Contexto (KB) - Memória de Longo Prazo
        if user_id:
            try:
                user_context = PatientContext.query.filter_by(patient_id=user_id).first()
                if user_context and user_context.context_data:
                    kb_data = user_context.context_data
                    nome = kb_data.get("nome_do_paciente")
                    if nome and nome != "null":
                        system_rules += f" O nome do paciente é {nome}."
                    
                    # Formatação mais limpa para a KB
                    kb_summary = json.dumps(kb_data, ensure_ascii=False, indent=2)
                    system_rules += f"\n\nJANELA DE CONTEXTO (BASE DE CONHECIMENTO):\n{kb_summary}\n"
                    system_rules += "Aja naturalmente. Use as informações da Janela de Contexto APENAS como conhecimento de fundo para não fazer perguntas repetitivas. NÃO relembre o histórico do paciente de forma proativa. Não diga coisas como 'lembrando que você tem...'. Use a memória de forma invisível."
            except Exception as e:
                print(f"[AI CONTEXT ERROR] Erro ao carregar PatientContext: {e}")

        if intent == "EMERGENCY":
            system_rules += " ATENÇÃO: Possível emergência. Oriente o paciente a buscar ajuda imediata (SAMU/UBS) e avalie sinais de risco."
        elif intent == "GREETING":
            system_rules += " ATENÇÃO: O usuário APENAS CUMPRIMENTOU ou fez uma saudação. VOCÊ DEVE APENAS RETRIBUIR O CUMPRIMENTO (ex: 'Olá! Como posso te ajudar hoje?') e PARE POR AÍ. VOCÊ ESTÁ TERMINANTEMENTE PROIBIDO de iniciar assuntos sobre saúde, exercícios, dieta ou histórico médico por conta própria."

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
            fontes_instruction = f'Ao final da resposta, inclua a linha: "Fontes: {fontes_str}"\n'

        system_content = f"{system_rules}\n\n{rag_guidance}\n\n{fontes_instruction}"
        if context:
            system_content += f"\nCONTEXTO-BASE (Protocolos do SUS):\n{context}\n"
        
        system_content += "\nDIRETRIZES DE RESPOSTA OBRIGATÓRIAS:\n"
        system_content += "- Seja EXTREMAMENTE conciso e vá direto ao ponto.\n"
        system_content += "- Espelhe o tamanho da mensagem do usuário. Se o usuário disser apenas 'oi', 'olá', 'tudo bem?', responda APENAS com um cumprimento curto (ex: 'Olá! Como posso te ajudar hoje?')"
        system_content += "- NÃO inicie assuntos médicos por conta própria.\n"
        system_content += "- Só dê conselhos de saúde se o paciente perguntar ativamente sobre algo."

        # O Histórico é passado como mensagens distintas (não concatenado)
        messages = [{"role": "system", "content": system_content.strip()}]

        for chat in last_chats:
            messages.append({"role": "user", "content": chat.message})
            messages.append({"role": "assistant", "content": chat.response})

        messages.append({"role": "user", "content": message})
        
        return messages


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

    def _call_llama_chat(self, messages):
        chat_url = self.ollama_url.replace('/api/generate', '/api/chat')
        payload = {"model": self.llama_model, "messages": messages, "stream": False}
        try:
            res = requests.post(chat_url, json=payload, timeout=90)
            return res.json().get("message", {}).get("content", "Desculpe, não consegui gerar uma resposta.")
        except Exception as e:
            print(f"Erro no Llama Chat: {e}")
            return "Erro de conexão com o Llama 3.2:3b (Ollama). Verifique se ele está rodando."
