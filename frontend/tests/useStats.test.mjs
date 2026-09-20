// Run with: node --test tests/useStats.test.mjs
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

async function runStats({ apiMode, base = '/', payload, ok = true, reject = false }) {
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
  const initial = exports.useStats()
  assert.equal(initial.data, null)
  assert.equal(initial.loading, true)
  assert.equal(initial.error, null)
  await setImmediate()
  return { data: states[0], loading: states[1], error: states[2], urls }
}

for (const apiMode of [false, true]) {
  for (const base of ['/', '/ai-intel/']) {
    test(`uses same-site canonical stats: API_MODE=${apiMode}, BASE_URL=${base}`, async () => {
      const payload = { total_articles: 42, daily_trends: [], source_health: {}, keyword_trends: [] }
      const result = await runStats({ apiMode, base, payload })
      assert.deepEqual(result.urls, [`${base}data/stats.json`])
      assert.equal(result.data, payload)
      assert.equal(result.loading, false)
      assert.equal(result.error, null)
    })
  }
  for (const failure of [{ ok: false, error: '503' }, { reject: true, error: 'offline' }]) {
    test(`reports fetch failure: API_MODE=${apiMode}, ${failure.error}`, async () => {
      const result = await runStats({ apiMode, ...failure })
      assert.equal(result.data, null)
      assert.equal(result.loading, false)
      assert.equal(result.error, failure.error)
    })
  }
}
