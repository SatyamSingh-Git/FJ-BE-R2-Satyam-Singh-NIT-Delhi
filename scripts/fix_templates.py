import os
import re

def fix_split_template_tags(file_path):
    """
    Reads an HTML file, finds Django template tags {{ ... }} that are split across multiple lines,
    consolidates them into a single line to fix literal rendering issues, and writes the corrected
    content back to the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Regex to find {{ ... }} tags spanning multiple lines
        # Pattern explanation:
        # \{\{       : Matches start of tag
        # \s*        : Matches optional whitespace
        # (.*?)      : Non-greedy match for content
        # \s*        : Matches optional whitespace
        # \}\}       : Matches end of tag
        # re.DOTALL  : Makes dot (.) match newlines
        
        def replace_match(match):
            original = match.group(0)
            # Only fix if it contains newlines
            if '\n' in original:
                # Get the content inside braces
                inner_content = match.group(1)
                # Remove newlines and collapse multiple spaces into one
                cleaned_content = re.sub(r'\s+', ' ', inner_content).strip()
                result = f"{{{{ {cleaned_content} }}}}"
                # print(f"Fixed in {os.path.basename(file_path)}:\n  FROM: {original!r}\n  TO:   {result!r}")
                return result
            return original

        # Apply the regex substitution
        new_content = re.sub(r'\{\{\s*(.*?)\s*\}\}', replace_match, content, flags=re.DOTALL)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed syntax in: {file_path}")
            return True
            
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, 'templates')
    
    print(f"Scanning for split template tags in: {templates_dir}")
    
    count = 0
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                if fix_split_template_tags(file_path):
                    count += 1
    
    print(f"\nDone! Fixed issues in {count} files.")

if __name__ == '__main__':
    main()
