from flask import Blueprint, request, jsonify, session, render_template, Response, stream_with_context
from app.services.ai_service import HealthAgent
from app.services.voice_service import VoiceService
import asyncio
import uuid
import time
import queue
import threading

chat_bp = Blueprint('chat', __name__)
agent = HealthAgent()
voice = VoiceService(init_pygame=False)

# Cache temporário para o áudio (evita passar texto gigante na URL)
audio_sessions = {}

@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized. Usuário não autenticado.'}), 401

    user_id = session.get('user_id')
    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'Mensagem vazia'}), 400
    
    # Chama o agente para obter o texto
    response = agent.get_response(user_message, user_id=user_id)
    
    # 5. DISPARA PRÉ-AQUECIMENTO DO ÁUDIO (Background Thread)
    audio_id = str(uuid.uuid4())
    audio_q = queue.Queue(maxsize=20)
    
    def producer_worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        first_sent = False
        t_start = time.time()
        try:
            async def run_gen():
                nonlocal first_sent
                gen = voice.stream_audio_generator(response)
                async for chunk in gen:
                    if not first_sent:
                        print(f"[AUDIO][DEBUG] PRE-WARM: Primeiro chunk gerado em {(time.time() - t_start)*1000:.1f}ms.", flush=True)
                        first_sent = True
                    audio_q.put(chunk)
            loop.run_until_complete(run_gen())
        except Exception as e:
            print(f"Erro no pre-warm de áudio: {e}")
        finally:
            audio_q.put(None)
            loop.close()

    # Inicia a geração ANTES de responder o JSON
    thread = threading.Thread(target=producer_worker)
    thread.start()

    audio_sessions[audio_id] = {
        'text': response,
        'created_at': time.time(),
        'queue': audio_q,
        'thread': thread
    }
    
    # Limpeza simples de cache
    if len(audio_sessions) > 50:
        first_key = next(iter(audio_sessions))
        del audio_sessions[first_key]
        
    return jsonify({
        'response': response,
        'audio_id': audio_id
    })

@chat_bp.route('/api/audio/stream', methods=['GET'])
def stream_audio():
    """Endpoint que transmite o áudio pré-aquecido ou gera se necessário."""
    t_req = time.time()
    audio_id = request.args.get('id')
    audio_data = audio_sessions.get(audio_id)
    
    if not audio_data:
        return "Áudio expirado ou texto ausente", 404
    
    # Tenta usar a fila pré-aquecida
    q = audio_data.get('queue')
    t_ready = audio_data.get('created_at', time.time())
    
    print(f"[AUDIO][DEBUG] Request do browser recebida {(time.time() - t_ready)*1000:.1f}ms após texto pronto.", flush=True)

    def generate():
        if q:
            # Consome da fila já existente (Pre-warmed)
            print(f"[AUDIO][DEBUG] Usando stream PRÉ-AQUECIDO para ID {audio_id}.", flush=True)
            while True:
                item = q.get()
                if item is None:
                    break
                yield item
        else:
            # Fallback (caso o pre-warm falhe ou não tenha sido acionado)
            print(f"[AUDIO][WARNING] Pre-warm não encontrado para {audio_id}, gerando agora...", flush=True)
            q_fallback = queue.Queue(maxsize=10)
            def fallback_producer():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    async def run_gen():
                        gen = voice.stream_audio_generator(audio_data['text'])
                        async for chunk in gen:
                            q_fallback.put(chunk)
                    loop.run_until_complete(run_gen())
                finally:
                    q_fallback.put(None)
                    loop.close()
            threading.Thread(target=fallback_producer).start()
            while True:
                item = q_fallback.get()
                if item is None:
                    break
                yield item

    return Response(stream_with_context(generate()), mimetype="audio/mpeg")
        # OBS: Não deleta o ID imediatamente para permitir múltiplos requests do browser


    return Response(stream_with_context(generate()), mimetype="audio/mpeg")

@chat_bp.route('/api/audio', methods=['POST'])
def generate_audio():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    text = data.get('text')
    if not text:
        return jsonify({'error': 'Texto ausente'}), 400

    print(f"🔊 Gerando áudio de resposta em background...")
    audio_b64 = voice.generate_base64_audio(text)
    
    return jsonify({
        'audio_b64': audio_b64
    })

@chat_bp.route('/voice', methods=['GET'])
def voice_page():
    return render_template('voice.html')

@chat_bp.route('/api/chat/end', methods=['POST'])
def end_chat():
    """Encerrar a conversa e atualizar a Janela de Contexto (KB) de modo síncrono ou assíncrono."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized. Usuário não autenticado.'}), 401

    user_id = session.get('user_id')
    
    # Executa a atualização do contexto assincronamente (em uma thread) 
    # para não travar a UI (pois consulta o LLM na summarização)
    def run_context_update():
        print(f"[CHAT END] Iniciando atualização de janela de contexto para user={user_id}...")
        try:
            from app.extensions.sql_alchemy import app # Precisamos do context da app principal para DB
        except ImportError:
            pass
            
        with db.session.begin_nested() if db.session.is_active else db.session.begin():
            pass
        # Aqui, como rodamos no background, precisamos do active app_context
        # Mas `flask_current_app` não pode ser acessada em nova Thread sem injetar.
        # Então, como solução SIMPLES para o TCC, podemos chamar de forma SÍNCRONA,
        # ou, recuperar a APP via current_app antes de criar a thread.
        
    # Recupenrando o app para ser invocado na thread
    from flask import current_app
    app = current_app._get_current_object()
    
    def process_background():
        with app.app_context():
            print(f"[CHAT END] Iniciando atualização de janela de contexto (KB) para user {user_id}", flush=True)
            agent.update_patient_context(user_id)
            
    thread = threading.Thread(target=process_background)
    thread.start()
    
    return jsonify({'status': 'success', 'message': 'Contexto do paciente está sendo processado.'})
    return jsonify({'status': 'success', 'message': 'Contexto do paciente está sendo processado.'})
