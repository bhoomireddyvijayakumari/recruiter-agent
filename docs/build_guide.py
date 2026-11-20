"""Builds guide.html by injecting real project files into docs/guide_template.html ({{file:PATH}})."""
import html, pathlib, re
root = pathlib.Path(__file__).resolve().parent.parent
tpl = (root / "docs/guide_template.html").read_text()
def rep(m):
    p = m.group(1)
    return f'<div class="file"><div class="fn">{p}</div><pre><code>{html.escape((root / p).read_text())}</code></pre></div>'
(root / "guide.html").write_text(re.sub(r"\{\{file:([^}]+)\}\}", rep, tpl))
print("guide.html built")
