import httpx
import asyncio
import json
import re
from typing import List, Dict, Any, Set
from app.core.config import settings

class LocalLLMEngine:
    def __init__(self):
        self.api_url = f"{settings.OLLAMA_HOST}/api/generate"
        self.model = settings.LOCAL_LLM_MODEL
        self.timeout = 600 # Extended timeout for heavy LLM operations
        
    async def _call_ollama(self, prompt: str, system_instruction: str = "") -> str:
        """Makes an asynchronous HTTP POST request to the local Ollama instance."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False,
            "options": {
                "temperature": 0.2, # Low temperature for analytical consistency
                "top_p": 0.9
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(self.api_url, json=payload)
                if response.status_code != 200:
                    print(f"Ollama API Error [{response.status_code}]: {response.text}")
                response.raise_for_status()
                return response.json().get("response", "")
            except Exception as e:
                print(f"Error communicating with local LLM: {str(e)}")
                return ""

    def _clean_json_output(self, llm_response: str) -> str:
        """Removes markdown formatting if the LLM wraps the JSON output."""
        cleaned = re.sub(r"```json", "", llm_response)
        cleaned = re.sub(r"```", "", cleaned)
        return cleaned.strip()

    def _chunk_poem_with_overlap(self, poem_text: str, chunk_size: int = 3, overlap: int = 1) -> List[str]:
        """Splits a full poem into overlapping chunks of verses."""
        lines = [line.strip() for line in poem_text.split('\n') if line.strip()]
        if not lines:
            return []
            
        chunks = []
        step = chunk_size - overlap
        if step < 1:
            step = 1
            
        for i in range(0, len(lines), step):
            chunk = lines[i:i + chunk_size]
            chunks.append("\n".join(chunk))
            if i + chunk_size >= len(lines):
                break
        return chunks

    async def _extract_keywords_async(self, chunk: str) -> List[str]:
        """Extracts difficult words and core themes from a specific chunk."""
        sys_prompt = "You are a precise linguistic extractor. Return ONLY a valid JSON list of strings. No conversational text."
        prompt = f"""
        Analyze the following Arabic poem verses.
        Extract a maximum of 5 difficult Arabic words or core thematic keywords.
        Return them as a JSON list of strings.
        
        Verses:
        {chunk}
        
        Example output: ["word1", "word2", "theme1"]
        """
        
        response = await self._call_ollama(prompt, system_instruction=sys_prompt)
        cleaned_response = self._clean_json_output(response)
        
        try:
            keywords = json.loads(cleaned_response)
            if isinstance(keywords, list):
                return keywords
        except json.JSONDecodeError:
            pass
        return []

    async def process_request(self, poem_text: str, is_full_poem: bool, rag_engine: Any) -> Dict[str, Any]:
        """Main routing method based on the user's flag."""
        if is_full_poem:
            return await self._analyze_full_poem(poem_text, rag_engine)
        else:
            return await self._analyze_single_verse(poem_text, rag_engine)

    async def _analyze_single_verse(self, verse_text: str, rag_engine: Any) -> Dict[str, Any]:
        """Pipeline for a single verse."""
        # 1. Retrieve context directly
        retrieved_data = rag_engine.search(verse_text, top_k=3)
        context_str = json.dumps(retrieved_data, ensure_ascii=False)
        
        # 2. Final synthesis
        return await self._generate_final_analysis(verse_text, context_str)

    async def _analyze_full_poem(self, poem_text: str, rag_engine: Any) -> Dict[str, Any]:
        """Advanced Multi-Verse Pipeline (Sequential Execution for Local Hardware)"""
        # 1. Chunking
        chunks = self._chunk_poem_with_overlap(poem_text)
        
        # 2. Sequential Micro-Extraction
        extracted_lists = []
        for chunk in chunks:
            result = await self._extract_keywords_async(chunk)
            extracted_lists.append(result)
        
        # 3. Deduplication
        unique_keywords: Set[str] = set()
        for kw_list in extracted_lists:
            unique_keywords.update(kw_list)
        
        aggregated_query = " ".join(list(unique_keywords))
        
        # 4. Hybrid Retrieval based on extracted essence
        retrieved_data = rag_engine.search(aggregated_query, top_k=2)
        context_str = json.dumps(retrieved_data, ensure_ascii=False)
        
        # 5. Final Holistic Synthesis
        return await self._generate_final_analysis(poem_text, context_str)

    async def _generate_final_analysis(self, target_text: str, context: str) -> Dict[str, Any]:
        """The final generative step incorporating RAG context and self-reflection."""
        sys_prompt = """You are an expert critic of Arabic poetry.
        You MUST write your entire response in Arabic.
        Rely heavily on the provided retrieved context to formulate accurate meanings.
        Do not parrot the context exactly; synthesize a coherent, generalized explanation.
        You must evaluate your own confidence (0.0 to 1.0) based on how well the context matched the text.
        Output strictly in JSON format with NO markdown wrapping.
        """
        
        prompt = f"""
        Analyze the following text utilizing the retrieved reference context.
        
        Target Text:
        {target_text}
        
        Retrieved Reference Context:
        {context}
        
        JSON Output Schema requirement:
        {{
            "explanation": "Detailed Arabic explanation and analysis",
            "theme": "The main theme or purpose",
            "confidence": 0.95
        }}
        """
        
        response = await self._call_ollama(prompt, system_instruction=sys_prompt)
        cleaned_response = self._clean_json_output(response)
        
        try:
            analysis_dict = json.loads(cleaned_response)
            return analysis_dict
        except json.JSONDecodeError:
            # Fallback in case the LLM fails to return valid JSON
            return {
                "explanation": "Error: Failed to parse LLM output.",
                "theme": "Unknown",
                "confidence": 0.0
            }

# Instantiated engine
local_llm_engine = LocalLLMEngine()