import os
import json
import requests
import re
from app.extensions.sql_alchemy import db

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

# Usar mistral conforme instrução do usuário
MODEL_NAME = "gemma:2b"

class RegistrationAgent:
    def __init__(self):
        # A lista precisa, ordenada, de todas as perguntas que devem ser feitas.
        # Estrutura: chave_do_banco: { "question": "Pergunta amigável", "type": "str/bool/int", "context": "Dica para a IA extrair" }
        self.fields_sequence = [
            ("name", {"question": "Olá! Sou seu assistente virtual de cadastro por voz. Para comerçarmos, qual é o seu nome completo?", "type": "str"}),
            ("email", {"question": "Certo. Agora, qual e-mail você gostaria de usar para o cadastro?", "type": "str"}),
            ("password", {"question": "E para finalizar esta etapa básica, qual senha você deseja cadastrar? Lembrando, antes de você me dizer, anote a senha no papel", "type": "str"}),
            ("date_of_birth", {"question": "Qual a sua completa data de nascimento? Diga no formato dia, mês e ano inteiro.", "type": "str", "context": "Extraia a data no formato YYYY-MM-DD se possível, ou retorne exatamente como o usuário falou"}),
            ("gender", {"question": "Com qual gênero você se identifica?", "type": "str"}),
            ("cpf", {"question": "Qual é o seu número de CPF? Por favor, leia os números devagar.", "type": "str", "context": "Remova qualquer pontuação e extraia apenas os 11 números"}),
            ("marital_status", {"question": "Qual o seu estado civil?", "type": "str"}),
            ("nationality", {"question": "Qual a sua nacionalidade?", "type": "str"}),
            ("education_level", {"question": "Qual o seu nível de escolaridade?", "type": "str"}),
            ("caregiver_name", {"question": "Seja em alguma emergência ou rotina, qual o nome do seu cuidador ou do contato mais próximo?", "type": "str"}),
            ("caregiver_phone", {"question": "E qual o telefone dessa pessoa? Não se esqueça do DDD.", "type": "str"}),
            ("state", {"question": "Em qual estado do Brasil você mora no momento?", "type": "str", "context": "Extraia a sigla (UF) em maiúsculas com duas letras"}),
            ("city", {"question": "E qual é a sua cidade?", "type": "str"}),
            ("neighborhood", {"question": "Qual o nome do seu bairro?", "type": "str"}),
            ("street", {"question": "Qual o nome da sua rua ou avenida?", "type": "str"}),
            ("number", {"question": "Qual o número da sua casa ou prédio?", "type": "str"}),
            ("zone", {"question": "O seu endereço fica em zona urbana ou zona rural?", "type": "str"}),
            ("num_residents", {"question": "Quantas pessoas moram na mesma casa que você?", "type": "int"}),
            ("has_potable_water", {"question": "Sua casa possui água potável encanada?", "type": "bool"}),
            ("has_sanitation", {"question": "Você tem rede de esgoto e saneamento básico na sua casa?", "type": "bool"}),
            ("has_garbage_collection", {"question": "A coleta de lixo passa na sua rua regularmente?", "type": "bool"}),
            ("has_electricity", {"question": "A sua casa possui acesso comum e seguro a energia elétrica?", "type": "bool"}),
            ("has_internet", {"question": "Você tem acesso à internet ou wi-fi em casa?", "type": "bool"}),
            ("financially_dependent", {"question": "Você depende financeiramente de outra pessoa?", "type": "bool"}),
            ("chronic_conditions", {"question": "Sobre o seu histórico de saúde: você tem alguma doença crônica, como pressão alta ou diabetes? Caso positivo, quais?", "type": "str"}),
            ("mobility_status", {"question": "Como está a sua mobilidade hoje? Você anda sozinho, ou precisa de bengala ou cadeira de rodas?", "type": "str"}),
            ("can_bathe_alone", {"question": "Você consegue tomar banho totalmente sozinho, sem precisar de ajuda?", "type": "bool"}),
            ("can_dress_alone", {"question": "E para se vestir, você consegue fazer isso sozinho?", "type": "bool"}),
            ("can_eat_alone", {"question": "Você consegue se alimentar de forma independente?", "type": "bool"}),
            ("perceived_memory", {"question": "Como você acha que está a sua memória nos últimos tempos? Tem se esquecido de muitas coisas?", "type": "str"}),
            ("mental_diagnoses", {"question": "Você foi diagnosticado com alguma questão de saúde mental, como depressão ou ansiedade?", "type": "str"}),
            ("physical_activity_frequency", {"question": "Pensando na semana, com qual frequência você realiza atividades físicas?", "type": "str"}),
            ("sleep_quality", {"question": "Como anda a qualidade do seu sono? Costuma dormir bem à noite?", "type": "str"}),
            ("alcohol_consumption", {"question": "Você costuma consumir bebidas alcoólicas com que frequência?", "type": "str"}),
            ("smoking", {"question": "Você possui o hábito de fumar?", "type": "str"}),
            ("frequent_visits", {"question": "Você costuma receber visitas de amigos ou familiares com certa frequência na sua casa?", "type": "bool"}),
            ("community_activities", {"question": "Por fim, você participa de atividades em comunidade, como igreja ou convívio em grupos do bairro?", "type": "bool"}),
        ]

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
Você é um extrator de dados assistente.
O sistema perguntou ao usuário: "{field_data['question']}"
A transcrição da resposta do usuário foi: "{user_answer}"

ATENÇÃO: A transcrição de áudio pode conter erros absurdos. Por exemplo, nomes, senhas, emails e endereçamento precisam ser escritos corretamente, não traduza para o português. 
O usuário também pode ter usado o teclado para corrigir e digitado diretamente. 
Se ele disser "o meu nome é X", extraia apenas "X". Se for uma senha ou e-mail, extraia exatamente a string sem espaços.

O objetivo é extrair o valor limpo e exato para o campo: "{field_key}".
O tipo de dado esperado é: {expected_type}.
Dica: {context_hint}

SUA RESPOSTA DEVE SER ESTRITAMENTE UM JSON VÁLIDO E MAIS NADA. NÃO EXPLIQUE. NÃO ADICIONE TEXTO.
Se a resposta não contiver a informação pedida, retorne null.
Formato:
{{
  "{field_key}": "valor extraído"
}}
"""
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
                print(f"[RegistrationAgent] Extraindo passo {current_step_index} | Raw: {user_answer} | JSON gerado: {clean_json} | Extraído: {extracted_val}")
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

registration_agent = RegistrationAgent()
