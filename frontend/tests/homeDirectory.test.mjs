import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const page = readFileSync(new URL('../src/pages/HomePage.tsx', import.meta.url), 'utf8')

test('homepage has jump directory and stable section anchors', () => {
  assert.match(page, /目录|Contents/)
  for (const id of ['github-top5', 'model-leaderboard', 'curated-articles', 'github-trending']) {
    assert.match(page, new RegExp(`id=["']${id}["']`))
  }
})
