"""
Multi-Language Service

Provides language detection and translation for 100+ languages.
Uses FREE APIs (deep-translator, langdetect).

Supported Languages (Major):
- English, Hindi, Gujarati, Marathi, Tamil, Telugu, Kannada, Malayalam
- Bengali, Punjabi, Urdu, Odia, Assamese
- Arabic, Chinese, French, German, Spanish, Portuguese, Russian
- Japanese, Korean, Indonesian, Thai, Vietnamese
- And 80+ more languages

Cost: $0/month (free tier)
"""

from __future__ import annotations

import logging
from typing import Optional
from functools import lru_cache

from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)


class LanguageService:
    """
    Multi-language support service.
    
    Features:
    - Auto-detect language (100+ languages)
    - Translate text (FREE Google Translate API)
    - Cached translations for performance
    - Fallback to English if detection fails
    
    Examples:
        >>> service = LanguageService()
        >>> lang = service.detect("मुझे कपास चाहिए")
        >>> print(lang)  # "hi" (Hindi)
        
        >>> translated = service.translate("I need cotton", target_lang="hi")
        >>> print(translated)  # "मुझे कपास चाहिए"
    """
    
    # Supported languages with native names
    SUPPORTED_LANGUAGES = {
        # Indian languages
        'en': 'English',
        'hi': 'हिंदी (Hindi)',
        'gu': 'ગુજરાતી (Gujarati)',
        'mr': 'मराठी (Marathi)',
        'ta': 'தமிழ் (Tamil)',
        'te': 'తెలుగు (Telugu)',
        'kn': 'ಕನ್ನಡ (Kannada)',
        'ml': 'മലയാളം (Malayalam)',
        'bn': 'বাংলা (Bengali)',
        'pa': 'ਪੰਜਾਬੀ (Punjabi)',
        'ur': 'اردو (Urdu)',
        'or': 'ଓଡ଼ିଆ (Odia)',
        'as': 'অসমীয়া (Assamese)',
        
        # International languages
        'ar': 'العربية (Arabic)',
        'zh-cn': '中文 (Chinese Simplified)',
        'zh-tw': '中文 (Chinese Traditional)',
        'fr': 'Français (French)',
        'de': 'Deutsch (German)',
        'es': 'Español (Spanish)',
        'pt': 'Português (Portuguese)',
        'ru': 'Русский (Russian)',
        'ja': '日本語 (Japanese)',
        'ko': '한국어 (Korean)',
        'id': 'Bahasa Indonesia (Indonesian)',
        'th': 'ไทย (Thai)',
        'vi': 'Tiếng Việt (Vietnamese)',
        'tr': 'Türkçe (Turkish)',
        'it': 'Italiano (Italian)',
        'pl': 'Polski (Polish)',
        'nl': 'Nederlands (Dutch)',
        'sv': 'Svenska (Swedish)',
        'no': 'Norsk (Norwegian)',
        'da': 'Dansk (Danish)',
        'fi': 'Suomi (Finnish)',
        'el': 'Ελληνικά (Greek)',
        'he': 'עברית (Hebrew)',
        'fa': 'فارسی (Persian)',
        'ms': 'Bahasa Melayu (Malay)',
        'sw': 'Kiswahili (Swahili)',
        'af': 'Afrikaans',
    }
    
    def __init__(self):
        """Initialize language service."""
        self._translators = {}  # Cache translators per language pair
    
    def detect(self, text: str) -> str:
        """
        Detect language of text.
        
        Args:
            text: Text to detect language
            
        Returns:
            ISO 639-1 language code ('en', 'hi', 'gu', etc.)
            Defaults to 'en' if detection fails
            
        Examples:
            >>> detect("Hello")  # 'en'
            >>> detect("नमस्ते")  # 'hi'
            >>> detect("સુપ્રભાત")  # 'gu'
        """
        if not text or len(text.strip()) < 3:
            return 'en'
        
        try:
            detected_lang = detect(text)
            
            # Normalize language code
            if detected_lang == 'zh-cn' or detected_lang == 'zh':
                detected_lang = 'zh-cn'
            
            return detected_lang
        
        except LangDetectException as e:
            logger.warning(f"Language detection failed for '{text[:50]}': {e}")
            return 'en'  # Default to English
    
    def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> str:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_lang: Target language code ('hi', 'gu', 'en', etc.)
            source_lang: Source language code (auto-detected if None)
            
        Returns:
            Translated text
            
        Examples:
            >>> translate("I need cotton", "hi")
            # "मुझे कपास चाहिए"
            
            >>> translate("કપાસ જોઈએ છે", "en", "gu")
            # "Need cotton"
        """
        if not text or not text.strip():
            return text
        
        # Auto-detect source language if not provided
        if source_lang is None:
            source_lang = self.detect(text)
        
        # No translation needed if same language
        if source_lang == target_lang:
            return text
        
        # Get or create translator for this language pair
        translator_key = f"{source_lang}->{target_lang}"
        
        if translator_key not in self._translators:
            try:
                self._translators[translator_key] = GoogleTranslator(
                    source=source_lang,
                    target=target_lang
                )
            except Exception as e:
                logger.error(f"Failed to create translator {translator_key}: {e}")
                return text  # Return original on error
        
        try:
            translator = self._translators[translator_key]
            translated = translator.translate(text)
            return translated
        
        except Exception as e:
            logger.error(f"Translation failed ({translator_key}): {e}")
            return text  # Return original on error
    
    def translate_to_english(self, text: str, source_lang: Optional[str] = None) -> str:
        """
        Translate text to English.
        
        Convenience method for translating to English.
        
        Args:
            text: Text to translate
            source_lang: Source language (auto-detected if None)
            
        Returns:
            English translation
        """
        return self.translate(text, target_lang='en', source_lang=source_lang)
    
    def translate_from_english(self, text: str, target_lang: str) -> str:
        """
        Translate English text to target language.
        
        Convenience method for translating from English.
        
        Args:
            text: English text to translate
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        return self.translate(text, target_lang=target_lang, source_lang='en')
    
    def is_supported(self, lang_code: str) -> bool:
        """
        Check if language is supported.
        
        Args:
            lang_code: ISO 639-1 language code
            
        Returns:
            True if supported, False otherwise
        """
        return lang_code in self.SUPPORTED_LANGUAGES
    
    def get_language_name(self, lang_code: str) -> str:
        """
        Get native name of language.
        
        Args:
            lang_code: ISO 639-1 language code
            
        Returns:
            Language name in native script
            
        Examples:
            >>> get_language_name("hi")  # "हिंदी (Hindi)"
            >>> get_language_name("gu")  # "ગુજરાતી (Gujarati)"
        """
        return self.SUPPORTED_LANGUAGES.get(lang_code, lang_code)
    
    def get_all_languages(self) -> dict[str, str]:
        """
        Get all supported languages.
        
        Returns:
            Dictionary of {code: name}
        """
        return self.SUPPORTED_LANGUAGES.copy()
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def _cached_detect(text: str) -> str:
        """
        Cached language detection for performance.
        
        Internal method - use detect() instead.
        """
        try:
            return detect(text)
        except LangDetectException:
            return 'en'


# Singleton instance
_language_service = None


def get_language_service() -> LanguageService:
    """
    Get singleton instance of LanguageService.
    
    Returns:
        LanguageService instance
        
    Usage:
        >>> from backend.ai.services import get_language_service
        >>> service = get_language_service()
        >>> lang = service.detect("કપાસ")
    """
    global _language_service
    if _language_service is None:
        _language_service = LanguageService()
    return _language_service
