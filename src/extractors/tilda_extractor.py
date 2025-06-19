"""
Tilda data extractor
"""

import requests
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
import time
import base64

class TildaExtractor:
    """Экстрактор для прямого скачивания опубликованного сайта Tilda без API."""
    def __init__(self, config):
        self.config = config
        self.base_url = getattr(config, 'base_url', '').rstrip('/')
        self.session = requests.Session()
        # Настройка User-Agent для обхода защиты
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def test_connection(self):
        try:
            # Первый запрос для получения cookies от DDoS Guard
            response = self.session.get(self.base_url, timeout=30)
            if response.status_code == 200:
                return True
            else:
                raise Exception(f"Site not available: {self.base_url} (Status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Site not available: {self.base_url} - {str(e)}")

    def extract_pages(self) -> List[Dict[str, Any]]:
        # Скачиваем главную страницу и ищем все внутренние ссылки
        visited = set()
        to_visit = [self.base_url]
        pages = []
        
        while to_visit:
            url = to_visit.pop()
            if url in visited:
                continue
            try:
                # Добавляем задержку между запросами
                time.sleep(1)
                resp = self.session.get(url, timeout=30)
                if resp.status_code != 200:
                    continue
                html = resp.text
                pages.append({'url': url, 'html': html})
                visited.add(url)
                
                # Парсим ссылки только с главной страницы для начала
                if url == self.base_url:
                    soup = BeautifulSoup(html, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.startswith('/'):
                            abs_url = self.base_url + href
                        elif href.startswith(self.base_url):
                            abs_url = href
                        else:
                            continue
                        if abs_url not in visited and abs_url not in to_visit:
                            to_visit.append(abs_url)
                            
            except Exception as e:
                print(f"Error extracting page {url}: {e}")
                continue
        return pages

    def extract_assets(self) -> List[Dict[str, Any]]:
        # Скачиваем все ресурсы (css, js, img) со всех страниц
        pages = self.extract_pages()
        asset_urls = set()
        assets = []
        
        for page in pages:
            soup = BeautifulSoup(page['html'], 'html.parser')
            # CSS
            for link in soup.find_all('link', href=True):
                href = link['href']
                if href.endswith('.css') or 'css' in href:
                    asset_urls.add(self._make_absolute(href))
            # JS
            for script in soup.find_all('script', src=True):
                src = script['src']
                if src.endswith('.js') or 'js' in src:
                    asset_urls.add(self._make_absolute(src))
            # IMG
            for img in soup.find_all('img', src=True):
                src = img['src']
                asset_urls.add(self._make_absolute(src))
                
        for url in asset_urls:
            try:
                time.sleep(0.5)  # Задержка между запросами ресурсов
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200:
                    # Конвертируем bytes в base64 для JSON сериализации
                    content_b64 = base64.b64encode(resp.content).decode('utf-8')
                    assets.append({
                        'url': url, 
                        'content': content_b64,
                        'content_type': resp.headers.get('content-type', 'application/octet-stream')
                    })
            except Exception as e:
                print(f"Error downloading asset {url}: {e}")
                continue
        return assets

    def extract_forms(self) -> List[Dict[str, Any]]:
        # Находим формы на всех страницах
        pages = self.extract_pages()
        forms = []
        for page in pages:
            soup = BeautifulSoup(page['html'], 'html.parser')
            for form in soup.find_all('form'):
                action = form.get('action', '')
                method = form.get('method', 'get').lower()
                fields = []
                for input_ in form.find_all('input'):
                    if input_.get('name'):
                        fields.append({
                            'name': input_.get('name'),
                            'type': input_.get('type', 'text'),
                            'required': input_.has_attr('required')
                        })
                forms.append({'page': page['url'], 'action': action, 'method': method, 'fields': fields})
        return forms

    def _make_absolute(self, url: str) -> str:
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if url.startswith('//'):
            return 'http:' + url
        if url.startswith('/'):
            return self.base_url + url
        return self.base_url + '/' + url

    def _get_file_extension(self, url: str, content_type: str = None) -> str:
        if url.endswith('.jpg') or (content_type and 'jpeg' in content_type):
            return 'jpg'
        if url.endswith('.png') or (content_type and 'png' in content_type):
            return 'png'
        if url.endswith('.gif') or (content_type and 'gif' in content_type):
            return 'gif'
        if url.endswith('.css') or (content_type and 'css' in content_type):
            return 'css'
        if url.endswith('.js') or (content_type and 'javascript' in content_type):
            return 'js'
        return 'bin' 