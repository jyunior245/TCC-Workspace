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
from datetime import timedelta

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
        
        # Ativa RAG se for Saúde/Emergência OU se houver menção direta a protocolos OU se houver sintomas claros
        symptoms_keywords = ["dor", "febre", "quente", "nariz", "tosse", "gripe", "mal", "sintoma", "remédio", "medicação"]
        is_health_query = intent in ["HEALTH_QUERY", "EMERGENCY"] or \
                          any(word in message.lower() for word in ["sus", "protocolo", "manual", "diretriz"]) or \
                          any(word in message.lower() for word in symptoms_keywords)
        
        if is_health_query:
            try:
                context_sus, sources = rag_service.query_protocols_with_sources(message, n_results=1)
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
        
        print(f"[AI][RESPONSE] {response}", flush=True)
        
        print(f"[AI][DEBUG] === FIM DO PROCESSAMENTO ({time.time() - start_total:.2f}s total) ===\n", flush=True)
        return response

    def generate_daily_report(self, patient_id, target_date=None, update_existing=False):
        """Gera um relatório diário das interações do paciente para o ACS visualizar"""
        from datetime import timezone, timedelta
        br_tz = timezone(timedelta(hours=-3))
        
        if not target_date:
            target_date = datetime.now(br_tz).date()

        # O banco de dados armazena em UTC. Precisamos definir os limites em UTC-3 e reverter para UTC
        start_of_day_local = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=br_tz)
        end_of_day_local = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=br_tz)
        
        start_of_day_utc = start_of_day_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_of_day_utc = end_of_day_local.astimezone(timezone.utc).replace(tzinfo=None)
        
        query = ChatHistory.query.filter(
            ChatHistory.user_id == patient_id,
            ChatHistory.timestamp >= start_of_day_utc,
            ChatHistory.timestamp <= end_of_day_utc
        )
        
        existing_report = DailyReport.query.filter_by(patient_id=patient_id, date=target_date).first()

        if update_existing and existing_report:
            # Busca apenas mensagens APÓS a última atualização do relatório
            query = query.filter(ChatHistory.timestamp > existing_report.updated_at)
            chats_today = query.order_by(ChatHistory.timestamp.asc()).all()
            
            if not chats_today:
                return existing_report.content, "Não há novas mensagens para atualizar o relatório hoje."
            
            conversation_transcript = "\n".join([
                f"[{c.timestamp.strftime('%H:%M')}] Paciente ({c.intent}): {c.message}\nIA: {c.response}\n" 
                for c in chats_today
            ])
            
            summary_prompt = f"""
Você é um sistema de sumarização clínica para Agentes Comunitários de Saúde (ACS).
Sua tarefa é ATUALIZAR o Relatório Diário do paciente.

Abaixo você receberá o Relatório Atual e as Novas Conversas.
Você deve REESCREVER o Relatório Atual incorporando as novas informações nas seções já existentes (ex: adicionando novos sintomas à lista de 'Sintomas Relatados', novos alertas em 'Alerta', etc).

REGRAS CRÍTICAS:
1. NÃO crie seções como "Nova Informação", "Estrutura Adicional" ou "Nova Conversa". Apenas reescreva o relatório fundindo os dados orgânicamente no layout base original.
2. NÃO transcreva e NÃO inclua trechos de diálogo ou o histórico da conversa no relatório final.
3. Mantenha as informações antigas intactas, apenas ADICIONE os novos dados às categorias correspondentes. A única exceção é se o paciente afirmar que um problema passou (ex: "a dor parou").

Relatório Atual:
{existing_report.content}

Novas Conversas:
{conversation_transcript}

Retorne APENAS o Relatório Diário completo reescrito:
"""
        else:
            chats_today = query.order_by(ChatHistory.timestamp.asc()).all()
            if not chats_today:
                return None, "O paciente não teve interações com a IA neste dia."

            # Transcreve a conversa completa
            conversation_transcript = "\n".join([
                f"[{c.timestamp.strftime('%H:%M')}] Paciente ({c.intent}): {c.message}\nIA: {c.response}\n" 
                for c in chats_today
            ])

            # Prompt para sumarização clínica inicial
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
        existing_context = PatientContext.query.filter_by(patient_id=patient_id).first()
        
        # Lógica Incremental: Busca apenas mensagens enviadas após a última atualização
        query = ChatHistory.query.filter_by(user_id=patient_id).order_by(ChatHistory.timestamp.asc())
        if existing_context and existing_context.updated_at:
            query = query.filter(ChatHistory.timestamp > existing_context.updated_at)
            
        new_chats = query.all()
        
        if not new_chats:
            print(f"[AI CONTEXT] Sem novas mensagens para atualizar para o paciente {patient_id}.")
            return existing_context.context_data if existing_context else None
            
        # Limita a 15 interações mais recentes para evitar estouro do prompt
        if len(new_chats) > 15:
            new_chats = new_chats[-15:]
            
        print(f"[AI CONTEXT][DEBUG] Processando {len(new_chats)} novas mensagens para o paciente {patient_id}.", flush=True)
        
        conversation_transcript = "\n".join([
            f"Paciente: {c.message}\nIA: {c.response}\n" 
            for c in new_chats
        ])
        
        # Trunca para limite máximo absoluto de 3000 caracteres (safety net)
        conversation_transcript = conversation_transcript[-3000:]

        current_json_str = "Nenhum histórico anterior."
        if existing_context and existing_context.context_data:
            # Limita as listas para não crescerem ao infinito
            truncated_data = dict(existing_context.context_data)
            if "sintomas_relatados" in truncated_data and isinstance(truncated_data["sintomas_relatados"], list):
                truncated_data["sintomas_relatados"] = truncated_data["sintomas_relatados"][-5:]
            if "medicacoes_relatadas" in truncated_data and isinstance(truncated_data["medicacoes_relatadas"], list):
                truncated_data["medicacoes_relatadas"] = truncated_data["medicacoes_relatadas"][-5:]
                
            current_json_str = json.dumps(truncated_data, ensure_ascii=False, indent=2)[:1500]

        summary_prompt = f"""
Você é um sistema de auditoria e memória de longo prazo para um Agente de Saúde Inteligente.
Sua tarefa é analisar as NOVAS CONVERSAS do paciente e ATUALIZAR/FUNDIR as informações com o CONTEXTO ATUAL.
Esse JSON será usado como a Janela de Contexto (Knowledge Base) para o agente.

Contexto Atual:
{current_json_str}

Novas Conversas:
{conversation_transcript}

INSTRUÇÃO OBRIGATÓRIA DE FORMATO E TAMANHO:
Você DEVE retornar APENAS um objeto JSON válido.
SEJA EXTREMAMENTE CONCISO E RÁPIDO. Use APENAS PALAVRAS-CHAVE curtas (máximo 2 a 3 palavras por item) nas listas.
NÃO escreva frases longas ou explicações.
Siga EXATAMENTE esta estrutura:
{{
  "nome_do_paciente": "Apenas o Nome",
  "sintomas_relatados": ["palavra-chave 1", "palavra-chave 2"],
  "medicacoes_relatadas": ["remedio 1", "remedio 2"],
  "acoes_recomendadas_pela_ia": ["acao 1", "acao 2"],
  "observacoes_adicionais": "resumo extremamente curto"
}}
"""
        response_text = self._call_llama(summary_prompt, num_predict=500, temperature=0.1, json_format=True).strip()
        print(f"[AI CONTEXT][DEBUG] Resposta JSON bruta do Ollama:\n{response_text}", flush=True)
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            context_dict = json.loads(response_text)
            
            # Atualiza a data automaticamente via Python para precisão absoluta (UTC-3)
            from datetime import timezone, timedelta
            br_tz = timezone(timedelta(hours=-3))
            context_dict["data_ultima_conversa"] = datetime.now(br_tz).date().isoformat()
            
            # Preenche o nome verdadeiro do paciente do banco (ignora a tentativa do Llama)
            try:
                from app.repositories.user_repository import UserRepository
                user_obj = UserRepository.get_user_by_id(patient_id)
                if user_obj and user_obj.name:
                    context_dict["nome_do_paciente"] = user_obj.name
                else:
                    context_dict["nome_do_paciente"] = "Paciente"
            except Exception as e:
                print(f"[AI CONTEXT] Aviso: falha ao buscar nome real do bd: {e}")
            
            print(f"[AI CONTEXT][DEBUG] JSON final consolidado e persistido no BD:\n{json.dumps(context_dict, ensure_ascii=False, indent=2)}", flush=True)
            
            if existing_context:
                existing_context.context_data = context_dict
                existing_context.updated_at = datetime.utcnow()
            else:
                new_context = PatientContext(patient_id=patient_id, context_data=context_dict)
                db.session.add(new_context)
            db.session.commit()
            print(f"[AI CONTEXT] Contexto Atualizado com Sucesso (Incremental) para paciente {patient_id}.")
            return context_dict
        except Exception as e:
            db.session.rollback()
            print(f"[AI CONTEXT ERROR] Falha ao extrair ou salvar contexto: {e}\nResposta Bruta: {response_text}")
        return existing_context.context_data if existing_context else None

    def _classify_intent(self, message):
        """Classificação de intenção via Similaridade de Embeddings + Fallback Heurístico (Sub-segundo)"""
        import unicodedata
        import numpy as np
        
        msg_lower = message.lower().strip()
        
        # 1. FAST-PATH: Saudações comuns curtas (economia máxima de processamento)
        greetings = ['oi', 'olá', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'tudo bem', 'tudo bom']
        if any(g in msg_lower for g in greetings) and len(msg_lower) < 25:
            print(f"[AI][DEBUG] Intent classificada via FAST-PATH: GREETING", flush=True)
            return "GREETING"

        # 2. CLASSIFICAÇÃO VIA EMBEDDINGS (Muito Rápida, baseada em vetores pré-calculados)
        if hasattr(rag_service, 'model') and rag_service.model is not None:
            try:
                # Exemplos semânticos para cada categoria
                intent_examples = {
                    "EMERGENCY": [
                        "estou com uma dor muito forte no peito",
                        "estou sentindo uma dor aguda insuportável",
                        "não consigo respirar, falta de ar severa",
                        "acho que estou infartando, socorro",
                        "chame a ambulância, caso urgente",
                        "estou morrendo de dor"
                    ],
                    "HEALTH_QUERY": [
                        "como eu tomo esse remédio?",
                        "quais os sintomas da dengue?",
                        "como fazer curativo em ferida?",
                        "onde encontro o protocolo do SUS?",
                        "o que é bom para dor de cabeça?",
                        "estou com febre e tosse",
                        "marcar consulta médica para exame",
                        "falar sobre tratamento para diabetes",
                        "estou com manchas vermelhas na pele"
                    ],
                    "GREETING": [
                        "olá, como vai?",
                        "tudo bem com você?",
                        "boa tarde, só passei para dar um oi",
                        "bom dia, espero que esteja bem"
                    ]
                }
                
                # Gera cache (centróides) apenas na primeira requisição
                if not hasattr(self, '_intent_embeddings_cache'):
                    self._intent_embeddings_cache = {}
                    for intent_cat, examples in intent_examples.items():
                        embeddings = rag_service.model.encode(examples)
                        mean_emb = np.mean(embeddings, axis=0)
                        # Normaliza para otimizar com Produto Escalar (Dot Product)
                        norm = np.linalg.norm(mean_emb)
                        self._intent_embeddings_cache[intent_cat] = mean_emb / norm if norm > 0 else mean_emb
                        
                # Computa o vetor para a mensagem atual
                msg_embedding = rag_service.model.encode([msg_lower])[0]
                msg_norm = np.linalg.norm(msg_embedding)
                if msg_norm > 0:
                    msg_embedding = msg_embedding / msg_norm
                    
                best_intent = "OTHER"
                best_score = -1.0
                
                # Classificador de distância
                for intent_cat, cat_embedding in self._intent_embeddings_cache.items():
                    score = np.dot(msg_embedding, cat_embedding)
                    if score > best_score:
                        best_score = score
                        best_intent = intent_cat
                        
                print(f"[AI][DEBUG] Intent classificada via EMBEDDINGS (Score: {best_score:.3f}): {best_intent}", flush=True)
                
                # Aplica um limiar de confiança (se não bater com nada fortemente, cai no OTHER ou Fallback)
                if best_score > 0.35: 
                    return best_intent
                    
            except Exception as e:
                print(f"[AI][ERROR] Falha na classificação por Embeddings: {e}. Usando Fallback.", flush=True)

        # 3. FALLBACK: HEURÍSTICA DE REGEX/STEMS (Caso o modelo RAG não esteja na memória)
        msg_unaccented = unicodedata.normalize('NFKD', msg_lower).encode('ascii', 'ignore').decode('utf-8')
        
        # Emergências
        emergencies = ['dor forte', 'dor aguda', 'falta de ar', 'infarto', 'socorro', 'urgente', 'morrendo', 'samu', 'ambulancia']
        if any(e in msg_unaccented for e in emergencies):
            print(f"[AI][DEBUG] Intent classificada via HEURÍSTICA FALLBACK: EMERGENCY", flush=True)
            return "EMERGENCY"

        # Consultas de Saúde (Stems)
        health_stems = [
            "dor", "febr", "quent", "nariz", "toss", "grip", "sintom", "remedi", "medic",
            "sus", "protocol", "diretriz", "pressao", "ferid", "inflama", "diarrei", "vomit",
            "doen", "receit", "sangue", "exame", "coracao", "alopecia", "cabel", "pele",
            "olho", "ouvid", "gargant", "osso", "muscul", "respir", "tont", "desmai",
            "enjo", "ansia", "defeca", "urin", "fez", "sangrament", "machuc", "queimadur",
            "picad", "alergi", "coceir", "manch", "vermelh", "inchac", "dormenci", "formigament",
            "fraquez", "cansac", "fadig", "emagreci", "obes", "colesterol", "diabet",
            "hipertensao", "cancer", "tumor", "cirurgi", "tratament", "curativ", "terapi",
            "psicolog", "psiquiatr", "depressa", "ansiedad", "estress", "insoni", "sono",
            "nutri", "alimenta", "diet", "vitamin", "suplement", "vacin", "imuniza",
            "covid", "dengu", "zika", "chikunguny", "malari", "tuberculos", "hiv", "aids",
            "sifili", "gonorrei", "herpes", "hpv", "peso", "gordura", "pressao", "bpm",
            "batimento", "corativo", "pos-operatorio", "gravidez", "gestacao", "parto",
            "aborto", "menstruacao", "menopausa", "andropausa", "prostata", "mama", "utero",
            "ovario", "testiculo", "penis", "vagina", "dst", "ist", "infeccao", "bacteri",
            "virus", "fungo", "parasit", "verm", "lombriga", "carrapato", "piolho", "pulga",
            "sarna", "micos", "caspa", "seborreia", "espinha", "acne", "cravo", "ruga",
            "cicatriz", "queloid", "umbigo", "unha", "calvicie", "careca", "pelada", "aguada", "esverdeada"
        ]
        
        exact_words = ["mal", "sus"]
        if any(stem in msg_unaccented for stem in health_stems):
            print(f"[AI][DEBUG] Intent classificada via HEURÍSTICA FALLBACK: HEALTH_QUERY", flush=True)
            return "HEALTH_QUERY"
            
        words = msg_unaccented.split()
        if any(w in words for w in exact_words):
            print(f"[AI][DEBUG] Intent classificada via HEURÍSTICA FALLBACK: HEALTH_QUERY", flush=True)
            return "HEALTH_QUERY"
            
        print(f"[AI][DEBUG] Intent classificada via HEURÍSTICA FALLBACK: OTHER", flush=True)
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
        response_text = self._call_llama(triage_prompt, json_format=True).strip()
        
        try:
            triage_data = json.loads(response_text)
            
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
                    sint = kb_data.get("sintomas_relatados", [])
                    meds = kb_data.get("medicacoes_relatadas", [])
                    acoes = kb_data.get("acoes_recomendadas_pela_ia", [])
                    obs = kb_data.get("observacoes_adicionais")
                    
                    bg_info = ""
                    if nome and nome != "null": bg_info += f"Paciente: {nome}. "
                    
                    # Injeção condicional pesada (só em intents de saúde)
                    if intent in ("HEALTH_QUERY", "EMERGENCY"):
                        if sint and isinstance(sint, list): bg_info += f"Sintomas Recentes (BD): {', '.join(sint)}. "
                        if meds and isinstance(meds, list): bg_info += f"Medicações (BD): {', '.join(meds)}. "
                        if acoes and isinstance(acoes, list): bg_info += f"IA Recomendou: {', '.join(acoes)}. "
                        if obs and obs != "null": bg_info += f"Obs: {obs}. "
                        
                        # Verifica staleness (TTL de 15 dias)
                        if user_context.updated_at:
                            dias_desde_atualizacao = (datetime.utcnow() - user_context.updated_at).days
                            if dias_desde_atualizacao > 15:
                                bg_info += f"[ATENÇÃO: Este contexto clínico tem {dias_desde_atualizacao} dias de atraso e pode estar desatualizado.] "
                    
                    if bg_info:
                        system_rules += f" [{bg_info.strip()}]"
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
            fontes_instruction = f'- Cite a fonte ao final: "Fontes: {fontes_str}"\n'

        system_content = f"{system_rules}\n{rag_guidance}\n{fontes_instruction}"
        if context:
            system_content += f"\n[PROTOCOLOS SUS]: {context[:1200]}\n"
        system_content += "\nREGRAS DE RESPOSTA:\n- SEJA EXTREMAMENTE BREVE E CONCISO.\n- Sua resposta deve ter obrigatoriamente no máximo 2 a 3 frases curtas.\n- Vá direto ao ponto e entregue apenas o mais essencial.\n- Não faça longas explicações."

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

    def _call_llama(self, prompt, num_predict=None, temperature=None, json_format=False):
        payload = {
            "model": self.llama_model, 
            "prompt": prompt, 
            "stream": False,
            "keep_alive": "15m" # Mantém o modelo na memória por 15 min
        }
        
        if json_format:
            payload["format"] = "json"
            
        # Adiciona opções de performance
        options = {}
        if num_predict: options["num_predict"] = num_predict
        if temperature is not None: options["temperature"] = temperature
        if options: payload["options"] = options

        try:
            res = requests.post(self.ollama_url, json=payload, timeout=90)
            if res.status_code != 200:
                print(f"[AI][ERROR] Ollama respondeu HTTP {res.status_code}: {res.text}")
            return res.json().get("response", "Desculpe, não consegui gerar uma resposta.")
        except Exception as e:
            print(f"Erro no Llama: {e}")
            return "Erro de conexão com o Llama 3.2:3b (Ollama). Verifique se ele está rodando."

    def _call_llama_chat(self, messages):
        chat_url = self.ollama_url.replace('/api/generate', '/api/chat')
        payload = {
            "model": self.llama_model, 
            "messages": messages, 
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.3,
                "num_predict": 250 # Limite afrouxado; a brevidade será controlada cognitivamente pelo modelo.
            }
        }
        try:
            res = requests.post(chat_url, json=payload, timeout=90)
            if res.status_code != 200:
                print(f"[AI][ERROR] Ollama respondeu HTTP {res.status_code}: {res.text}")
            return res.json().get("message", {}).get("content", "Desculpe, não consegui gerar uma resposta.")
        except Exception as e:
            print(f"Erro no Llama Chat: {e}")
            return "Erro de conexão com o Llama 3.2 (Ollama). Verifique se ele está rodando."


