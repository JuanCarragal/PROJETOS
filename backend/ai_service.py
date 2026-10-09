import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

class AIService:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def generate_insights(self, analysis_data: Dict[str, Any]) -> str:
        """
        Generates narrative insights based on the provided analysis data.
        """
        if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "YOUR_API_KEY_HERE":
            return "Erro: Chave de API do Google não configurada no arquivo .env."

        prompt = f"""
        Você é um consultor analista de negócios sênior. 
        Analise os seguintes dados extraídos de uma planilha financeira/operacional e forneça insights estratégicos.
        
        DADOS DE ANÁLISE:
        {analysis_data}
        
        REQUISITOS:
        1. Identifique as 3 principais tendências ou pontos de atenção.
        2. Destaque o desempenho dos principais fornecedores ou operações.
        3. Sugira 2 ações práticas para melhoria baseadas nos números.
        4. Use um tom profissional, direto e em português do Brasil.
        
        Formate a resposta com títulos claros.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Erro ao gerar insights com IA: {str(e)}"
