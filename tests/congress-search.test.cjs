const test = require('node:test');
const assert = require('node:assert/strict');
const catalog = require('../static/congress-members.json');
const {createIndex, findMatches, buildSearch, resolveMember} = require('../static/congress-search.js');
const index = createIndex(catalog.members);
const find = value => findMatches(index, value);
const toro = catalog.members.find(m => m.full_name === 'David Alejandro Toro Ramírez');

test('prefixes match names and surnames without accents, in either order', () => {
  for (const value of ['toro alej', 'ALEJ TOR', 'ramirez david', 'Toro Ramí']) {
    assert.ok(find(value).members.some(m => m.id === toro.id), value);
  }
  assert.ok(find('pen').members.some(m => m.surnames === 'de la Peña Duran'));
  assert.ok(find('astrid montes').members.some(m => m.surnames === 'Sánchez Montes de Oca'));
  assert.ok(find('corcho').members.some(m => m.chamber === 'senado'));
  assert.equal(find('zzzzzz').total, 0);
});

test('results require two letters, have a limit and sort surname first', () => {
  assert.equal(find('a').total, 0);
  assert.equal(find('  a  ').total, 0);
  const matches = find('ma');
  assert.equal(matches.members.length, 8);
  assert.ok(matches.total > 8);
  const names = matches.members.map(m => m.display_name);
  assert.deepEqual(names, [...names].sort(new Intl.Collator('es', {sensitivity: 'base'}).compare));
});

test('selection searches a useful name plus complete name and retains manual terms', () => {
  const query = buildSearch(toro.display_name, 'AlejoToroAnt, Alejandro Toro', toro);
  assert.equal(query.name, 'Alejandro Toro');
  assert.ok(query.aliases.includes('David Alejandro Toro Ramírez'));
  assert.ok(query.aliases.includes('AlejoToroAnt'));
  assert.ok(!query.aliases.split(', ').includes('Alejandro Toro'));
  assert.equal(query.aliases.split(', ').filter(a => a === toro.full_name).length, 1);
});

test('changing the selected name returns to free text without former aliases', () => {
  assert.deepEqual(buildSearch('Nombre libre', 'Mi término', toro), {name: 'Nombre libre', aliases: 'Mi término'});
  assert.deepEqual(buildSearch('  Fuera del directorio  ', '', null), {name: 'Fuera del directorio', aliases: ''});
});

test('directory preserves identities, official provenance and compound surnames', () => {
  assert.equal(new Set(catalog.members.map(m => m.id)).size, catalog.members.length);
  for (const member of catalog.members) {
    assert.ok(['www.camara.gov.co', 'www.senado.gov.co'].includes(new URL(member.source_url).hostname));
    assert.equal(member.display_name, `${member.surnames}, ${member.given_names}`);
    const query = buildSearch(member.display_name, '', member);
    assert.ok([query.name, ...query.aliases.split(', ')].includes(member.full_name));
  }
  assert.equal(catalog.members.find(m => m.full_name === 'Alejandro De la Ossa Lacayo').surnames, 'De la Ossa Lacayo');
});

test('official profile lookup accepts complete known names in either order', () => {
  for (const name of ['Alejandro Toro', 'DAVID ALEJANDRO TORO RAMIREZ', 'Toro Ramírez, David Alejandro']) {
    assert.equal(resolveMember(index, name)?.id, toro.id);
  }
  assert.equal(resolveMember(index, 'Isabel Zuleta')?.chamber, 'senado');
  for (const member of catalog.members) {
    assert.equal(resolveMember(index, member.search_name, member.id)?.id, member.id);
    if (member.profile_url) {
      const url = new URL(member.profile_url);
      assert.equal(url.protocol, 'https:');
      assert.equal(url.hostname, member.chamber === 'camara' ? 'www.camara.gov.co' : 'www.senado.gov.co');
    } else {
      assert.equal(member.chamber, 'senado', 'Only unlinked Senate entries use the directory fallback');
    }
  }
});

test('profile lookup never chooses an arbitrary person from a partial or ambiguous name', () => {
  for (const name of ['Toro', 'alej tor', 'Persona desconocida', '']) assert.equal(resolveMember(index, name), null);
  const other = catalog.members.find(m => m.full_name === 'Isabel Cristina Zuleta López');
  assert.equal(resolveMember(index, 'Isabel Zuleta', toro.id)?.id, other.id, 'A stale selection cannot override the searched name');
  const ambiguous = createIndex([toro, other].map(member => ({...member, aliases: [...member.aliases, 'Nombre Compartido']})));
  assert.equal(resolveMember(ambiguous, 'Nombre Compartido'), null);
  assert.equal(resolveMember(ambiguous, 'Nombre Compartido', toro.id)?.id, toro.id);
});
