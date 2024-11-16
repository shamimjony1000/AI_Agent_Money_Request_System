import google.generativeai as genai
import json
import re
from typing import Optional, Dict, Any

class GeminiProcessor:
    def __init__(self):
        api_key = "AIzaSyCLyDgZNcE_v4wLMFF8SoimKga9bbLSun0"
        if not api_key:
            raise ValueError("API key not found")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.config = genai.GenerationConfig(
            temperature=0,
            top_p=1,
            top_k=1,
            max_output_tokens=2048
        )

    def is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        arabic_pattern = re.compile('[\u0600-\u06FF]')
        return bool(arabic_pattern.search(text))

    def translate_arabic_to_english(self, text: str) -> str:
        """Translate Arabic text to English while preserving non-Arabic parts."""
        prompt = f"""
        Translate the following text to English. If the text is mixed (Arabic and English),
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

    def extract_request_details(self, text: str, context: str = "") -> Optional[Dict[str, Any]]:
        """
        Extract request details from text with context.
        Returns a dictionary with extracted information or None if extraction fails.
        """
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
        
        Rules for extraction:
        1. Project number: Extract ONLY the numeric value, remove any non-numeric characters
        2. Project name: Extract the complete project name, including "University" if mentioned
        3. Amount: Extract ONLY the numeric value in riyals
        4. Reason: Extract the complete reason phrase
        
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
            
            # Clean up project number - ensure it's only numeric
            if result.get('project_number'):
                result['project_number'] = ''.join(filter(str.isdigit, str(result['project_number'])))
            
            # Clean up amount - ensure it's a number
            try:
                result['amount'] = float(str(result.get('amount', '0')).replace(',', ''))
            except ValueError:
                result['amount'] = 0
            
            # Validate required fields
            required_keys = ['project_number', 'project_name', 'amount', 'reason', 'missing_fields']
            if not all(key in result for key in required_keys):
                raise ValueError("Missing required keys in response")
            
            # Update missing fields based on empty or invalid values
            missing_fields = []
            if not result['project_number']:
                missing_fields.append('project_number')
            if not result['project_name']:
                missing_fields.append('project_name')
            if result['amount'] == 0:
                missing_fields.append('amount')
            if not result['reason']:
                missing_fields.append('reason')
            result['missing_fields'] = missing_fields
            
            # Add original and translated text
            result['original_text'] = full_text
            if is_arabic_input:
                result['translated_text'] = processing_text
            
            # Add confidence scores
            result['confidence_scores'] = {
                'project_number': 1.0 if result['project_number'] else 0.0,
                'project_name': 1.0 if result['project_name'] else 0.0,
                'amount': 1.0 if result['amount'] > 0 else 0.0,
                'reason': 1.0 if result['reason'] else 0.0
            }
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return None
        except Exception as e:
            print(f"Error processing request: {e}")
            return None

    def validate_extraction(self, result: Dict[str, Any]) -> bool:
        """
        Validate the extracted information.
        Returns True if all required fields are present and valid.
        """
        if not result:
            return False
            
        # Check if all required fields have values
        if not result.get('project_number'):
            return False
        if not result.get('project_name'):
            return False
        if not result.get('amount'):
            return False
        if not result.get('reason'):
            return False
            
        # Validate amount is a positive number
        try:
            amount = float(result['amount'])
            if amount <= 0:
                return False
        except (ValueError, TypeError):
            return False
            
        return True
