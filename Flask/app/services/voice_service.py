
import speech_recognition as sr
import edge_tts
import asyncio
import pygame
import os
import tempfile

class VoiceService:
    def __init__(self, init_pygame=True):
        # Voz natural em português do Brasil (Feminina)
        self.voice = "pt-BR-FranciscaNeural"
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.2
        if init_pygame:
            pygame.mixer.init()

    def listen(self):
        """Ouve o microfone do usuário e retorna o texto transcrito."""
        with sr.Microphone() as source:
            print("\n🎤 Ajustando para ruído ambiente... aguarde um segundo.")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("🎤 Pode falar...")
            
            try:
                # Escuta o usuário (timeout=5s para começar a falar, limitamos a frase a 15s)
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=30)
                print("🎧 Processando o áudio, aguarde...")
                
                # Reconhecimento usando Google (gratuito, sem necessidade de chave)
                text = self.recognizer.recognize_google(audio, language="pt-BR")
                return text
                
            except sr.WaitTimeoutError:
                print("⏳ Tempo esgotado. Nenhuma fala foi detectada.")
                return ""
            except sr.UnknownValueError:
                print("🤷 Não consegui entender o que foi dito.")
                return ""
            except sr.RequestError as e:
                print(f"❌ Erro de conexão com o serviço de reconhecimento de voz: {e}")
                return ""

    def _sanitize_text(self, text):
        lines = []
        for ln in text.splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith(("U:", "A:", "USUÁRIO:", "ASSISTENTE:", "Fontes:")):
                continue
            lines.append(s)
        cleaned = " ".join(lines)
        return cleaned

    async def _generate_audio(self, text, output_file):
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_file)

    async def stream_audio_generator(self, text):
        """Gera o áudio em chunks (streaming) para o Flask."""
        cleaned = self._sanitize_text(text)
        if not cleaned:
            return
            
        communicate = edge_tts.Communicate(cleaned, self.voice)
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                data = chunk.get("data")
                if data:
                    yield data

    def generate_base64_audio(self, text):
        """Transforma texto em áudio natural e retorna em base64."""
        import base64
        if not text:
            return None

        cleaned = self._sanitize_text(text)
        if not cleaned:
            return None

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_filename = fp.name

        try:
            # edge-tts é assíncrono
            asyncio.run(self._generate_audio(cleaned, temp_filename))
            
            # Read file as base64
            with open(temp_filename, "rb") as f:
                audio_bytes = f.read()
                audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            return audio_b64
        except Exception as e:
            print(f"Erro ao gerar áudio base64: {e}")
            return None
        finally:
            if os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                except Exception:
                    pass

    def speak(self, text):
        """Transforma texto em áudio natural e reproduz imediatamente."""
        if not text:
            return

        cleaned = self._sanitize_text(text)
        if not cleaned:
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_filename = fp.name

        try:
            # edge-tts é assíncrono
            asyncio.run(self._generate_audio(cleaned, temp_filename))
            
            # Reproduzir o áudio gerado com pygame
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            
            # Aguardar o fim da reprodução
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            # Descarrega o arquivo da memória do pygame para conseguir deletar
            pygame.mixer.music.unload()
            
        finally:
            # Remove o arquivo temporário
            if os.path.exists(temp_filename):
                try:
                    os.remove(temp_filename)
                except Exception:
                    pass
