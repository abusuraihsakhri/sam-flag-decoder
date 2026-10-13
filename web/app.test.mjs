import test from 'node:test';
import assert from 'node:assert/strict';
import {decodeFlag, parseFlag, parseCsv, exportCsv, decodeCsv} from './app.js';

test('standard SAM FLAG examples', () => {
  assert.equal(parseFlag('99'), 99);
  assert.equal(parseFlag('0x63'), 99);
  assert.deepEqual(decodeFlag(99).setBits.map(x => x.bit), [1, 2, 32, 64]);
  assert.deepEqual(decodeFlag(147).setBits.map(x => x.bit), [1, 2, 16, 128]);
  assert.deepEqual(decodeFlag(2064).setBits.map(x => x.bit), [16, 2048]);
  assert.equal(decodeFlag(0).summary, 'No SAM FLAG bits set');
  assert.equal(decodeFlag(4096).unknownBits, 4096);
  assert.equal(decodeFlag(193).warnings.length, 0);
});
test('invalid FLAG values are rejected', () => {
  for (const invalid of ['-1', '65536', 'NaN', '1.5', '0xZZ', '']) {
    assert.throws(() => parseFlag(invalid));
  }
});
test('CSV quoting, batch results, and errors', () => {
  const decoded = decodeCsv('name,FLAG\r\n"Q,1",99\r\nQ2,147\r\nQ3,bad\r\n');
  assert.equal(decoded.rows.length, 3);
  assert.equal(decoded.invalid, 1);
  assert.equal(decoded.rows[0].name, 'Q,1');
  assert.equal(decoded.rows[1].flag_decimal, 147);
  assert.ok(decoded.rows[2].error);
  assert.deepEqual(parseCsv(exportCsv([['a', 'b'], ['a,b', 'x"y']])), [['a', 'b'], ['a,b', 'x"y']]);
  assert.throws(() => parseCsv('FLAG\n"no end'));
});
