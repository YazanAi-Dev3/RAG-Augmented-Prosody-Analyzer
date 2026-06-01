import google.generativeai as genai
import json
import re
from typing import Dict, Any
from app.core.config import settings

class GeminiFallbackEngine:
    def __init__(self):
        print("--- Initializing Gemini Fallback Engine ---")
        # Configure the Google Generative AI SDK with the API key from .env
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # We use gemini-2.0-flash-lite for optimal speed and massive context window capabilities
        self.model = genai.GenerativeModel('gemini-flash-lite-latest')

    def _clean_json_output(self, response_text: str) -> str:
        """Removes markdown formatting if the LLM wraps the JSON output."""
        cleaned = re.sub(r"```json", "", response_text)
        cleaned = re.sub(r"```", "", cleaned)
        return cleaned.strip()

    async def process_request(self, target_text: str, context: str, is_full_poem: bool) -> Dict[str, Any]:
        """
        Calls Gemini API as a fallback when local LLM confidence is low or fails.
        Handles both single verses and full poems seamlessly.
        """
        sys_instruction = (
            "You are an expert critic of Arabic poetry. "
            "You MUST write your entire response in Arabic. "
            "Analyze the provided text deeply. You may use the provided reference context "
            "to guide your understanding of difficult words or themes. "
            "Output strictly in valid JSON format with NO markdown wrapping."
        )
        
        # Adjust the context awareness based on the user's flag
        poem_type = "Full Poem (Multiple Verses)" if is_full_poem else "Single Verse"
        
        prompt = f"""
        System Instruction: {sys_instruction}
        
        Input Type: {poem_type}
        Target Text: {target_text}
        
        Retrieved Reference Context (Use as knowledge base):
        {context}
        
        JSON Output Schema requirement:
        {{
            "explanation": "Detailed Arabic explanation and analysis",
            "theme": "The main theme or purpose",
            "confidence": 0.99
        }}
        """
        
        try:
            # Using async generation to prevent blocking the FastAPI event loop
            response = await self.model.generate_content_async(prompt)
            cleaned_response = self._clean_json_output(response.text)
            
            analysis_dict = json.loads(cleaned_response)
            return analysis_dict
            
        except Exception as e:
            print(f"Gemini API Critical Error: {str(e)}")
            # Safe fallback response in case the fallback itself fails!
            return {
                "explanation": "Error: Failed to process request via Gemini Fallback.",
                "theme": "Unknown",
                "confidence": 0.0
            }

# Instantiated engine ready for import
gemini_fallback_engine = GeminiFallbackEngine()