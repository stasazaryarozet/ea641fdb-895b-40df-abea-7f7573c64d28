"""
Tests for Tilda extractor
"""

import pytest
from unittest.mock import Mock, patch
from src.extractors.tilda_extractor import TildaExtractor
from src.core.config import TildaConfig


class TestTildaExtractor:
    """Test Tilda extractor functionality"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return TildaConfig(
            api_key="test_api_key",
            secret_key="test_secret_key",
            project_id="test_project_id",
            base_url="https://test-site.tilda.ws"
        )
    
    @pytest.fixture
    def extractor(self, config):
        """Create test extractor"""
        return TildaExtractor(config)
    
    def test_init(self, config):
        """Test extractor initialization"""
        extractor = TildaExtractor(config)
        assert extractor.config == config
        assert extractor.api_base == "https://api.tildacdn.info"
    
    @patch('src.extractors.tilda_extractor.requests.Session')
    def test_test_connection_success(self, mock_session, extractor):
        """Test successful connection test"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'FOUND'}
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Test connection
        result = extractor.test_connection()
        assert result is True
    
    @patch('src.extractors.tilda_extractor.requests.Session')
    def test_test_connection_failure(self, mock_session, extractor):
        """Test failed connection test"""
        # Mock failed response
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'ERROR', 'message': 'Invalid credentials'}
        mock_response.raise_for_status.return_value = None
        
        mock_session_instance = Mock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Test connection should raise exception
        with pytest.raises(Exception):
            extractor.test_connection()
    
    def test_generate_file_hash(self, extractor):
        """Test file hash generation"""
        content = b"test content"
        hash_result = extractor._get_file_extension("test.jpg", "image/jpeg")
        assert hash_result == "jpg"
    
    def test_get_file_extension_from_url(self, extractor):
        """Test file extension extraction from URL"""
        extension = extractor._get_file_extension("https://example.com/image.jpg", None)
        assert extension == "jpg"
    
    def test_get_file_extension_from_content_type(self, extractor):
        """Test file extension extraction from content type"""
        extension = extractor._get_file_extension("https://example.com/image", "image/png")
        assert extension == "png"
    
    def test_get_file_extension_default(self, extractor):
        """Test default file extension"""
        extension = extractor._get_file_extension("https://example.com/file", "unknown/type")
        assert extension == "bin" 