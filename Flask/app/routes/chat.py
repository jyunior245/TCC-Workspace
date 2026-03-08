from flask import Blueprint, request, jsonify, session, render_template
from app.services.ai_service import HealthAgent
from app.services.voice_service import VoiceService

chat_bp = Blueprint('chat', __name__)
agent = HealthAgent()
voice = VoiceService(init_pygame=False)

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message')
    user_id = session.get('user_id') or "user_voice"
    
    if not user_message:
        return jsonify({'error': 'Mensagem vazia'}), 400
    
    print(f"\n👴 Você disse (Web): {user_message}")
    print("🔍 Analisando intenção e buscando contexto no agente...")
    
    response = agent.get_response(user_message, user_id=user_id)
    print(f"\n🤖 Assistente: {response}\n")
    
    print("🔊 Gerando áudio de resposta...")
    audio_b64 = voice.generate_base64_audio(response)
    print("-" * 50)
    
    return jsonify({
        'response': response,
        'audio_b64': audio_b64
    })

@chat_bp.route('/voice', methods=['GET'])
def voice_page():
    return render_template('voice.html')
