"""Report generator — dispatches to format-specific renderers."""

from __future__ import annotations

from argus.models.investigation import Investigation
from argus.reporting.csv_export import generate_csv
from argus.reporting.html import generate_html
from argus.reporting.markdown import generate_markdown

_FORMATS = {
    "json": lambda inv: inv.model_dump_json(indent=2),
    "markdown": generate_markdown,
    "md": generate_markdown,
    "html": generate_html,
    "csv": generate_csv,
}


class ReportGenerator:
    """Generate investigation reports in multiple formats."""

    def generate(self, investigation: Investigation, fmt: str) -> str:
        renderer = _FORMATS.get(fmt)
        if renderer is None:
            raise ValueError(f"Unsupported report format: {fmt!r}. Use: {', '.join(_FORMATS)}")
        return renderer(investigation)

    def generate_json(self, investigation: Investigation) -> str:
        return self.generate(investigation, "json")

    def generate_markdown(self, investigation: Investigation) -> str:
        return self.generate(investigation, "markdown")

    def generate_html(self, investigation: Investigation) -> str:
        return self.generate(investigation, "html")
