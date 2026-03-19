from authlib.integrations.flask_client import OAuth
import json
import os

oauth = OAuth()

def init_google_auth(app):
    # __file__ é Flask/app/extensions/google_auth.py (ou /app/app/extensions/google_auth.py no Docker)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(base_dir, 'oauth-client-key.json')
    
    # Debug info
    print(f"[OAuth] BASE_DIR: {base_dir}")
    print(f"[OAuth] Tentando carregar JSON em: {json_path}")
    
    if not os.path.exists(json_path):
        print(f"[OAuth] Arquivo não encontrado no caminho calculado. Tentando padrões comuns...")
        fallbacks = [
            'oauth-client-key.json',
            '../oauth-client-key.json',
            '/app/oauth-client-key.json',
            '/oauth-client-key.json'
        ]
        for fb in fallbacks:
            if os.path.exists(fb):
                json_path = fb
                print(f"[OAuth] Encontrado em fallback: {json_path}")
                break

    try:
        if not os.path.exists(json_path):
            print("ERREUR CRITIQUE [OAuth]: Arquivo oauth-client-key.json NÃO ENCONTRADO em nenhum local conhecido.")
            return # Não registra o cliente 'google', causando o AttributeError reportado

        with open(json_path, 'r') as f:
            config = json.load(f)
        
        web_config = config.get('web', {})
        if not web_config:
            print("ERREUR CRITIQUE [OAuth]: Chave 'web' não encontrada no JSON.")
            return
            
        oauth.init_app(app)
        oauth.register(
            name='google',
            client_id=web_config.get('client_id'),
            client_secret=web_config.get('client_secret'),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        print("[OAuth] Cliente 'google' registrado com sucesso!")
    except Exception as e:
        print(f"ERRO CRÍTICO ao registrar cliente Google: {e}")
