// Run with: node --test tests/useTop5.test.mjs
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { setImmediate } from 'node:timers/promises'
import { test } from 'node:test'
import { runInNewContext } from 'node:vm'
import ts from '../node_modules/typescript/lib/typescript.js'

// Execute the actual hook without a DOM or Vite (and without loading .env).
// Only React's effect/state scheduler and the network boundary are substituted.
const source = readFileSync(new URL('../src/hooks/useData.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source.replaceAll('import.meta.env', '__env'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
})

async function runTop5({ apiMode, base = '/', payload, ok = true, reject = false }) {
  const states = []
  const urls = []
  const exports = {}
  runInNewContext(outputText, {
    exports,
    __env: { VITE_API_MODE: String(apiMode), VITE_API_BASE: 'https://api.example.invalid', BASE_URL: base },
    require(name) {
      assert.equal(name, 'react')
      return {
        useState(initial) {
          const index = states.push(initial) - 1
          return [initial, value => { states[index] = value }]
        },
        useEffect(effect) { effect() },
        useCallback(callback) { return callback },
      }
    },
    async fetch(url) {
      urls.push(url)
      if (reject) throw new Error('offline')
      return { ok, status: ok ? 200 : 503, async json() { return payload } }
    },
  })
  const initial = exports.useTop5()
  assert.equal(initial.data, null)
  assert.equal(initial.loading, true)
  await setImmediate()
  return { data: states[0], loading: states[1], urls }
}

function fixture(stars = [10, 600, 20, 400, 500, 300, 200]) {
  return {
    generated_at: '2026-09-18T00:00:00Z',
    repos: stars.map((stars, i) => ({
      full_name: `owner/repo-${i}`, name: `repo-${i}`, owner: 'owner',
      description: `Description ${i}`, url: `https://github.com/owner/repo-${i}`,
      stars, stars_formatted: `${stars} stars`, forks: 37 + i,
      language: 'TypeScript', topics: ['ai', `topic-${i}`],
      summary: `Canonical summary ${i}`, updated_at: '2026-09-17T00:00:00Z',
    })),
  }
}

for (const apiMode of [false, true]) {
  for (const base of ['/', '/ai-intel/']) {
    test(`uses same-site canonical JSON: API_MODE=${apiMode}, BASE_URL=${base}`, async () => {
      const result = await runTop5({ apiMode, base, payload: fixture() })
      assert.deepEqual(result.urls, [`${base}data/github_top5.json`])
      assert.equal(result.loading, false)
    })
  }
  test(`preserves canonical fields and selects five by descending stars: API_MODE=${apiMode}`, async () => {
    const payload = fixture()
    const original = structuredClone(payload)
    const result = await runTop5({ apiMode, payload })
    assert.deepEqual(JSON.parse(JSON.stringify(result.data)), {
      ...payload, repos: [payload.repos[1], payload.repos[4], payload.repos[3], payload.repos[5], payload.repos[6]],
    })
    assert.deepEqual(payload, original, 'must not mutate the fetched payload')
    assert.equal(result.loading, false)
  })
}

for (const stars of [[], [5, 20], [20, 20, 5]]) {
  test(`handles short lists and stable ties: ${JSON.stringify(stars)}`, async () => {
    const payload = fixture(stars)
    const result = await runTop5({ apiMode: true, payload })
    assert.deepEqual(JSON.parse(JSON.stringify(result.data)), {
      ...payload, repos: [...payload.repos].sort((a, b) => b.stars - a.stars),
    })
    assert.equal(result.loading, false)
  })
}

for (const failure of [{ ok: false }, { reject: true }]) {
  test(`settles loading without data on fetch failure: ${JSON.stringify(failure)}`, async () => {
    const result = await runTop5({ apiMode: true, payload: fixture(), ...failure })
    assert.equal(result.data, null)
    assert.equal(result.loading, false)
  })
}
