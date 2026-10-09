import os
import re
import hashlib
import edge_tts
from typing import Optional

AUDIO_CACHE_DIR = os.path.join("backend", "static", "audio")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

class TTSService:
    VOICES = {
        "francisca": "pt-BR-FranciscaNeural",
        "antonio": "pt-BR-AntonioNeural",
        "thalita": "pt-BR-ThalitaNeural"
    }

    def clean_markdown(self, text: str) -> str:
        """Remove markdown syntax and prepare text for natural speech synthesis."""
        if not text:
            return ""
        # Remove code blocks or JSON
        t = re.sub(r'```[\s\S]*?```', '', text)
        # Remove headers
        t = re.sub(r'#+\s*', '', t)
        # Remove bold and italic markers
        t = re.sub(r'[*_]{1,3}', '', t)
        # Clean bullet points and numeric lists
        t = re.sub(r'^\s*[-*•]\s+', '', t, flags=re.MULTILINE)
        t = re.sub(r'^\s*\d+\.\s+', '', t, flags=re.MULTILINE)
        # Replace multiple newlines with periods
        t = re.sub(r'\n+', '. ', t)
        # Remove duplicate spaces
        t = re.sub(r'\s+', ' ', t)
        return t.strip()

    def extract_section(self, text: str, section: str) -> str:
        """Extract a specific section like 'trends' or 'recommendations' from markdown."""
        if not text or section == "all":
            return self.clean_markdown(text)
        
        lines = text.split('\n')
        extracted_lines = []
        capturing = False
        target_keywords = {
            "trends": ["tendência", "tendencia", "tendências", "ponto de atenção", "pontos de atenção"],
            "recommendations": ["recomendação", "recomendações", "recomendacoes", "ação prática", "ações práticas", "acoes praticas"]
        }
        keywords = target_keywords.get(section.lower(), [])

        for line in lines:
            line_clean = line.strip().lower()
            if line.strip().startswith(('#', '###', '##')):
                if any(kw in line_clean for kw in keywords):
                    capturing = True
                    continue
                elif capturing:
                    break
            if capturing:
                extracted_lines.append(line)
        
        if not extracted_lines:
            return self.clean_markdown(text)
        return self.clean_markdown("\n".join(extracted_lines))

    async def synthesize(self, text: str, voice: str = "pt-BR-FranciscaNeural") -> bytes:
        """Generate mp3 audio bytes with local file caching."""
        cleaned_text = self.clean_markdown(text)
        if not cleaned_text:
            return b""

        # Hash for cache
        cache_key = hashlib.md5(f"{voice}_{cleaned_text}".encode('utf-8')).hexdigest()
        cache_file = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.mp3")

        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
            with open(cache_file, "rb") as f:
                return f.read()

        communicate = edge_tts.Communicate(cleaned_text, voice)
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        result = bytes(audio_data)
        if len(result) > 0:
            with open(cache_file, "wb") as f:
                f.write(result)

        return result
