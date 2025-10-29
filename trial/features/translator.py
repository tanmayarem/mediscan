"""
Multilingual Support Module

This module provides translation support for Malayalam, Tamil, and Hindi.
Can use Google Translate API or other translation services.

For production, consider using:
- Google Cloud Translation API
- Microsoft Translator API
- Or offline models for privacy
"""

import os
import requests
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Language codes
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ml": "Malayalam",
    "ta": "Tamil",
    "hi": "Hindi"
}

# Common medicine terms in regional languages (for quick lookup)
MEDICINE_TERMS = {
    "ml": {
        "medicine": "മരുന്ന്",
        "side_effect": "പാർശ്വഫലങ്ങൾ",
        "composition": "ഘടന",
        "manufacturer": "നിർമ്മാതാവ്",
        "expiry": "കാലാവധി",
        "uses": "ഉപയോഗങ്ങൾ"
    },
    "ta": {
        "medicine": "மருந்து",
        "side_effect": "பக்க விளைவுகள்",
        "composition": "கலவை",
        "manufacturer": "உற்பத்தியாளர்",
        "expiry": "காலாவதி",
        "uses": "பயன்கள்"
    },
    "hi": {
        "medicine": "दवा",
        "side_effect": "दुष्प्रभाव",
        "composition": "संरचना",
        "manufacturer": "निर्माता",
        "expiry": "समाप्ति",
        "uses": "उपयोग"
    }
}


class Translator:
    """
    Handles translation between supported languages.
    """
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "google"):
        """
        Initialize translator.
        
        Args:
            api_key: API key for translation service
            provider: "google", "microsoft", or "libre" (free, offline)
        """
        self.api_key = api_key or os.environ.get("GOOGLE_TRANSLATE_API_KEY")
        self.provider = provider
    
    def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_lang: Target language code (ml, ta, hi, en)
            source_lang: Source language code (default: en)
            
        Returns:
            Translated text
        """
        if target_lang == source_lang:
            return text
        
        if not text or not text.strip():
            return text
        
        # Try API translation
        if self.api_key and self.provider == "google":
            return self._translate_google(text, target_lang, source_lang)
        elif self.provider == "libre":
            return self._translate_libre(text, target_lang, source_lang)
        else:
            # Fallback: return original with note
            logger.warning(f"Translation API not configured - returning original text")
            return text
    
    def _translate_google(self, text: str, target_lang: str, source_lang: str) -> str:
        """Translate using Google Translate API."""
        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                "key": self.api_key,
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text"
            }
            
            response = requests.post(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            return data["data"]["translations"][0]["translatedText"]
        except Exception as e:
            logger.error(f"Google translation error: {e}")
            return text  # Return original on error
    
    def _translate_libre(self, text: str, target_lang: str, source_lang: str) -> str:
        """
        Translate using LibreTranslate (free, open-source).
        Requires LibreTranslate server running.
        """
        try:
            # LibreTranslate free API endpoint
            url = "https://libretranslate.com/translate"
            data = {
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text"
            }
            
            response = requests.post(url, json=data, timeout=5)
            response.raise_for_status()
            result = response.json()
            return result.get("translatedText", text)
        except Exception as e:
            logger.error(f"LibreTranslate error: {e}")
            return text
    
    def translate_medicine_data(self, medicine_data: Dict, target_lang: str) -> Dict:
        """
        Translate medicine information to target language.
        
        Args:
            medicine_data: Dictionary with medicine info (name, composition, etc.)
            target_lang: Target language code
            
        Returns:
            Translated medicine data
        """
        if target_lang == "en":
            return medicine_data
        
        translated = {}
        fields_to_translate = ["medicine_name", "composition", "uses", "side_effects", "manufacturer"]
        
        for field in fields_to_translate:
            if field in medicine_data and medicine_data[field]:
                translated[field] = self.translate(str(medicine_data[field]), target_lang)
            else:
                translated[field] = medicine_data.get(field, "")
        
        # Keep non-translatable fields
        for field in medicine_data:
            if field not in fields_to_translate:
                translated[field] = medicine_data[field]
        
        return translated
    
    def get_term(self, term: str, lang: str) -> str:
        """
        Get translated term from pre-defined dictionary.
        Faster than API calls for common terms.
        """
        if lang == "en" or lang not in SUPPORTED_LANGUAGES:
            return term
        
        return MEDICINE_TERMS.get(lang, {}).get(term, term)


def translate_text(text: str, target_lang: str, source_lang: str = "en", 
                  api_key: Optional[str] = None) -> str:
    """
    Convenience function to translate text.
    
    Usage:
        translated = translate_text("Hello", "hi")
        print(translated)  # "नमस्ते"
    """
    translator = Translator(api_key=api_key)
    return translator.translate(text, target_lang, source_lang)

