import test from 'node:test';
import assert from 'node:assert/strict';
import { api, ApiError, resourceErrors, scenarioPayload } from '../src/api.js';

test('surfaces API validation errors on the affected resource, preserving field paths', () => {
  const error = new ApiError(
    [
      { loc: ['body', 'cenario', 'recursos', 2, 'base_id'], msg: 'Base inexistente', type: 'value_error' },
      { loc: ['body', 'cenario', 'reserva'], msg: 'Reserva negativa', type: 'value_error' },
    ],
    422,
  );
  assert.deepEqual(resourceErrors(error, 2), ['Base inexistente']);
  assert.deepEqual(resourceErrors(error, 1), []);
  assert.match(error.message, /recursos → 2 → base_id/);
});
test('scenario submission preserves declared bases, explicit availability and no invented crews', () => {
  const original = {
    recursos: [{ id: 'r', base_id: 'decl_b', capacidade: '2', disponivel: false, tipo: 'aereo' }],
    bases: [{ id: 'decl_b', nome: 'Base', lat: 1, lon: 2, fonte: 'Coordenação' }],
    reserva: '0',
    notas: ['Acesso interrompido'],
    simulado: false,
  };
  const result = scenarioPayload(original, 'regiao-teste', '2026-10-23');
  assert.equal(result.regiao, 'regiao-teste');
  assert.equal(result.periodo, '2026-10-23');
  assert.equal(result.recursos[0].capacidade, 2);
  assert.equal(result.recursos[0].disponivel, false);
  assert.equal(result.simulado, false);
  assert.deepEqual(result.bases, original.bases);
  assert.equal(original.recursos[0].capacidade, '2');
  assert.deepEqual(scenarioPayload({ ...original, recursos: [] }, 'r', 'p').recursos, []);
});
test('HTTP wrapper forwards POST JSON and handles structured server errors', async () => {
  const previous = globalThis.fetch;
  try {
    globalThis.fetch = async (path, options) => {
      assert.equal(path, '/api/run');
      assert.equal(options.method, 'POST');
      assert.deepEqual(JSON.parse(options.body), { sample: true });
      return new Response(JSON.stringify({ detail: 'Período sem dados' }), { status: 400 });
    };
    await assert.rejects(
      () => api('/api/run', { sample: true }),
      (error) => error instanceof ApiError && error.status === 400 && error.message === 'Período sem dados',
    );
  } finally {
    globalThis.fetch = previous;
  }
});
