import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extractors.tilda_extractor import TildaExtractor
from src.core.config import load_config

class TestApiTildaExtractor(unittest.TestCase):

    def setUp(self):
        """Настройка тестового окружения перед каждым тестом."""
        # Используем пример конфигурации для тестов
        self.config = load_config('config.example.yaml')
        self.extractor = TildaExtractor(self.config.tilda)

    @patch('src.extractors.tilda_extractor.requests.get')
    def test_get_pages_list_success(self, mock_get):
        """
        Тестирует успешное получение списка страниц проекта.
        """
        # --- Mocking ---
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "FOUND",
            "result": {
                "pages": [
                    {"id": "1", "title": "Home"},
                    {"id": "2", "title": "About"}
                ]
            }
        }
        mock_get.return_value = mock_response

        # --- Execution ---
        pages = self.extractor.get_pages_list()

        # --- Assertions ---
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0]['title'], 'Home')
        mock_get.assert_called_once() # Проверяем, что был сделан один запрос

    @patch('src.extractors.tilda_extractor.requests.get')
    def test_get_page_full_export_success(self, mock_get):
        """
        Тестирует успешное получение полного экспорта одной страницы.
        """
        # --- Mocking ---
        page_id = "12345"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "FOUND",
            "result": {
                "id": page_id,
                "html": "<html>...</html>",
                "images": [{"from": "img1.jpg", "to": "http://example.com/img1.jpg"}],
                "css": [{"from": "style.css", "to": "http://example.com/style.css"}],
                "js": [{"from": "script.js", "to": "http://example.com/script.js"}]
            }
        }
        mock_get.return_value = mock_response

        # --- Execution ---
        page_data = self.extractor.get_page_full_export(page_id)

        # --- Assertions ---
        self.assertIsNotNone(page_data)
        self.assertEqual(page_data['id'], page_id)
        self.assertIn("html", page_data)
        mock_get.assert_called_once()
        # Проверяем, что URL был сформирован правильно
        self.assertIn(f"pageid={page_id}", mock_get.call_args[0][0])


if __name__ == '__main__':
    unittest.main() 