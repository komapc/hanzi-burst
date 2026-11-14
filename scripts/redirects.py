"""site/_redirects для статики Cloudflare: постоянные (301) адреса вместо временных 307.

Статику отдаёт сам Cloudflare, без Worker'а (run_worker_first в wrangler.toml — только /api/* и файлы
подтверждения). Его html_handling приводит адреса к каноническим через 307: /c/6c34.html -> /c/6c34,
/japanese -> /japanese/. Поисковики считают 307 временным, поэтому те же переходы задаём здесь как 301:
_redirects применяется раньше html_handling (проверено в wrangler dev 4.151).

Правила строятся по уже собранному site/, поэтому build_static.py вызывает write() после всех страниц.
Лимиты Cloudflare: 2000 статичных и 100 динамических правил (с :плейсхолдером), статичные идут первыми.
"""
from pathlib import Path

# отдаются Worker'ом по точному адресу (run_worker_first) и 404 — редирект им не нужен
SKIP = {"404.html"}
SKIP_PREFIX = ("google", "yandex_")


def rules(site: Path) -> list[str]:
    static, dynamic = [], []
    for f in sorted(site.glob("*.html")):
        if f.name == "index.html":
            static.append("/index.html / 301")
        elif f.name not in SKIP and not f.name.startswith(SKIP_PREFIX):
            static.append(f"/{f.name} /{f.stem} 301")
    for d in sorted(p for p in site.rglob("*") if p.is_dir()):
        rel = d.relative_to(site).as_posix()
        if rel.split("/")[0] == "data":   # шарды JSON, страниц нет
            continue
        if (d / "index.html").exists():
            static += [f"/{rel} /{rel}/ 301", f"/{rel}/index.html /{rel}/ 301"]
        if any(f.name != "index.html" for f in d.glob("*.html")):
            dynamic.append(f"/{rel}/:page.html /{rel}/:page 301")
    assert len(static) <= 2000 and len(dynamic) <= 100, (len(static), len(dynamic))
    return static + dynamic


def write(site: Path) -> int:
    r = rules(site)
    (site / "_redirects").write_text("# собирается scripts/redirects.py, не править руками\n" + "\n".join(r) + "\n", encoding="utf-8")
    return len(r)
