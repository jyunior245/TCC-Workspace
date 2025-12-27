def analyze_text(text):
    text = text.lower()
    
    response = {
        "intent": "unknown",
        "action": None,
        "risk_level": "low",
        "feedback": "Não entendi, pode repetir?"
    }

    # RF19 - Identificação de sintomas comuns (Rule-based)
    sintomas_alertas = ["dor no peito", "falta de ar", "desmaio", "sangramento"]
    sintomas_comuns = ["dor de cabeça", "febre", "tosse", "enjoo"]

    for sintoma in sintomas_alertas:
        if sintoma in text:
            response["intent"] = "report_symptom"
            response["risk_level"] = "high"
            response["feedback"] = f"Entendi que você está com {sintoma}. Isso é um sinal de alerta. Vou notificar o ACS imediatamente."
            response["action"] = "notify_acs_emergency"
            return response

    for sintoma in sintomas_comuns:
        if sintoma in text:
            response["intent"] = "report_symptom"
            response["risk_level"] = "medium"
            response["feedback"] = f"Registrei que você está com {sintoma}. Recomendamos repouso e hidratação. Se piorar, procure a UBS."
            response["action"] = "log_symptom"
            return response

    # RF02/RF09 - Comandos de voz
    if "ajuda" in text or "socorro" in text:
        response["intent"] = "emergency"
        response["risk_level"] = "high"
        response["feedback"] = "Chamando ajuda imediatamente."
        response["action"] = "call_emergency"
        return response
    
    if "água" in text or "beber" in text:
        response["intent"] = "log_hydration"
        response["feedback"] = "Registrei que você bebeu água. Parabéns!"
        response["action"] = "log_water"
        return response

    return response
