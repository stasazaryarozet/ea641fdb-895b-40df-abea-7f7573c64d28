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
from dotmap import DotMap

# from src.core.config import ProcessingConfig # This class was removed


class ContentProcessor:
    """Process and optimize extracted content"""
    
    def __init__(self, config: DotMap, form_handler_url: str = None):
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
            # Handle cases like /page/ and /page
            clean_path = path.strip('/')
            filename = f"{Path(clean_path).name}.html"
            if not Path(clean_path).name: # root index case again
                 filename = "index.html"

        
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
            
            if asset_type == 'image' and self.config.get("optimize_images"):
                content = self._optimize_image(content)
            
            elif asset_type == 'css' and self.config.get("minify_css"):
                content = self._minify_css(content)
            
            elif asset_type == 'js' and self.config.get("minify_js"):
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

    def extract_new_urls_from_css(self, css_text: str, base_url: str) -> List[str]:
        """
        Extracts all url() values from a CSS string and returns them as a list
        of absolute URLs. This is used for the recursive asset download loop.
        """
        new_urls = []
        try:
            sheet = cssutils.parseString(css_text, validate=False)
            for url_in_css in cssutils.getUrls(sheet):
                url = url_in_css.strip("'\" ")
                if not url or url.startswith('data:'):
                    continue
                
                absolute_url = urljoin(base_url, url)
                if absolute_url != base_url:
                    new_urls.append(absolute_url)
        except Exception as e:
            logger.warning(f"Could not parse CSS to extract new URLs from base {base_url}. Error: {e}")

        return new_urls

    def _optimize_image(self, image_data: bytes) -> bytes:
        """
        Optimizes an image by converting it to a web-friendly format
        and reducing its quality.
        """
        if not self.config.get("optimize_images", False):
            return image_data
            
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                output = io.BytesIO()
                # Convert to RGB if it's not, to avoid issues with saving as JPEG
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                img.save(output, format='JPEG', quality=self.config.get("image_quality", 85))
                optimized_data = output.getvalue()
                
                original_size = len(image_data)
                optimized_size = len(optimized_data)
                reduction = (original_size - optimized_size) / original_size * 100
                
                if reduction > 0:
                    logger.debug(f"Optimized image, reduced size by {reduction:.2f}%")
                
                return optimized_data
        except Exception as e:
            logger.warning(f"Image optimization failed: {e}. Returning original image.")
            return image_data

    def _minify_css(self, css_data: bytes) -> bytes:
        """
        Minifies CSS data.
        """
        if not self.config.get("minify_css", False):
            return css_data
            
        try:
            # Using a library is more robust than regex
            import rcssmin
            css_text = css_data.decode('utf-8')
            minified_text = rcssmin.cssmin(css_text)
            return minified_text.encode('utf-8')
        except ImportError:
            logger.warning("rcssmin not installed. Skipping CSS minification.")
            return css_data
        except Exception as e:
            logger.warning(f"CSS minification failed: {e}. Returning original CSS.")
            return css_data

    def _minify_js(self, js_data: bytes) -> bytes:
        """
        Minifies JS data.
        """
        if not self.config.get("minify_js", False):
            return js_data
            
        try:
            # Using a library is more robust than regex
            import rjsmin
            js_text = js_data.decode('utf-8')
            minified_text = rjsmin.jsmin(js_text)
            return minified_text.encode('utf-8')
        except ImportError:
            logger.warning("rjsmin not installed. Skipping JS minification.")
            return js_data
        except Exception as e:
            logger.warning(f"JS minification failed: {e}. Returning original JS.")
            return js_data

    def _generate_local_path(self, url: str) -> str:
        """
        Generates a consistent, safe local path for a given asset URL.
        Example: https://example.com/fonts/my-font.woff?v=1.2 -> assets/fonts/my-font.woff
        """
        if not url:
            return ""

        # Remove query strings and fragments for path generation
        parsed_url = urlparse(url)
        clean_url = parsed_url._replace(query="", fragment="").geturl()

        # Create a predictable path based on the URL structure
        if clean_url.startswith(str(self.config.base_url)):
            relative_path = Path(clean_url[len(str(self.config.base_url)):]).lstrip('/')
        else:
            # For external URLs, place them in an 'external' folder
            # to avoid conflicts, using the domain as a subfolder.
            domain = parsed_url.netloc
            path_part = Path(parsed_url.path).lstrip('/')
            relative_path = Path('external') / domain / path_part
        
        # Use a hash of the full original URL for uniqueness if paths are not descriptive
        # This helps with very long URLs or potential collisions.
        # Here, we just use the path.
        
        final_path = Path(self.config.get("assets_dir", "assets")) / relative_path
        
        # Security: prevent path traversal attacks (e.g., ../../)
        # We ensure the final path is inside the intended assets directory.
        assets_root = Path(self.config.output_dir) / self.config.get("assets_dir", "assets")
        
        # This is a basic check. A more robust implementation would resolve
        # the absolute paths and check if the asset path starts with the root path.
        if ".." in str(relative_path):
             # Fallback to a safe, hashed filename if traversal is detected
            hashed_name = hashlib.md5(clean_url.encode()).hexdigest()
            ext = Path(clean_url).suffix
            final_path = Path(self.config.get("assets_dir", "assets")) / f"{hashed_name}{ext}"

        return str(final_path)


    def process_forms(self, forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all forms"""
        processed_forms = []
        for form in forms:
            processed_form = self._process_form(form)
            processed_forms.append(processed_form)
        return processed_forms

    def _process_form(self, form: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual form"""
        processed_form = {
            **form,
            'processed': True
        }
        # Additional form processing logic here
        for i, field in enumerate(form.get('fields', [])):
            processed_form['fields'][i] = self._process_form_field(field)
            
        return processed_form

    def _process_form_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual form field"""
        processed_field = {
            **field,
            'processed': True
        }
        # Additional form field processing logic here
        
        return processed_field

    # Method to get the mapping of original URLs to local paths
    def get_asset_mapping(self) -> Dict[str, str]:
        return self.asset_mapping

    # Method to get the list of processed assets
    def get_processed_assets(self) -> List[Dict[str, Any]]:
        return list(self.processed_assets.values())

    def relativize_links(self, html_content: str, base_url: str) -> str:
        """
        Заменяет абсолютные ссылки на относительные в HTML-документе.
        
        Args:
            html_content (str): Исходный HTML.
            base_url (str): Базовый URL сайта, чьи ссылки нужно заменить.

        Returns:
            str: Модифицированный HTML с относительными ссылками.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urlparse(base_url).netloc

        tags = {
            'a': 'href',
            'link': 'href',
            'script': 'src',
            'img': 'src',
            'source': 'src'
        }

        for tag, attr in tags.items():
            for item in soup.find_all(tag, **{attr: True}):
                url = item[attr]
                url_parsed = urlparse(url)

                # Заменяем только ссылки, которые ведут на тот же домен
                if url_parsed.netloc == base_domain:
                    # Собираем относительный путь
                    relative_path = f".{url_parsed.path}"
                    item[attr] = relative_path
                    logger.debug(f"Relativized link: {url} -> {relative_path}")

        return str(soup)

    def remove_tilda_elements(self, html_content: str) -> str:
        """
        Удаляет Tilda-специфичные скрипты, ссылки и комментарии из HTML.
        
        Args:
            html_content (str): Исходный HTML.

        Returns:
            str: Очищенный HTML.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Удаляем скрипты, содержащие "tilda" в src
        for script in soup.find_all('script', src=True):
            if 'tilda' in script['src']:
                src = script['src']
                script.decompose()
                logger.debug(f"Removed Tilda script: {src}")

        # Удаляем комментарии, связанные с Tilda
        from bs4 import Comment
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            if 'tilda' in comment.lower():
                comment.extract()
                logger.debug("Removed Tilda-related comment.")
        
        return str(soup) 