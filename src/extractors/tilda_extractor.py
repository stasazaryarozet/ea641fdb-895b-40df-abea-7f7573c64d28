"""
Tilda data extractor
"""

import requests
from typing import List, Dict, Any
from dotmap import DotMap
from loguru import logger

class TildaExtractor:
    """
    Извлекает данные проекта с Tilda с использованием официального Tilda API.
    """
    
    BASE_API_URL = "http://api.tildacdn.info/v1"

    def __init__(self, config: DotMap):
        """
        Инициализирует экстрактор с конфигурацией Tilda.

        Args:
            config (DotMap): Секция 'tilda' из файла конфигурации.
                             Должна содержать api_key, secret_key и project_id.
        """
        self.config = config
        self.api_key = self.config.api_key
        self.secret_key = self.config.secret_key
        self.project_id = self.config.project_id
        
        if not all([self.api_key, self.secret_key, self.project_id]):
            raise ValueError("Tilda API key, secret key, and project ID must be provided.")
            
        logger.info("Tilda Extractor (API) initialized.")

    def _make_request(self, command: str, params: Dict = None) -> Dict[str, Any]:
        """
        Выполняет запрос к Tilda API.

        Args:
            command (str): Команда API (например, 'getpageslist').
            params (Dict, optional): Дополнительные параметры запроса. Defaults to None.

        Returns:
            Dict[str, Any]: Ответ API в формате JSON.
        """
        if params is None:
            params = {}
        
        url = f"{self.BASE_API_URL}/{command}/?key={self.api_key}&secret={self.secret_key}"
        
        for key, value in params.items():
            url += f"&{key}={value}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data['status'] != 'FOUND':
                logger.error(f"Tilda API error for command '{command}': {data.get('message', 'Unknown error')}")
                return None
            return data['result']
        except requests.RequestException as e:
            logger.error(f"Failed to request Tilda API command '{command}'. Error: {e}")
            return None

    def get_pages_list(self) -> List[Dict[str, Any]]:
        """
        Получает список страниц для указанного project_id.
        API: http://help-ru.tilda.ws/api/getpageslist
        """
        logger.info(f"Requesting pages list for project ID: {self.project_id}...")
        result = self._make_request("getpageslist", {"projectid": self.project_id})
        if result and 'pages' in result:
            logger.success(f"Successfully retrieved {len(result['pages'])} pages.")
            return result['pages']
        logger.warning("Could not retrieve pages list or project has no pages.")
        return []

    def get_page_full_export(self, page_id: str) -> Dict[str, Any]:
        """
        Получает полный экспорт страницы, включая HTML, CSS, JS и изображения.
        API: http://help-ru.tilda.ws/api/getpagefullexport
        """
        logger.info(f"Requesting full export for page ID: {page_id}...")
        result = self._make_request("getpagefullexport", {"pageid": page_id})
        if result:
            logger.success(f"Successfully retrieved full export for page ID: {page_id}.")
        return result

    def get_project_export(self) -> Dict[str, Any]:
        """
        Получает полный экспорт проекта.
        API: http://help-ru.tilda.ws/api/getprojectexport
        """
        logger.info(f"Requesting full export for project ID: {self.project_id}...")
        result = self._make_request("getprojectexport", {"projectid": self.project_id})
        if result:
            logger.success(f"Successfully retrieved full export for project ID: {self.project_id}.")
        return result

    def extract_pages(self) -> list:
        logger.info(f"Starting page extraction from base URL: {self.base_url}")
        visited = set()
        to_visit = [self.base_url]
        pages = []
        
        try:
            while to_visit:
                url = to_visit.pop(0) # Use as a queue
                if url in visited:
                    continue
                    
                logger.debug(f"Extracting: {url}")
                try:
                    self.driver.get(url)
                    # Wait for the body tag to be present, indicating page has loaded
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    html = self.driver.page_source
                    pages.append({'url': url, 'html': html})
                    visited.add(url)
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                    
                        if href.startswith('mailto:') or href.startswith('tel:') or href.startswith('#'):
                            continue

                        abs_url = urljoin(self.base_url, href)
                        
                        # Only follow links that are part of the same base domain
                        if abs_url.startswith(self.base_url) and abs_url not in visited and abs_url not in to_visit:
                            logger.debug(f"Found new internal link: {abs_url}")
                            to_visit.append(abs_url)
                                
                except Exception as e:
                    logger.error(f"Could not extract page {url}. Error: {str(e)}")
                    continue
        finally:
            if self.driver:
                self.driver.quit()
        
        logger.info(f"Extraction complete. Found {len(pages)} pages.")
        
        pages_file = self.output_path / "pages.json"
        with open(pages_file, 'w', encoding='utf-8') as f:
            json.dump(pages, f, indent=4, ensure_ascii=False)
            logger.info(f"✅ Raw page data saved to '{pages_file}'")

        return pages

    def extract_assets(self) -> List[Dict[str, Any]]:
        # This method is not used by the new processing flow,
        # but kept for potential future use or debugging.
        # The new flow identifies assets in the processor and downloads them there.
        return []

    def extract_forms(self) -> list:
        # This can be implemented similarly if needed, by parsing the saved HTML files.
        # For now, we assume the ContentProcessor handles form discovery.
        logger.info("Skipping form extraction in TildaExtractor; handled by ContentProcessor.")
        return []

    def _make_absolute(self, url: str) -> str:
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if url.startswith('//'):
            return 'http:' + url
        if url.startswith('/'):
            return self.base_url + url
        return self.base_url + '/' + url

    def load_extracted_pages(self) -> List[Dict[str, Any]]:
        """Loads pages from the pages.json file."""
        pages_file = self.output_path / "pages.json"
        if not pages_file.exists():
            return []
        with open(pages_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_extracted_forms(self) -> List[Dict[str, Any]]:
        """Loads forms from the forms.json file."""
        forms_file = self.output_path / "forms.json"
        if not forms_file.exists():
            return []
        with open(forms_file, 'r', encoding='utf-8') as f:
            return json.load(f)

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