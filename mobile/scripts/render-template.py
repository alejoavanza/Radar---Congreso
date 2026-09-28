"""Render the same source catalog as Flask without starting the server."""
from pathlib import Path
import sys

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from source_catalog import public_catalog

templates = Environment(loader=FileSystemLoader(root / 'templates'),
                        autoescape=select_autoescape(['html']), undefined=StrictUndefined)
sys.stdout.write(templates.get_template('index.html').render(source_catalog=public_catalog()))
