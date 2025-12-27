from flask import Blueprint, jsonify, request
from app.services.voice_processor import analyze_text

index_bp = Blueprint('index', __name__)
voice_bp = Blueprint('voice', __name__)

@index_bp.route('/')
def index():
    return jsonify({"status": "online", "service": "Flask AI Agent"})

@voice_bp.route('/process-voice', methods=['POST'])
def process_voice():
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400

    analysis = analyze_text(text)
    
    return jsonify({
        "original_text": text,
        "analysis": analysis
    }), 200
