from datetime import datetime, timedelta
import json
from gtts import gTTS
import io

class MemoryHandler:
    def __init__(self):
        self.conversation_history = []
        self.max_history = 5
        self.context_timeout = timedelta(minutes=2)
        self.last_interaction_time = None
        self.partial_info = {
            'project_number': None,
            'project_name': None,
            'amount': None,
            'reason': None,
            'timestamp': None
        }
        self.confidence_scores = {
            'project_number': 0.0,
            'project_name': 0.0,
            'amount': 0.0,
            'reason': 0.0
        }
    
    def add_interaction(self, text: str, extracted_info: dict = None) -> None:
        current_time = datetime.now()
        
        if self.last_interaction_time and \
           (current_time - self.last_interaction_time) > self.context_timeout:
            self.clear_partial_info()
        
        if text:
            self.conversation_history.append({
                'text': text,
                'timestamp': current_time.isoformat(),
                'extracted_info': extracted_info
            })
            if len(self.conversation_history) > self.max_history:
                self.conversation_history.pop(0)
        
        if extracted_info:
            self._update_partial_info(extracted_info, current_time)
        
        self.last_interaction_time = current_time
    
    def _update_partial_info(self, extracted_info: dict, current_time: datetime) -> None:
        for key in self.partial_info:
            if key in extracted_info and extracted_info[key]:
                new_value = extracted_info[key]
                current_value = self.partial_info[key]
                
                if (current_value is None or 
                    extracted_info.get(f'{key}_confidence', 0.5) > 
                    self.confidence_scores.get(key, 0)):
                    self.partial_info[key] = new_value
                    self.confidence_scores[key] = extracted_info.get(f'{key}_confidence', 0.5)
        
        self.partial_info['timestamp'] = current_time
    
    def get_context(self) -> str:
        context_parts = []
        
        for entry in self.conversation_history:
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
            context_parts.append(f"[{timestamp}] {entry['text']}")
        
        context = " ".join(context_parts)
        
        partial_context = []
        for key, value in self.partial_info.items():
            if value and key != 'timestamp':
                confidence = self.confidence_scores.get(key, 0)
                partial_context.append(f"{key}: {value} (confidence: {confidence:.2f})")
        
        if partial_context:
            context += "\nPartial information: " + ", ".join(partial_context)
        
        return context
    
    def get_partial_info(self) -> dict:
        info = {k: v for k, v in self.partial_info.items() 
               if k != 'timestamp' and v is not None}
        info['confidence_scores'] = self.confidence_scores
        return info
    
    def merge_partial_info(self, new_info: dict) -> None:
        for key in self.partial_info:
            if key in new_info and new_info[key] is not None:
                new_confidence = new_info.get(f'{key}_confidence', 0.5)
                if (self.partial_info[key] is None or 
                    new_confidence > self.confidence_scores.get(key, 0)):
                    self.partial_info[key] = new_info[key]
                    self.confidence_scores[key] = new_confidence
    
    def clear_partial_info(self) -> None:
        self.partial_info = {
            'project_number': None,
            'project_name': None,
            'amount': None,
            'reason': None,
            'timestamp': None
        }
        self.confidence_scores = {
            'project_number': 0.0,
            'project_name': 0.0,
            'amount': 0.0,
            'reason': 0.0
        }
    
    def clear_memory(self) -> None:
        self.conversation_history = []
        self.clear_partial_info()
        self.last_interaction_time = None
        return "Memory cleared!"
    
    def get_missing_fields(self) -> list:
        missing = []
        confidence_threshold = 0.5
        
        for field in ['project_number', 'project_name', 'amount', 'reason']:
            if (self.partial_info.get(field) is None or 
                self.confidence_scores.get(field, 0) < confidence_threshold):
                missing.append(field)
        return missing
    
    def get_prompt_for_missing_info(self) -> str:
        missing = self.get_missing_fields()
        if not missing:
            return "All required information has been provided with sufficient confidence."
        
        current_info = self.get_partial_info()
        prompt = "Current information:\n"
        
        for key, value in current_info.items():
            if key != 'confidence_scores' and value is not None:
                confidence = self.confidence_scores.get(key, 0)
                prompt += f"- {key}: {value} (confidence: {confidence:.2f})\n"
        
        prompt += "\nPlease provide or clarify the following information:\n"
        for field in missing:
            current_confidence = self.confidence_scores.get(field, 0)
            if current_confidence > 0:
                prompt += f"- {field} (current confidence: {current_confidence:.2f}, needs improvement)\n"
            else:
                prompt += f"- {field} (missing)\n"
        
        return prompt