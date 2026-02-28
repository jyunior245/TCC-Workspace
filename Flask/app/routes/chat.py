from flask import Blueprint, request, jsonify
from app.services.ai_service import HealthAgent

chat_bp = Blueprint('chat', __name__)
agent = HealthAgent()

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'Mensagem vazia'}), 400
    
    response = agent.get_response(user_message)
    return jsonify({'response': response})