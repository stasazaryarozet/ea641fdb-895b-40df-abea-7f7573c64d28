import os
import shutil
import re
from bs4 import BeautifulSoup

def process_site():
    source_dir = 'extracted_data'
    dist_dir = 'dist'
    
    # 1. Create a clean dist directory
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
        print(f"Removed existing directory: {dist_dir}")
    os.makedirs(dist_dir)
    print(f"Created directory: {dist_dir}")
    
    # 2. Define asset directories
    asset_dirs = {
        'css': os.path.join(dist_dir, 'css'),
        'js': os.path.join(dist_dir, 'js'),
        'assets': os.path.join(dist_dir, 'assets')
    }
    for d in asset_dirs.values():
        os.makedirs(d)
        print(f"Created asset directory: {d}")

    # 3. Move index.html from parisinseptember.ru folder
    # Assuming the main html is the only one in that specific folder.
    main_domain_dir = os.path.join(source_dir, 'parisinseptember.ru')
    print(f"Looking for index.html in: {main_domain_dir}")
    if os.path.exists(main_domain_dir):
        for item in os.listdir(main_domain_dir):
            if item.endswith('.html'):
                shutil.copy(os.path.join(main_domain_dir, item), os.path.join(dist_dir, 'index.html'))
                print(f"Copied index.html to {dist_dir}")
                break # Assuming one index file.
    else:
        print(f"Directory not found: {main_domain_dir}")

    # 4. Consolidate assets
    file_map = {}
    print("Starting asset consolidation...")
    for root, _, files in os.walk(source_dir):
        for file in files:
            original_path = os.path.join(root, file)
            new_name = os.path.basename(file).split('?')[0] # Clean query params
            
            file_ext = new_name.split('.')[-1].lower()
            dest_subdir = ''
            if file_ext in ['css']:
                dest_subdir = asset_dirs['css']
            elif file_ext in ['js']:
                dest_subdir = asset_dirs['js']
            elif file_ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'ttf', 'woff', 'woff2', 'eot', 'otf']:
                dest_subdir = asset_dirs['assets']

            if dest_subdir:
                dest_path = os.path.join(dest_subdir, new_name)
                shutil.copy(original_path, dest_path)
                
                # Create a map from old path fragment to new relative path
                # This is a bit naive, might need refinement
                key = os.path.join(os.path.basename(os.path.dirname(original_path)), file)
                if dest_subdir == asset_dirs['css']:
                    file_map[key] = f"css/{new_name}"
                elif dest_subdir == asset_dirs['js']:
                    file_map[key] = f"js/{new_name}"
                else:
                    file_map[key] = f"assets/{new_name}"
    print(f"Asset consolidation complete. Processed {len(file_map)} files.")


    # 5. Process HTML and CSS files to update paths
    index_path = os.path.join(dist_dir, 'index.html')
    print(f"Processing paths in: {index_path}")
    if os.path.exists(index_path):
        with open(index_path, 'r+', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

            # Update links and scripts
            for tag in soup.find_all(['link', 'script', 'img', 'source']):
                attr = ''
                if tag.name == 'link' and tag.has_attr('href'):
                    attr = 'href'
                elif tag.has_attr('src'):
                    attr = 'src'
                
                if attr:
                    old_path = tag[attr]
                    filename = old_path.split('/')[-1].split('?')[0]
                    file_ext = filename.split('.')[-1].lower()
                    
                    new_path = ''
                    if file_ext == 'css':
                        new_path = f"css/{filename}"
                    elif file_ext == 'js':
                        new_path = f"js/{filename}"
                    elif file_ext in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico']:
                         new_path = f"assets/{filename}"
                    
                    if new_path and os.path.exists(os.path.join(dist_dir, new_path)):
                         tag[attr] = new_path

            # Remove Tilda-specific scripts
            for script in soup.find_all('script', src=re.compile(r'tilda|ws\.tildacdn\.com')):
                if 'tilda-blocks' not in script['src']: # Keep block-specific logic
                    script.decompose()

            # Modify forms
            for form in soup.find_all('form'):
                form['action'] = 'https://your-new-form-handler.com/submit'
                form['method'] = 'POST'
            
            f.seek(0)
            f.write(str(soup))
            f.truncate()
            print("Path replacement and HTML cleaning complete.")
    else:
        print(f"index.html not found in {dist_dir} for processing.")

if __name__ == '__main__':
    process_site()
    print("Site processing complete. Files should be in 'dist' directory.")
    if os.path.exists('dist'):
        print("'dist' directory exists.")
    else:
        print("'dist' directory was NOT created.") 