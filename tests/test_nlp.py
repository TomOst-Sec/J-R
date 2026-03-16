"""Tests for multi-language NLP support."""

from argus.nlp.language import LanguageProcessor, detect_language


class TestLanguageDetection:
    def test_english(self):
        assert detect_language("Hello world, this is a test") == "en"

    def test_russian(self):
        result = detect_language("Привет мир, это тест")
        assert result == "ru"

    def test_chinese(self):
        result = detect_language("你好世界，这是一个测试")
        assert result == "zh"

    def test_japanese(self):
        result = detect_language("こんにちは世界")
        assert result == "ja"

    def test_korean(self):
        result = detect_language("안녕하세요 세계")
        assert result == "ko"

    def test_hebrew(self):
        result = detect_language("שלום עולם")
        assert result == "he"

    def test_arabic(self):
        result = detect_language("مرحبا بالعالم")
        assert result == "ar"

    def test_empty_defaults_to_english(self):
        assert detect_language("") == "en"


class TestLanguageProcessor:
    def test_english_tokenize(self):
        proc = LanguageProcessor()
        tokens = proc.tokenize("Hello world, this is great!", "en")
        assert "hello" in tokens
        assert "world" in tokens

    def test_chinese_tokenize(self):
        proc = LanguageProcessor()
        tokens = proc.tokenize("你好世界", "zh")
        assert len(tokens) > 0
        # Should have bigrams
        assert "你好" in tokens

    def test_stop_word_removal_english(self):
        proc = LanguageProcessor()
        tokens = ["the", "cat", "is", "on", "the", "mat"]
        filtered = proc.remove_stop_words(tokens, "en")
        assert "the" not in filtered
        assert "cat" in filtered
        assert "mat" in filtered

    def test_stop_word_removal_spanish(self):
        proc = LanguageProcessor()
        tokens = ["el", "gato", "es", "grande"]
        filtered = proc.remove_stop_words(tokens, "es")
        assert "el" not in filtered
        assert "gato" in filtered

    def test_keyword_extraction_english(self):
        proc = LanguageProcessor()
        text = "Python programming is great. Python is used for AI. Python developers love Python."
        keywords = proc.extract_keywords(text, top_n=3, language="en")
        assert "python" in keywords

    def test_keyword_extraction_top_n(self):
        proc = LanguageProcessor()
        text = "word1 word2 word3 word4 word5 word1 word2 word1"
        keywords = proc.extract_keywords(text, top_n=2, language="en")
        assert len(keywords) == 2
        assert keywords[0] == "word1"  # Most frequent

    def test_multilingual_processor_detects_language(self):
        proc = LanguageProcessor()
        # Should auto-detect and process
        keywords = proc.extract_keywords("Python programming data science machine learning")
        assert len(keywords) > 0
