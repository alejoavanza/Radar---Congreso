"""Explicit text clues for Colombia; these are not geolocation or identity proof."""
import re
import unicodedata


def words(value):
    value = unicodedata.normalize('NFKD', str(value or '')).casefold()
    return re.findall(r'[^\W_]+', ''.join(c for c in value if not unicodedata.combining(c)))


COUNTRY_WORDS = frozenset((
    'colombia', 'colombiano', 'colombiana', 'colombianos', 'colombianas',
    'colombian', 'colombians', 'colombie', 'colombien', 'colombienne',
    'colombiens', 'colombiennes', 'kolumbien', 'kolumbianisch',
    'colombiani', 'colombiane',
))
# A deliberately small list of strong geographic clues. Ambiguous city names
# (Cartagena, Armenia, etc.) cannot on their own establish Colombian context.
PLACES = frozenset(('bogota', 'antioquia', 'barranquilla', 'bucaramanga', 'cundinamarca'))
LOCAL_OFFICES = frozenset(('alcalde', 'alcaldesa', 'alcaldia', 'concejo', 'concejales',
                           'mayor', 'governor', 'gobernador', 'gobernadora', 'congresista',
                           'representante', 'senador', 'senadora', 'congressman'))


def matches_territory(text, territory):
    wanted = words(territory)
    if not wanted:
        return True
    tokens = words(text)
    if wanted != ['colombia']:
        return ' ' + ' '.join(wanted) + ' ' in ' ' + ' '.join(tokens) + ' '
    if (COUNTRY_WORDS | PLACES).intersection(tokens):
        return True
    # Medellín also exists outside Colombia: require nearby political context.
    return any(token == 'medellin' and LOCAL_OFFICES.intersection(tokens[max(0, i-12):i+13])
               for i, token in enumerate(tokens))


def territory_query(territory):
    """Syntax shared by Google News and DuckDuckGo, never source-country limits."""
    if words(territory) == ['colombia']:
        return '("Colombia" OR colombiano OR colombiana OR Colombian OR Colombie OR Bogotá OR Antioquia OR Medellín OR Barranquilla OR Bucaramanga OR Cundinamarca)'
    return '"' + territory.replace('"', ' ').strip() + '"' if territory.strip() else ''
