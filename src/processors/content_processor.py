"""
Content processor for Tilda migration
"""

import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from loguru import logger
from bs4 import BeautifulSoup
from PIL import Image
import io
import cssutils
import cssutils.css
import os
import requests

from src.core.config import ProcessingConfig


class ContentProcessor:
    """Process and optimize extracted content"""
    
    def __init__(self, config: ProcessingConfig, form_handler_url: Optional[str] = None):
        self.config = config
        self.form_handler_url = form_handler_url
        self.asset_mapping = {}  # Map original URLs to new local paths
        self.processed_pages = {}
        self.processed_assets = {}
        
    def process_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all pages"""
        logger.info("📄 Processing pages...")
        
        processed_pages = []
        for page in pages:
            processed_page = self._process_page(page)
            processed_pages.append(processed_page)
        
        logger.info(f"✅ Processed {len(processed_pages)} pages")
        return processed_pages
    
    def _process_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual page. Only replaces asset URLs and form actions."""
        html_content = page.get('html', '')
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # The only changes we make are to localize assets and update form handlers.
        # No more cleaning, optimization, or fixing.
        self._process_images_in_page(soup)
        self._process_css_in_page(soup)
        self._process_js_in_page(soup)
        self._update_forms_in_page(soup)
        
        # Add a base URL tag to resolve relative paths correctly in the browser
        # Tilda often uses relative paths for assets.
        base_tag = soup.find("base")
        if not base_tag:
            base_tag = soup.new_tag("base", href=page.get('url', ''))
            if soup.head:
                soup.head.insert(0, base_tag)

        # Generate a filename from the URL
        page_url = page.get('url', '')
        parsed_url = urlparse(page_url)
        path = parsed_url.path
        if path == '/' or not path:
            filename = "index.html"
        else:
            filename = f"{Path(path).name}.html"

        return {
            **page,
            'html': str(soup), # Use str(soup) instead of prettify() to minimize changes
            'filename': filename,
        }
    
    def _process_images_in_page(self, soup: BeautifulSoup):
        """Finds all image srcs, downloads them, and updates the srcs."""
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                # Preserve query string for the final href, but not for the file path
                parsed_src = urlparse(src)
                local_path_disk = self._generate_local_path(src)

                local_path_html = local_path_disk
                if parsed_src.query:
                    local_path_html = f"{local_path_disk}?{parsed_src.query}"
                
                self.asset_mapping[src] = {
                    "local_path": local_path_disk,
                    "type": "image"
                }
                
                img['src'] = local_path_html
    
    def _process_css_in_page(self, soup: BeautifulSoup):
        """Finds all CSS links, downloads them, and updates the hrefs."""
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                # Preserve query string for the final href, but not for the file path
                parsed_href = urlparse(href)
                local_path_disk = self._generate_local_path(href)
                
                local_path_html = local_path_disk
                if parsed_href.query:
                    local_path_html = f"{local_path_disk}?{parsed_href.query}"

                self.asset_mapping[href] = {
                    "local_path": local_path_disk,
                    "type": "css"
                }
                
                link['href'] = local_path_html
      
    def _process_js_in_page(self, soup: BeautifulSoup):
        """Finds all JS links, downloads them, and updates the src."""
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src:
                # Preserve query string for the final href, but not for the file path
                parsed_src = urlparse(src)
                local_path_disk = self._generate_local_path(src)

                local_path_html = local_path_disk
                if parsed_src.query:
                    local_path_html = f"{local_path_disk}?{parsed_src.query}"

                self.asset_mapping[src] = {
                    "local_path": local_path_disk,
                    "type": "js"
                }

                script['src'] = local_path_html
    
    def _update_forms_in_page(self, soup: BeautifulSoup):
        """Update forms in page"""
        if not self.form_handler_url:
            logger.warning("`form_handler_url` not provided to ContentProcessor. Skipping form action updates.")
            return

        for form in soup.find_all('form'):
            # Update form action to use the configured handler
            form['action'] = self.form_handler_url
            form['method'] = 'post'
            
            # You can add more logic here if needed, e.g., hidden fields
    
    def process_assets(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all assets"""
        logger.info("📦 Processing assets...")
        
        processed_assets = []
        for asset in assets:
            processed_asset = self._process_asset(asset)
            if processed_asset:
                processed_assets.append(processed_asset)
        
        logger.info(f"✅ Processed {len(processed_assets)} assets")
        return processed_assets
    
    def _process_asset(self, asset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process individual asset"""
        processed_asset = None
        try:
            asset_type = asset.get('type', '')
            content = asset.get('content', b'')
            
            if asset_type == 'css':
                css_text = content.decode('utf-8')
                modified_css = self._parse_and_replace_css_urls(css_text, asset.get('url', ''))
                content = modified_css.encode('utf-8')

            if asset_type == 'image' and self.config.optimize_images:
                content = self._optimize_image(content)
            
            elif asset_type == 'css' and self.config.minify_css:
                content = self._minify_css(content)
            
            elif asset_type == 'js' and self.config.minify_js:
                content = self._minify_js(content)
            
            # Generate local path
            original_url = asset.get('url', '')
            local_path = self._generate_local_path(original_url)
            
            processed_asset = {
                **asset,
                'content': content,
                'local_path': local_path,
                'processed': True
            }
            
        except Exception as e:
            logger.warning(f"Failed to process asset {asset.get('url', '')}: {e}")
            processed_asset = asset  # Fallback to original asset
        
        # Final check to ensure content is bytes
        if processed_asset:
            content = processed_asset.get('content', b'')
            if isinstance(content, str):
                processed_asset['content'] = content.encode('utf-8')
        
        return processed_asset
    
    def _parse_and_replace_css_urls(self, css_text: str, base_url: str) -> str:
        """
        Parses CSS to find url() values, processes them, and then performs a simple
        string replacement on the original CSS text for maximum reliability.
        """
        try:
            sheet = cssutils.parseString(css_text, validate=False)
            urls_to_replace = {}  # E.g., {'/fonts/font.woff': 'assets/font.woff'}

            for original_url_in_css in list(cssutils.getUrls(sheet)):
                # Strip quotes and whitespace that cssutils might leave
                original_url = original_url_in_css.strip("'\" ")
                
                if not original_url or original_url.startswith('data:'):
                    continue

                absolute_url = urljoin(base_url, original_url)
                
                if absolute_url == base_url:
                    continue

                local_path = self._generate_local_path(absolute_url)
                self.asset_mapping[absolute_url] = {"local_path": local_path, "type": "asset"}
                urls_to_replace[original_url] = local_path
            
            # Perform direct, reliable string replacement
            modified_css_text = css_text
            for old, new in urls_to_replace.items():
                modified_css_text = modified_css_text.replace(old, new)
            
            return modified_css_text

        except Exception as e:
            logger.warning(f"Failed during CSS parsing, returning original content. Error: {e}")
            return css_text

    def _optimize_image(self, image_data: bytes) -> bytes:
        """Optimize image"""
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Optimize
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.warning(f"Failed to optimize image: {e}")
            return image_data
    
    def _minify_css(self, css_data: bytes) -> bytes:
        """Minify CSS"""
        try:
            css_text = css_data.decode('utf-8')
            
            # Remove comments
            css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
            
            # Remove unnecessary whitespace
            css_text = re.sub(r'\s+', ' ', css_text)
            css_text = re.sub(r';\s*}', '}', css_text)
            css_text = re.sub(r'{\s*', '{', css_text)
            css_text = re.sub(r'}\s*', '}', css_text)
            
            return css_text.strip().encode('utf-8')
            
        except Exception as e:
            logger.warning(f"Failed to minify CSS: {e}")
            return css_data
    
    def _minify_js(self, js_data: bytes) -> bytes:
        """Minify JavaScript"""
        try:
            js_text = js_data.decode('utf-8')
            
            # Remove comments
            js_text = re.sub(r'//.*$', '', js_text, flags=re.MULTILINE)
            js_text = re.sub(r'/\*.*?\*/', '', js_text, flags=re.DOTALL)
            
            # Remove unnecessary whitespace
            js_text = re.sub(r'\s+', ' ', js_text)
            
            return js_text.strip().encode('utf-8')
            
        except Exception as e:
            logger.warning(f"Failed to minify JavaScript: {e}")
            return js_data
    
    def _generate_local_path(self, url: str) -> str:
        """
        Generates a local path for a URL, preserving its original hostname and path structure
        to maintain dependencies. All assets will be stored under the 'assets/'
        directory.
        e.g., https://static.tildacdn.one/css/tilda.css -> assets/static.tildacdn.one/css/tilda.css
        """
        if not url:
            return ""

        # Handle schemaless URLs like //static.tildacdn.com/...
        if url.startswith('//'):
            url = 'https:' + url
            
        try:
            parsed_url = urlparse(url)
            
            # We need a hostname, otherwise we can't create a sane folder structure
            if not parsed_url.hostname:
                # If no hostname, maybe it's a relative path.
                # In our case, this shouldn't happen as extractor makes URLs absolute.
                # Fallback to a hash-based name in a generic folder.
                logger.warning(f"URL '{url}' has no hostname. Falling back to hash.")
                url_hash = hashlib.md5(url.encode()).hexdigest()
                return os.path.join("assets", "no_hostname", url_hash)

            # Path without the leading slash
            path_without_slash = parsed_url.path.lstrip('/')
            
            # If the path is empty (e.g., https://example.com), use a default name.
            if not path_without_slash:
                path_without_slash = "index.html"
            
            # If the path ends with a slash, it's a directory; append a default name.
            elif path_without_slash.endswith('/'):
                path_without_slash += "index.html"
                
            new_path = os.path.join("assets", parsed_url.hostname, path_without_slash)
            
            # Normalize the path to handle '..' or '.'
            new_path = os.path.normpath(new_path)
            
            # Final security check: ensure the path starts with 'assets' and does not contain '..'
            # This prevents path traversal attacks.
            if not new_path.startswith('assets' + os.sep) or '..' in new_path.split(os.sep):
                raise ValueError(f"Path traversal attempt detected or invalid path generated: '{new_path}'")

            logger.debug(f"Generated local path '{new_path}' from URL '{url}'")
            return new_path

        except Exception as e:
            logger.error(f"Could not parse URL '{url}' to generate local path: {e}. Falling back to hash.")
            url_hash = hashlib.md5(url.encode()).hexdigest()
            return os.path.join("assets", "fallback", url_hash)
    
    def process_forms(self, forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Processes form data."""
        logger.info("📝 Processing forms...")
        
        processed_forms = []
        for form in forms:
            processed_form = self._process_form(form)
            processed_forms.append(processed_form)
        
        logger.info(f"✅ Processed {len(processed_forms)} forms")
        return processed_forms
    
    def _process_form(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual form"""
        # Add form handler endpoint
        form['handler_endpoint'] = '/api/form-handler'
        
        # Process fields
        fields = form.get('fields', [])
        processed_fields = []
        
        for field in fields:
            processed_field = self._process_form_field(field)
            processed_fields.append(processed_field)
        
        return {
            **form,
            'fields': processed_fields,
            'processed': True
        }
    
    def _process_form_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Process form field"""
        field_type = field.get('type', 'text')
        
        # Add validation rules
        validation = {}
        
        if field.get('required'):
            validation['required'] = True
        
        if field_type == 'email':
            validation['email'] = True
        
        if field_type == 'tel':
            validation['phone'] = True
        
        return {
            **field,
            'validation': validation
        }
    
    def get_asset_mapping(self) -> Dict[str, str]:
        """Get asset URL mapping"""
        return self.asset_mapping.copy()

    def get_processed_assets(self) -> List[Dict[str, Any]]:
        """
        Returns a list of all found assets with their original URL,
        new local path, and type. The content is downloaded here.
        This completely bypasses any asset processing/optimization steps.
        """
        assets_to_deploy = []
        session = requests.Session()
        logger.info(f"Downloading {len(self.asset_mapping)} assets...")

        for original_url, asset_data in self.asset_mapping.items():
            try:
                response = session.get(original_url, timeout=20)
                response.raise_for_status()
                
                assets_to_deploy.append({
                    "original_url": original_url,
                    "local_path": asset_data["local_path"],
                    "type": asset_data["type"],
                    "content": response.content,
                })
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not download asset {original_url}: {e}")

        logger.info(f"✅ Successfully downloaded {len(assets_to_deploy)} assets.")
        return assets_to_deploy 