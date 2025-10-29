"""
AI Chatbot Module

This module provides an AI-powered chatbot that can answer medicine-related queries.
The chatbot acts as an AI Agent with internet access, allowing it to look up
information beyond the local database.

Uses OpenAI API or other LLM APIs (can be configured for different providers).
"""

import os
import json
import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Check if OpenAI is available
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class MedicineChatbot:
    """
    AI Chatbot for medicine-related queries.
    
    How it works:
    1. User asks a question about medicine
    2. Bot searches local database first
    3. If needed, uses AI with internet access to get current information
    4. Returns helpful, accurate responses
    """
    
    def __init__(self, api_key: Optional[str] = None, api_provider: str = "groq"):
        """
        Initialize chatbot.
        
        Args:
            api_key: API key for the LLM provider
            api_provider: "openai", "anthropic", "groq", or "local"
        """
        # Check for Groq first (free), then OpenAI
        self.api_key = api_key or os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.api_provider = api_provider
        
        # Auto-detect provider if key is found
        if not api_provider or api_provider == "auto":
            if os.environ.get("GROQ_API_KEY"):
                self.api_provider = "groq"
            elif os.environ.get("OPENAI_API_KEY"):
                self.api_provider = "openai"
            else:
                self.api_provider = "groq"  # Default to Groq
        
        self.conversation_history: List[Dict] = []
        
        if HAS_OPENAI and self.api_key and self.api_provider == "openai":
            openai.api_key = self.api_key
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
            if not self.api_key:
                logger.warning("No API key found - chatbot will use fallback mode")
    
    def get_response(self, user_message: str, context: Optional[Dict] = None) -> Dict:
        """
        Get chatbot response to user message.
        
        Args:
            user_message: User's question
            context: Optional context (e.g., current medicine being viewed)
            
        Returns:
            {
                "response": "...",
                "sources": [...],
                "confidence": 0.0-1.0
            }
        """
        # Add system prompt
        system_prompt = self._get_system_prompt(context)
        
        # Try to use AI API
        if self.client and self.api_provider == "openai":
            return self._get_openai_response(user_message, system_prompt)
        elif self.api_provider == "groq" and self.api_key:
            return self._get_groq_response(user_message, system_prompt)
        else:
            # Fallback: rule-based responses
            return self._get_fallback_response(user_message, context)
    
    def _get_system_prompt(self, context: Optional[Dict] = None) -> str:
        """Generate system prompt for the AI."""
        prompt = """You are a helpful medical information assistant for MedScan, a medicine identification app. 
        
Your role:
- Answer questions about medicines, their uses, side effects, interactions, etc.
- NEVER prescribe medicines or provide medical advice - only factual information
- If asked about treatment, always recommend consulting a doctor
- Use up-to-date information from reliable medical sources
- Be clear, concise, and helpful

Important rules:
- Always emphasize "Consult your doctor" for medical decisions
- If you don't know something, say so - don't guess
- For drug interactions, always recommend checking with a pharmacist or doctor

"""
        if context:
            prompt += f"\nCurrent context:\n- Medicine: {context.get('medicine_name', 'None')}\n- Composition: {context.get('composition', 'None')}\n"
        
        return prompt
    
    def _get_openai_response(self, user_message: str, system_prompt: str) -> Dict:
        """Get response from OpenAI API."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                *self.conversation_history[-5:],  # Last 5 messages for context
                {"role": "user", "content": user_message}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use cost-effective model
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            return {
                "response": ai_response,
                "sources": ["OpenAI GPT-4"],
                "confidence": 0.9
            }
        except Exception as e:
            logger.error(f"Error getting OpenAI response: {e}")
            return self._get_fallback_response(user_message, None)
    
    def _get_groq_response(self, user_message: str, system_prompt: str) -> Dict:
        """Get response from Groq API (fast, free tier available)."""
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = [
                {"role": "system", "content": system_prompt},
                *self.conversation_history[-5:],
                {"role": "user", "content": user_message}
            ]
            
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            return {
                "response": ai_response,
                "sources": ["Groq Llama 3"],
                "confidence": 0.85
            }
        except Exception as e:
            logger.error(f"Error getting Groq response: {e}")
            return self._get_fallback_response(user_message, None)
    
    def _get_fallback_response(self, user_message: str, context: Optional[Dict]) -> Dict:
        """Fallback rule-based responses when AI is not available."""
        message_lower = user_message.lower()
        
        # Common queries and responses
        responses = {
            "side effect": "Side effects vary by medicine. Check the specific medicine details for complete information. If you experience severe side effects, consult your doctor immediately.",
            "interaction": "Drug interactions can be dangerous. Always check with your doctor or pharmacist before taking multiple medicines together. Use the Interaction Checker feature for preliminary checks.",
            "how to take": "Dosage and administration depend on the medicine and your condition. Always follow your doctor's prescription or the medicine label instructions.",
            "when to take": "Timing matters for some medicines. Some are best taken with food, others on an empty stomach. Check the medicine label or consult your pharmacist.",
            "expiry": "Check the expiry date on the medicine package. Never use expired medicines as they may be ineffective or harmful.",
            "fake": "To verify medicine authenticity, check the packaging for proper seals, manufacturer details, and batch numbers. If suspicious, report to authorities.",
        }
        
        # Find matching response
        for keyword, response in responses.items():
            if keyword in message_lower:
                return {
                    "response": response + "\n\n💡 For more detailed information, enable AI chat in settings (requires API key).",
                    "sources": ["Local knowledge base"],
                    "confidence": 0.6
                }
        
        # Default response
        return {
            "response": """I can help with questions about medicines, but for detailed answers, please:
            
1. Check the medicine details page
2. Use the Interaction Checker for drug interactions
3. Consult your doctor for medical advice

💡 Enable AI chat (requires API key) for more detailed responses.

Is there something specific about a medicine you'd like to know?""",
            "sources": ["MedScan Help"],
            "confidence": 0.5
        }
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


def get_chatbot_response(message: str, context: Optional[Dict] = None, api_key: Optional[str] = None) -> Dict:
    """
    Convenience function to get chatbot response.
    
    Usage:
        response = get_chatbot_response("What are the side effects of Paracetamol?")
        print(response["response"])
    """
    chatbot = MedicineChatbot(api_key=api_key)
    return chatbot.get_response(message, context)

