import logging
import sys

def init_logger(app):
    """
    Configura o sistema de logging padrão do Python e o atrela à aplicação Flask.
    """
    # Define o nível de log básico
    log_level = logging.DEBUG if app.debug else logging.INFO

    # Remove os handlers padrão do Flask para evitar duplicação se existirem
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    # Cria um handler para o console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Define um formato profissional para os logs
    # Ex: [2026-05-23 10:00:00] INFO in module_name: message
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    console_handler.setFormatter(formatter)

    # Adiciona o handler no logger do app
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)
    
    # Adiciona logger configurado também na raiz (para pacotes que não tenham acesso direto ao app)
    logging.basicConfig(level=log_level, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s', handlers=[console_handler])

    app.logger.info("✅ Sistema de logging profissional inicializado.")
