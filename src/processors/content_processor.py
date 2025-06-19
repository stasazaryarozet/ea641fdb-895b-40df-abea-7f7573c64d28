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

from core.config import ProcessingConfig


class ContentProcessor:
    """Process and optimize extracted content"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.asset_mapping = {}  # Map original URLs to new local paths
        
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
        """Process individual page"""
        html_content = page.get('html', '')
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process images
        if self.config.download_images:
            self._process_images_in_page(soup)
        
        # Process CSS
        if self.config.minify_css:
            self._process_css_in_page(soup)
        
        # Process JavaScript
        if self.config.minify_js:
            self._process_js_in_page(soup)
        
        # Remove Tilda-specific elements
        self._remove_tilda_elements(soup)
        
        # Update forms
        self._update_forms_in_page(soup)
        
        # Get processed HTML
        processed_html = str(soup)
        
        return {
            **page,
            'html': processed_html,
            'processed': True
        }
    
    def _process_images_in_page(self, soup: BeautifulSoup):
        """Process images in page"""
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                # Generate local path
                local_path = self._generate_local_path(src, 'images')
                self.asset_mapping[src] = local_path
                
                # Update image src
                img['src'] = local_path
                
                # Add alt text if missing
                if not img.get('alt'):
                    img['alt'] = 'Image'
    
    def _process_css_in_page(self, soup: BeautifulSoup):
        """Process CSS in page"""
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                # Generate local path
                local_path = self._generate_local_path(href, 'css')
                self.asset_mapping[href] = local_path
                
                # Update href
                link['href'] = local_path
    
    def _process_js_in_page(self, soup: BeautifulSoup):
        """Process JavaScript in page"""
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src:
                # Generate local path
                local_path = self._generate_local_path(src, 'js')
                self.asset_mapping[src] = local_path
                
                # Update src
                script['src'] = local_path
    
    def _remove_tilda_elements(self, soup: BeautifulSoup):
        """Remove Tilda-specific elements"""
        # Remove Tilda scripts
        for script in soup.find_all('script'):
            script_content = script.string or ''
            if 'tilda' in script_content.lower() or 'tilda' in str(script.get('src', '')):
                script.decompose()
        
        # Remove Tilda CSS
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if 'tilda' in href.lower():
                link.decompose()
        
        # Remove Tilda-specific classes
        for element in soup.find_all(class_=re.compile(r't\d+')):
            # Remove Tilda classes but keep the element
            classes = element.get('class', [])
            new_classes = [cls for cls in classes if not cls.startswith('t')]
            if new_classes:
                element['class'] = new_classes
            else:
                element.attrs.pop('class', None)
    
    def _update_forms_in_page(self, soup: BeautifulSoup):
        """Update forms in page"""
        for form in soup.find_all('form'):
            # Update form action to use our handler
            form['action'] = '/api/form-handler'
            form['method'] = 'post'
            
            # Add form type field
            form_type_input = soup.new_tag('input')
            form_type_input['type'] = 'hidden'
            form_type_input['name'] = 'form_type'
            form_type_input['value'] = 'contact'  # Default type
            form.insert(0, form_type_input)
    
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
            
            if asset_type == 'image' and self.config.optimize_images:
                content = self._optimize_image(content)
            
            elif asset_type == 'css' and self.config.minify_css:
                content = self._minify_css(content)
            
            elif asset_type == 'js' and self.config.minify_js:
                content = self._minify_js(content)
            
            # Generate local path
            original_url = asset.get('url', '')
            local_path = self._generate_local_path(original_url, asset_type)
            
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
    
    def _generate_local_path(self, original_url: str, asset_type: str) -> str:
        """Generate local path for asset"""
        # Create hash from URL
        url_hash = hashlib.md5(original_url.encode()).hexdigest()[:8]
        
        # Get file extension
        parsed = urlparse(original_url)
        path = parsed.path
        extension = ''
        
        if '.' in path:
            extension = path.split('.')[-1].lower()
        else:
            # Default extensions
            if asset_type == 'image':
                extension = 'jpg'
            elif asset_type == 'css':
                extension = 'css'
            elif asset_type == 'js':
                extension = 'js'
            else:
                extension = 'bin'
        
        return f"/assets/{asset_type}/{url_hash}.{extension}"
    
    def process_forms(self, forms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all forms"""
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