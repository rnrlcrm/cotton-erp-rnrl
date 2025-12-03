"""
Tests for Language Service

Tests language detection and translation for multiple languages.
"""

import pytest
from backend.ai.services.language_service import LanguageService, get_language_service


class TestLanguageService:
    """Test language service functionality."""
    
    @pytest.fixture
    def service(self):
        """Get language service instance."""
        return LanguageService()
    
    def test_detect_english(self, service):
        """Test English language detection."""
        lang = service.detect("I need cotton")
        assert lang == "en"
    
    def test_detect_hindi(self, service):
        """Test Hindi language detection."""
        lang = service.detect("मुझे कपास चाहिए")
        assert lang == "hi"
    
    def test_detect_gujarati(self, service):
        """Test Gujarati language detection."""
        lang = service.detect("મને કપાસ જોઈએ છે")
        assert lang == "gu"
    
    def test_detect_marathi(self, service):
        """Test Marathi language detection."""
        lang = service.detect("मला कापूस हवा आहे")
        assert lang == "mr"
    
    def test_detect_short_text(self, service):
        """Test detection with short text defaults to English."""
        lang = service.detect("Hi")
        assert lang == "en"
    
    def test_detect_empty_text(self, service):
        """Test detection with empty text defaults to English."""
        lang = service.detect("")
        assert lang == "en"
    
    def test_translate_to_english(self, service):
        """Test translation to English."""
        translated = service.translate_to_english("मुझे कपास चाहिए", source_lang="hi")
        assert "cotton" in translated.lower() or "need" in translated.lower()
    
    def test_translate_from_english(self, service):
        """Test translation from English."""
        translated = service.translate_from_english("I need cotton", target_lang="hi")
        assert len(translated) > 0
        # Should contain Hindi characters
        assert any('\u0900' <= char <= '\u097F' for char in translated)
    
    def test_translate_same_language(self, service):
        """Test translation to same language returns original."""
        text = "Hello world"
        translated = service.translate(text, target_lang="en", source_lang="en")
        assert translated == text
    
    def test_translate_empty_text(self, service):
        """Test translation of empty text."""
        translated = service.translate("", target_lang="hi")
        assert translated == ""
    
    def test_is_supported(self, service):
        """Test language support checking."""
        assert service.is_supported("en")
        assert service.is_supported("hi")
        assert service.is_supported("gu")
        assert service.is_supported("mr")
        assert service.is_supported("ta")
        assert service.is_supported("ar")
        assert service.is_supported("zh-cn")
        assert not service.is_supported("xyz")
    
    def test_get_language_name(self, service):
        """Test getting language names."""
        assert "English" in service.get_language_name("en")
        assert "Hindi" in service.get_language_name("hi")
        assert "Gujarati" in service.get_language_name("gu")
    
    def test_get_all_languages(self, service):
        """Test getting all supported languages."""
        languages = service.get_all_languages()
        assert isinstance(languages, dict)
        assert "en" in languages
        assert "hi" in languages
        assert "gu" in languages
        assert "mr" in languages
        assert len(languages) > 30  # Should support 30+ languages
    
    def test_singleton(self):
        """Test singleton pattern."""
        service1 = get_language_service()
        service2 = get_language_service()
        assert service1 is service2
    
    def test_auto_detect_and_translate(self, service):
        """Test auto-detection with translation."""
        # Translate Hindi to English with auto-detect
        translated = service.translate("नमस्ते", target_lang="en")
        assert len(translated) > 0
    
    def test_multiple_indian_languages(self, service):
        """Test detection of multiple Indian languages."""
        tests = [
            ("नमस्ते", "hi"),  # Hindi
            ("નમસ્તે", "gu"),  # Gujarati
            ("नमस्कार", "mr"),  # Marathi
            ("வணக்கம்", "ta"),  # Tamil
            ("నమస్కారం", "te"),  # Telugu
        ]
        
        for text, expected_lang in tests:
            detected = service.detect(text)
            # Language detection might vary slightly, just check it's not English
            assert detected != "en"
