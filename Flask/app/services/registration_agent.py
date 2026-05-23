import os
import json
import requests
import re
import google.generativeai as genai

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

# Usar llama3.2:3b como fallback local (melhor que gemma:2b para JSON/raciocínio)
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class RegistrationAgent:
    def __init__(self):
        # A lista precisa, ordenada, de todas as perguntas que devem ser feitas.
        # Estrutura: chave_do_banco: { "question": "Pergunta amigável", "type": "str/bool/int", "context": "Dica para a IA extrair", "requires_confirmation": bool }
        self.fields_sequence = [
            ("name", {"question": "Olá! Sou seu assistente virtual de cadastro por voz. Para começarmos, qual é o seu nome completo?", "type": "str", "requires_confirmation": False}),
            ("email", {"question": "Certo. Agora, qual e-mail você gostaria de usar para o cadastro? Você pode ditar ou usar o teclado na tela.", "type": "str", "requires_confirmation": True}),
            ("password", {"question": "E para finalizar esta etapa básica, qual senha você deseja cadastrar? Lembrando, antes de você me dizer, anote a senha no papel. Você também pode digitar se preferir.", "type": "str", "requires_confirmation": True}),
            ("date_of_birth", {"question": "Qual a sua completa data de nascimento? Diga no formato dia, mês e ano inteiro.", "type": "str", "context": "Extraia a data no formato YYYY-MM-DD se possível, ou retorne exatamente como o usuário falou", "requires_confirmation": False}),
            ("gender", {"question": "Com qual gênero você se identifica?", "type": "str", "requires_confirmation": False}),
            ("cpf", {"question": "Qual é o seu número de CPF? Por favor, leia os números devagar.", "type": "str", "context": "Remova qualquer pontuação e extraia apenas os 11 números", "requires_confirmation": True}),
            ("marital_status", {"question": "Qual o seu estado civil?", "type": "str", "requires_confirmation": False}),
            ("nationality", {"question": "Qual a sua nacionalidade?", "type": "str", "requires_confirmation": False}),
            ("education_level", {"question": "Qual o seu nível de escolaridade?", "type": "str", "requires_confirmation": False}),
            ("caregiver_name", {"question": "Seja em alguma emergência ou rotina, qual o nome do seu cuidador ou do contato mais próximo?", "type": "str", "requires_confirmation": False}),
            ("caregiver_phone", {"question": "E qual o telefone dessa pessoa? Não se esqueça do DDD.", "type": "str", "requires_confirmation": False}),
            ("state", {"question": "Em qual estado do Brasil você mora no momento?", "type": "str", "context": "Extraia a sigla (UF) em maiúsculas com duas letras", "requires_confirmation": False}),
            ("city", {"question": "E qual é a sua cidade?", "type": "str", "requires_confirmation": False}),
            ("neighborhood", {"question": "Qual o nome do seu bairro?", "type": "str", "requires_confirmation": False}),
            ("street", {"question": "Qual o nome da sua rua ou avenida?", "type": "str", "requires_confirmation": False}),
            ("number", {"question": "Qual o número da sua casa ou prédio?", "type": "str", "requires_confirmation": False}),
            ("zone", {"question": "O seu endereço fica em zona urbana ou zona rural?", "type": "str", "requires_confirmation": False}),
            ("num_residents", {"question": "Quantas pessoas moram na mesma casa que você?", "type": "int", "requires_confirmation": False}),
            ("has_potable_water", {"question": "Sua casa possui água potável encanada?", "type": "bool", "requires_confirmation": False}),
            ("has_sanitation", {"question": "Você tem rede de esgoto e saneamento básico na sua casa?", "type": "bool", "requires_confirmation": False}),
            ("has_garbage_collection", {"question": "A coleta de lixo passa na sua rua regularmente?", "type": "bool", "requires_confirmation": False}),
            ("has_electricity", {"question": "A sua casa possui acesso comum e seguro a energia elétrica?", "type": "bool", "requires_confirmation": False}),
            ("has_internet", {"question": "Você tem acesso à internet ou wi-fi em casa?", "type": "bool", "requires_confirmation": False}),
            ("financially_dependent", {"question": "Você depende financeiramente de outra pessoa?", "type": "bool", "requires_confirmation": False}),
            ("chronic_conditions", {"question": "Sobre o seu histórico de saúde: você tem alguma doença crônica, como pressão alta ou diabetes? Caso positivo, quais?", "type": "str", "requires_confirmation": False}),
            ("mobility_status", {"question": "Como está a sua mobilidade hoje? Você anda sozinho, ou precisa de bengala ou cadeira de rodas?", "type": "str", "requires_confirmation": False}),
            ("can_bathe_alone", {"question": "Você consegue tomar banho totalmente sozinho, sem precisar de ajuda?", "type": "bool", "requires_confirmation": False}),
            ("can_dress_alone", {"question": "E para se vestir, você consegue fazer isso sozinho?", "type": "bool", "requires_confirmation": False}),
            ("can_eat_alone", {"question": "Você consegue se alimentar de forma independente?", "type": "bool", "requires_confirmation": False}),
            ("perceived_memory", {"question": "Como você acha que está a sua memória nos últimos tempos? Tem se esquecido de muitas coisas?", "type": "str", "requires_confirmation": False}),
            ("mental_diagnoses", {"question": "Você foi diagnosticado com alguma questão de saúde mental, como depressão ou ansiedade?", "type": "str", "requires_confirmation": False}),
            ("physical_activity_frequency", {"question": "Pensando na semana, com qual frequência você realiza atividades físicas?", "type": "str", "requires_confirmation": False}),
            ("sleep_quality", {"question": "Como anda a qualidade do seu sono? Costuma dormir bem à noite?", "type": "str", "requires_confirmation": False}),
            ("alcohol_consumption", {"question": "Você costuma consumir bebidas alcoólicas com que frequência?", "type": "str", "requires_confirmation": False}),
            ("smoking", {"question": "Você possui o hábito de fumar?", "type": "str", "requires_confirmation": False}),
            ("frequent_visits", {"question": "Você costuma receber visitas de amigos ou familiares com certa frequência na sua casa?", "type": "bool", "requires_confirmation": False}),
            ("community_activities", {"question": "Por fim, você participa de atividades em comunidade, como igreja ou convívio em grupos do bairro?", "type": "bool", "requires_confirmation": False}),
        ]

    def _call_gemini(self, prompt):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Erro no Gemini: {e}")
            return None

    def _call_ollama(self, prompt, is_json=True):
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 1024
            }
        }
        if is_json:
            payload["format"] = "json"

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=90)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "")
            else:
                print(f"Erro na resposta do Ollama no onboarding: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Erro no Ollama Onboarding: {e}")
        return None

    def process_step(self, user_answer, current_step_index):
        if current_step_index >= len(self.fields_sequence):
             return None
             
        field_key, field_data = self.fields_sequence[current_step_index]
        expected_type = field_data["type"]
        context_hint = field_data.get("context", "")

        system_prompt = f"""
Você é um extrator de dados altamente preciso especializado em decodificar transcrições de áudio (Speech-to-Text) com ruídos e ditados fonéticos literais.

O sistema perguntou: "{field_data['question']}"
A transcrição do áudio do usuário foi: "{user_answer}"

O objetivo é extrair o valor limpo e exato para o campo: "{field_key}".
O tipo de dado esperado é: {expected_type}.
Dica de contexto: {context_hint}

REGRA DE TRADUÇÃO FONÉTICA (CRÍTICA PARA EMAILS E SENHAS):
Muitas vezes o usuário dita caracteres especiais e o sistema de voz escreve a palavra por extenso. Você deve traduzir:
- "arroba" -> "@"
- "ponto" -> "."
- "asterisco" -> "*"
- "underline" ou "traço embaixo" -> "_"
- "traço" ou "hífen" -> "-"
- "A maiúsculo" -> "A" (letras com indicação de maiúscula devem ser capitalizadas)
- "b de bola", "j de jacaré" -> "b", "j" (pegue apenas a letra correspondente)
- Espaços em senhas ou emails ditados devem ser removidos.
Exemplo 1: "josé ponto silva arroba gmail ponto com" -> "jose.silva@gmail.com"
Exemplo 2: "minha senha é 1 2 3 Mudar asterisco" -> "123Mudar*"
Exemplo 3: "A maiúsculo b minúsculo 1 2 arroba" -> "Ab12@"

Extraia apenas o valor correspondente. Se a resposta não contiver a informação pedida ou for ininteligível, retorne null.
SUA RESPOSTA DEVE SER ESTRITAMENTE UM JSON VÁLIDO E MAIS NADA. NÃO ADICIONE TEXTO ANTES OU DEPOIS.
Formato exato esperado:
{{
  "{field_key}": "valor extraído"
}}
"""
        if GEMINI_API_KEY:
            print("[RegistrationAgent] Utilizando GEMINI API para extração.")
            json_resp = self._call_gemini(system_prompt)
        else:
            print(f"[RegistrationAgent] Utilizando Ollama local ({MODEL_NAME}) para extração.")
            json_resp = self._call_ollama(system_prompt, is_json=True)
            
        extracted_val = None
        
        try:
            if json_resp:
                clean_json = json_resp.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()
                
                parsed = json.loads(clean_json)
                extracted_val = parsed.get(field_key)
                print(f"[RegistrationAgent] Extraindo passo {current_step_index} ({field_key}) | Raw: {user_answer} | JSON gerado: {clean_json} | Extraído: {extracted_val}")
        except Exception as e:
            print(f"[RegistrationAgent] JSON falhou: {e} -> Raw response: {json_resp}")
            
        # Limpeza / Casting manual
        if extracted_val is not None:
             if expected_type == "bool":
                  if isinstance(extracted_val, bool):
                       pass
                  elif isinstance(extracted_val, str):
                       v = extracted_val.lower().strip()
                       if v in ['sim', 'true', '1', 'yes', 's']:
                           extracted_val = True
                       elif v in ['não', 'nao', 'false', '0', 'no', 'n']:
                           extracted_val = False
                       else:
                           extracted_val = False
             elif expected_type == "int":
                  if isinstance(extracted_val, int):
                      pass
                  else:
                      try:
                          extracted_val = int(re.sub(r'[^0-9]', '', str(extracted_val)))
                      except:
                          extracted_val = None
             else: # str
                 extracted_val = str(extracted_val).strip()
                 if extracted_val.lower() in ['pular', 'não tenho', 'nenhum', 'nada']:
                     extracted_val = None

        return extracted_val

    def get_question_for_step(self, step_index):
         if step_index < len(self.fields_sequence):
              return self.fields_sequence[step_index][1]["question"]
         return "Cadastro concluído!"

    def get_field_key_for_step(self, step_index):
         if step_index < len(self.fields_sequence):
              return self.fields_sequence[step_index][0]
         return None

    def requires_confirmation(self, step_index):
         if step_index < len(self.fields_sequence):
              return self.fields_sequence[step_index][1].get("requires_confirmation", False)
         return False

    def handle_chat_interaction(self, user_message, state, voice_service):
        current_step = state.get('current_step', 0)
        sub_state = state.get('sub_state', 'ASKING')
        total_steps = len(self.fields_sequence)
        field_key = self.get_field_key_for_step(current_step)
        requires_conf = self.requires_confirmation(current_step)

        if sub_state == 'ASKING':
            extracted_val = self.process_step(user_message, current_step)

            if field_key == 'cpf' and extracted_val:
                cpf_clean = re.sub(r'[^0-9]', '', str(extracted_val))
                if len(cpf_clean) != 11:
                    msg = "O CPF informado não parece ter 11 números. Por favor, repita o seu CPF devagar."
                    return {'response': msg, 'audio_b64': voice_service.generate_base64_audio(msg), 'status': 'IN_PROGRESS', 'progress': int((current_step / total_steps) * 100), 'state_changed': False}

            if requires_conf and extracted_val is not None:
                state['sub_state'] = 'CONFIRMING'
                state['temp_val'] = extracted_val
                
                if field_key == 'password':
                    spelled_pw = " ".join(list(str(extracted_val)))
                    conf_msg = f"Eu entendi que a sua senha é: {spelled_pw}. Falei certo? Responda sim ou não."
                else:
                    conf_msg = f"Eu entendi: {extracted_val}. Falei certo? Responda sim ou não."
                    
                return {'response': conf_msg, 'audio_b64': voice_service.generate_base64_audio(conf_msg), 'status': 'IN_PROGRESS', 'progress': int((current_step / total_steps) * 100), 'state_changed': True}
            else:
                state['collected_data'][field_key] = extracted_val
                state['current_step'] += 1
                state['sub_state'] = 'ASKING'
                state['temp_val'] = None
                return {'state_changed': True, 'continue': True}

        elif sub_state == 'CONFIRMING':
            user_lower = user_message.lower().strip()
            is_yes = any(w in user_lower for w in ['sim', 'isso', 'certo', 'correto', 'positivo', 'é', 'exato', 'uhum'])
            is_no = any(w in user_lower for w in ['não', 'nao', 'errado', 'negativo', 'incorreto'])

            if is_yes and not is_no:
                state['collected_data'][field_key] = state['temp_val']
                state['current_step'] += 1
                state['sub_state'] = 'ASKING'
                state['temp_val'] = None
                return {'state_changed': True, 'continue': True}
            elif is_no:
                state['sub_state'] = 'ASKING'
                state['temp_val'] = None
                retry_msg = "Desculpe pelo erro. Por favor, me diga novamente."
                return {'response': retry_msg, 'audio_b64': voice_service.generate_base64_audio(retry_msg), 'status': 'IN_PROGRESS', 'progress': int((current_step / total_steps) * 100), 'state_changed': True}
            else:
                conf_msg = "Desculpe, não entendi se está correto. Responda apenas sim ou não."
                return {'response': conf_msg, 'audio_b64': voice_service.generate_base64_audio(conf_msg), 'status': 'IN_PROGRESS', 'progress': int((current_step / total_steps) * 100), 'state_changed': False}

        return {'state_changed': False}

registration_agent = RegistrationAgent()
