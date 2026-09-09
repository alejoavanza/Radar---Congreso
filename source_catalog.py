"""The 38 user-selected sources, shared by Radar and Comparativos.

Search scopes include sections where requested; they are not an allowlist for
the general search. A section and its parent publisher share a deduplication key.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    group: str
    scope: str

    @property
    def url(self):
        return 'https://' + self.scope.rstrip('/') + '/'

    def contains(self, url, *, domain_only=False):
        target, actual = urlsplit(self.url), urlsplit(url)
        host = (actual.hostname or '').lower().removeprefix('www.')
        expected = target.hostname.removeprefix('www.')
        return (host == expected or host.endswith('.' + expected)) and (
            domain_only or target.path == '/' or
            actual.path.rstrip('/') == target.path.rstrip('/') or
            actual.path.startswith(target.path))


SOURCES = tuple(Source(*row) for row in (
    ('infobae', 'Infobae Colombia', 'Internacionales', 'infobae.com/colombia'),
    ('elpais', 'El País América-Colombia', 'Internacionales', 'elpais.com/america-colombia'),
    ('bbc', 'BBC Mundo', 'Internacionales', 'bbc.com/mundo'),
    ('cnn', 'CNN en Español', 'Internacionales', 'cnnespanol.cnn.com'),
    ('france24', 'France 24', 'Internacionales', 'france24.com/es'),
    ('dw', 'DW', 'Internacionales', 'dw.com/es'),
    ('reuters', 'Reuters', 'Internacionales', 'reuters.com'),
    ('ap', 'Associated Press', 'Internacionales', 'apnews.com'),
    ('bloomberglinea', 'Bloomberg Línea Colombia', 'Internacionales', 'bloomberglinea.com'),
    ('guardian', 'The Guardian', 'Internacionales', 'theguardian.com'),
    ('efe', 'Agencia EFE', 'Internacionales', 'efe.com'),
    ('rfi', 'RFI', 'Internacionales', 'rfi.fr/es'),
    ('euronews', 'Euronews', 'Internacionales', 'euronews.com'),
    ('aljazeera', 'Al Jazeera', 'Internacionales', 'aljazeera.com'),
    ('nytimes', 'The New York Times', 'Internacionales', 'nytimes.com'),
    ('elcolombiano', 'El Colombiano', 'Regionales', 'elcolombiano.com'),
    ('vanguardia', 'Vanguardia', 'Regionales', 'vanguardia.com'),
    ('elpaiscali', 'El País de Cali', 'Regionales', 'elpais.com.co'),
    ('elheraldo', 'El Heraldo', 'Regionales', 'elheraldo.co'),
    ('eluniversal', 'El Universal', 'Regionales', 'eluniversal.com.co'),
    ('lapatria', 'La Patria', 'Regionales', 'lapatria.com'),
    ('laopinion', 'La Opinión', 'Regionales', 'laopinion.co'),
    ('zonacero', 'Zona Cero', 'Regionales', 'zonacero.com'),
    ('lasillavacia', 'La Silla Vacía', 'Política e investigación', 'lasillavacia.com'),
    ('cambio', 'Cambio', 'Política e investigación', 'cambiocolombia.com'),
    ('cuestionpublica', 'Cuestión Pública', 'Política e investigación', 'cuestionpublica.com'),
    ('voragine', 'Vorágine', 'Política e investigación', 'voragine.co'),
    ('las2orillas', 'Las2orillas', 'Política e investigación', 'las2orillas.co'),
    ('razonpublica', 'Razón Pública', 'Política e investigación', 'razonpublica.com'),
    ('confidencial', 'Confidencial Noticias', 'Política e investigación', 'confidencialnoticias.com'),
    ('pares', 'Pares', 'Política e investigación', 'pares.com.co'),
    ('colombiacheck', 'Colombiacheck', 'Política e investigación', 'colombiacheck.com'),
    ('irreverentes', 'Los Irreverentes', 'Política e investigación', 'losirreverentes.com'),
    ('verdadabierta', 'Verdad Abierta', 'Política e investigación', 'verdadabierta.com'),
    ('liga', 'La Liga Contra el Silencio', 'Política e investigación', 'ligacontraelsilencio.com'),
    ('nuevaprensa', 'La Nueva Prensa', 'Política e investigación', 'lanuevaprensa.com.co'),
    ('lineamedio', 'La Línea del Medio', 'Política e investigación', 'lalineadelmedio.com'),
    ('colombia20', 'Colombia+20 — El Espectador', 'Política e investigación', 'elespectador.com/colombia-20'),
))

# Small groups keep queries short and give regional/specialist sources their
# own result budget. The same complete groups run for every person and zone.
BATCHES = tuple(SOURCES[i:i + 4] for i in range(0, len(SOURCES), 4))
CATALOG_VERSION = '2026-09-09.1'


def site_query(batch):
    return '(' + ' OR '.join('site:' + source.scope for source in batch) + ')'


def matching_source(url, batch=SOURCES, *, domain_only=False):
    return next((source for source in batch if source.contains(url, domain_only=domain_only)), None)


def public_catalog():
    return [{'id': source.id, 'name': source.name, 'group': source.group,
             'url': source.url} for source in SOURCES]
