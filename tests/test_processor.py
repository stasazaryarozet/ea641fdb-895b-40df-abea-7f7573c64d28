import unittest
from pathlib import Path
import sys
from bs4 import BeautifulSoup

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.processors.content_processor import ContentProcessor
from src.core.config import load_config

class TestContentProcessor(unittest.TestCase):

    def setUp(self):
        """Настройка тестового окружения."""
        self.config = load_config('config.example.yaml')
        self.processor = ContentProcessor(self.config)

    def test_relativize_links(self):
        """
        Тестирует замену абсолютных ссылок на относительные в HTML.
        """
        base_url = "http://parisinseptember.com"
        html_content = f'''
        <html>
            <head>
                <link rel="stylesheet" href="{base_url}/css/style.css">
                <script src="{base_url}/js/script.js"></script>
            </head>
            <body>
                <img src="{base_url}/img/logo.png">
                <a href="{base_url}/about">About us</a>
                <a href="https://external.com/page">External</a>
            </body>
        </html>
        '''
        
        expected_html = '''
        <html>
            <head>
                <link rel="stylesheet" href="./css/style.css"/>
                <script src="./js/script.js"></script>
            </head>
            <body>
                <img src="./img/logo.png"/>
                <a href="./about">About us</a>
                <a href="https://external.com/page">External</a>
            </body>
        </html>
        '''

        processed_html = self.processor.relativize_links(html_content, base_url)
        
        # Парсим оба HTML для "умного" сравнения, нечувствительного к форматированию
        processed_soup = BeautifulSoup(processed_html, 'html.parser')
        expected_soup = BeautifulSoup(expected_html, 'html.parser')

        self.assertEqual(str(processed_soup), str(expected_soup))

    def test_remove_tilda_elements(self):
        """
        Тестирует удаление Tilda-специфичных скриптов и виджетов.
        """
        html_content = """
        <html>
            <body>
                <div id="allrecords" class="t-records" data-tilda-project-id="123"></div>
                <!-- Tilda PP big form -->
                <script src="https://static.tildacdn.com/js/tilda-forms-1.0.min.js"></script>
                <script src="https://tilda.ws/project/123/tildastat.js" async></script>
            </body>
        </html>
        """
        
        expected_html = """
        <html>
            <body>
                <div id="allrecords" class="t-records" data-tilda-project-id="123"></div>
            </body>
        </html>
        """

        processed_html = self.processor.remove_tilda_elements(html_content)
        
        processed_soup = BeautifulSoup(processed_html, 'html.parser')
        expected_soup = BeautifulSoup(expected_html, 'html.parser')

        self.assertEqual(str(processed_soup), str(expected_soup))

if __name__ == '__main__':
    unittest.main() 