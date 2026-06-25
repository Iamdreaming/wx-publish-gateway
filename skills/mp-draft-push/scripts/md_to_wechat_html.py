#!/usr/bin/env python3
"""
Markdown to WeChat HTML Converter
将公众号文章的 Markdown 内容转换为微信兼容的内联样式 HTML。

用法:
    python3 md_to_wechat_html.py input.md output.html
    
或直接作为模块导入:
    from md_to_wechat_html import markdown_to_wechat_html
    html = markdown_to_wechat_html(markdown_content)
"""

import re
import sys


def markdown_to_wechat_html(md: str) -> str:
    """Convert markdown to WeChat-compatible HTML with inline styles."""
    
    # Remove YAML frontmatter if present
    md = re.sub(r'^---\n.*?---\n', '', md, flags=re.DOTALL, count=1)
    
    lines = md.strip().split('\n')
    html_parts = []
    
    # Section wrapper with WeChat-compatible styles
    html_parts.append(
        '<section style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', '
        'sans-serif; line-height: 1.75; color: #3f3f3f; padding: 10px; '
        'font-size: 15px; letter-spacing: 1.5px;">'
    )
    
    in_paragraph = False
    
    for line in lines:
        line = line.strip()
        
        if not line:
            if in_paragraph:
                html_parts.append('</p>')
                in_paragraph = False
            continue
        
        # H1 title
        if line.startswith('# ') and not line.startswith('## '):
            title = line[2:].strip()
            if in_paragraph:
                html_parts.append('</p>')
                in_paragraph = False
            html_parts.append(
                f'<h1 style="font-size: 22px; color: #1a1a1a; '
                f'border-bottom: 1px solid #eee; padding-bottom: 8px; '
                f'margin-top: 20px; margin-bottom: 15px; font-weight: 600;">'
                f'{title}</h1>'
            )
        
        # H2 subtitle
        elif line.startswith('## '):
            title = line[3:].strip()
            if in_paragraph:
                html_parts.append('</p>')
                in_paragraph = False
            html_parts.append(
                f'<h2 style="font-size: 22px; color: #1a1a1a; '
                f'border-bottom: 1px solid #eee; padding-bottom: 8px; '
                f'margin-top: 30px; margin-bottom: 15px; font-weight: 600;">'
                f'{title}</h2>'
            )
        
        # Separator (---)
        elif line == '---':
            if in_paragraph:
                html_parts.append('</p>')
                in_paragraph = False
            html_parts.append(
                '<p style="text-align: center; color: #888; '
                'margin: 25px 0; font-size: 15px;">· · ·</p>'
            )
        
        # Italic source line (*text*)
        elif line.startswith('*') and line.endswith('*') and not line.startswith('**'):
            if in_paragraph:
                html_parts.append('</p>')
                in_paragraph = False
            content = line[1:-1]
            html_parts.append(
                f'<p style="font-size: 13px; color: #888; '
                f'margin-top: 20px; text-align: center;">{content}</p>'
            )
        
        # Regular paragraph
        else:
            # Process bold text
            line = re.sub(
                r'\*\*(.*?)\*\*',
                r'<strong style="color: #1a1a1a;">\1</strong>',
                line
            )
            
            if not in_paragraph:
                html_parts.append(
                    '<p style="margin-bottom: 20px; text-align: justify; '
                    'font-size: 15px; line-height: 1.75; '
                    'letter-spacing: 1.5px; color: #3f3f3f;">'
                )
                in_paragraph = True
            
            html_parts.append(line)
    
    if in_paragraph:
        html_parts.append('</p>')
    
    html_parts.append('</section>')
    
    return '\n'.join(html_parts)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 md_to_wechat_html.py input.md output.html")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    with open(input_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    html_content = markdown_to_wechat_html(md_content)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Converted {input_path} -> {output_path}")
    print(f"HTML length: {len(html_content)} chars")


if __name__ == '__main__':
    main()
