from __future__ import annotations

import re
from pathlib import Path

from mkdocs.config import Config
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

DOCS_ROOT = Path(__file__).parent.parent


def on_page_markdown(markdown: str, page: Page, config: Config, files: Files) -> str:
    """Called on each file after it is read and before it is converted to HTML."""
    markdown = replace_pip_uv_commands(markdown)
    markdown = inject_code_snippets(markdown, page)
    return markdown


def replace_pip_uv_commands(markdown: str) -> str:
    """Replace pip/uv command placeholders with tabbed sections."""
    
    def sub_install(m: re.Match[str]) -> str:
        command = m.group(1)
        package = m.group(2) if m.group(2) else ""
        
        return f"""\
=== "pip"

    ```bash
    pip install{package}
    ```

=== "uv"

    ```bash
    uv add{package}
    ```"""

    return re.sub(r'```bash\n(pip install|uv add)([^\n]*)\n```', sub_install, markdown)


def inject_code_snippets(markdown: str, page: Page) -> str:
    """Inject code snippets from examples directory."""
    def sub_snippet(m: re.Match[str]) -> str:
        snippet_path = m.group(1)
        full_path = DOCS_ROOT.parent / "examples" / snippet_path
        
        if full_path.exists():
            content = full_path.read_text().strip()
            # Remove docstrings that are duplicated in docs
            content = re.sub(r'^""".*?"""', '', content, count=1, flags=re.S).strip()
            return content
        else:
            return f"<!-- Snippet not found: {snippet_path} -->"
    
    return re.sub(r'#! *examples/(.+)', sub_snippet, markdown, flags=re.M)