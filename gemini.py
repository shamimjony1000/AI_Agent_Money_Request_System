import google.generativeai as genai
import os
import json
import re

class GeminiProcessor:
    def __init__(self):
        api_key = "AIzaSyCLyDgZNcE_v4wLMFF8SoimKga9bbLSun0"
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.config = genai.GenerationConfig(temperature=0)
    
    def is_arabic(self, text):
        arabic_pattern = re.compile('[\u0600-\u06FF]')
        return bool(arabic_pattern.search(text))
    
    def translate_arabic_to_english(self, text):
        prompt = f"""
        Translate the following Arabic text to English. If the text is mixed (Arabic and English),
        translate only the Arabic parts and keep the English parts as is.
        Keep numbers in their original format.
        
        Text to translate: {text}
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    
    def extract_request_details(self, text, context=""):
        full_text = f"{context} {text}".strip()
        is_arabic_input = self.is_arabic(full_text)
        
        if is_arabic_input:
            translated_text = self.translate_arabic_to_english(full_text)
            processing_text = translated_text
        else:
            processing_text = full_text
        
        prompt = f"""
        Extract the following information from this text and previous context.
        The input has been translated from Arabic if it contained Arabic text.
        
        If any information is missing, leave it empty.
        Format the response exactly as a JSON object with these keys:
        {{
            "project_number": "extracted number or empty string",
            "project_name": "extracted name or empty string",
            "amount": extracted number or 0,
            "reason": "extracted reason or empty string",
            "missing_fields": ["list of missing required fields"],
            "original_text": "the original input text"
        }}

        ##No preamble## Response in VALID JSON ONLY##

        Text to analyze: {processing_text}
        """
        
        try:
            response = self.model.generate_content(prompt, generation_config=self.config)
            result = json.loads(response.text)
            
            required_keys = ['project_number', 'project_name', 'amount', 'reason', 'missing_fields']
            if not all(key in result for key in required_keys):
                raise ValueError("Missing required keys in response")
            
            result['amount'] = float(result.get('amount', 0))
            result['original_text'] = full_text
            
            if is_arabic_input:
                result['translated_text'] = processing_text
            
            return result
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return None
        except Exception as e:
            print(f"Error processing request: {e}")
            return None