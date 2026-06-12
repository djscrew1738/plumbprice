#!/usr/bin/env node
/**
 * UI cleanup audit — Phase 0
 *
 * Scans src/app/ and src/components/ for patterns we want to eliminate during
 * the UI reorganization:
 *  - Raw <button> / <input> JSX elements outside src/components/ui/
 *  - Hardcoded Tailwind color utilities in className/class attributes
 *  - Legacy CSS classes (btn-primary, btn-ghost, input, badge-*, card*, glass*)
 *
 * Run with: node scripts/audit-ui-patterns.mjs
 */

import { readdir, readFile } from 'node:fs/promises'
import { join, relative } from 'node:path'

const ROOT = new URL('../src', import.meta.url).pathname

const COLOR_UTIL_REGEX =
  /\b(?:bg|text|border|ring|shadow|from|via|to|fill|stroke|outline|decoration|placeholder|caret|divide|ring-offset|accent)-(?:blue|red|green|emerald|amber|zinc|slate|gray|neutral|stone|orange|yellow|lime|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose)(?:-[0-9]{2,3})?(?:\/\d+)?\b/g

const LEGACY_CLASSES = [
  'btn-primary',
  'btn-ghost',
  'btn-secondary',
  'input',
  'badge-high',
  'badge-medium',
  'badge-low',
  'badge-success',
  'badge-warning',
  'badge-danger',
  'card',
  'card-sm',
  'glass-card',
  'glass',
  'shell-button-primary',
  'shell-card',
]
const LEGACY_CLASS_REGEX = new RegExp(
  `\\b(?:${LEGACY_CLASSES.map(c => c.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')).join('|')})\\b`,
  'g'
)

const CLASSNAME_REGEX = /(?:className|class)\s*=\s*(?:\{[^}]*[`"']([^`"']*)[`"'][^}]*\}|["']([^"']*)["'])/g

const RAW_ELEMENT_REGEX = /<\s*(button|input)\b/

async function* walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true })
  for (const entry of entries) {
    const path = join(dir, entry.name)
    if (entry.isDirectory()) {
      yield* walk(path)
    } else if (entry.isFile() && entry.name.endsWith('.tsx')) {
      yield path
    }
  }
}

const findings = {
  rawElements: [],
  hardcodedColors: [],
  legacyClasses: [],
}

for await (const file of walk(ROOT)) {
  const content = await readFile(file, 'utf8')
  const rel = relative(ROOT, file)

  const isPrimitive = rel.startsWith('components/ui/')

  for (const [lineNumber, line] of content.split('\n').entries()) {
    const ln = lineNumber + 1

    // Raw <button> / <input> outside primitives.
    if (!isPrimitive && RAW_ELEMENT_REGEX.test(line)) {
      findings.rawElements.push({ file: rel, line: ln, snippet: line.trim() })
    }

    // Scan className/class values for legacy classes and hardcoded colors.
    let match
    CLASSNAME_REGEX.lastIndex = 0
    while ((match = CLASSNAME_REGEX.exec(line)) !== null) {
      const classValue = match[1] ?? match[2]
      if (!classValue) continue

      const colorMatches = classValue.match(COLOR_UTIL_REGEX)
      if (colorMatches) {
        findings.hardcodedColors.push({
          file: rel,
          line: ln,
          matches: [...new Set(colorMatches)],
        })
      }

      const legacyMatches = classValue.match(LEGACY_CLASS_REGEX)
      if (legacyMatches) {
        findings.legacyClasses.push({
          file: rel,
          line: ln,
          matches: [...new Set(legacyMatches)],
        })
      }
    }
  }
}

function section(title, items) {
  console.log(`\n## ${title} (${items.length})`)
  if (items.length === 0) {
    console.log('None found.')
    return
  }
  const byFile = items.reduce((acc, item) => {
    acc[item.file] = acc[item.file] || []
    acc[item.file].push(item)
    return acc
  }, {})
  for (const [file, entries] of Object.entries(byFile).sort()) {
    console.log(`\n${file}`)
    for (const entry of entries) {
      const detail = entry.matches ? entry.matches.join(', ') : entry.snippet
      console.log(`  L${entry.line}: ${detail}`)
    }
  }
}

console.log('# UI Pattern Audit Report\n')
section('Raw <button> / <input> outside primitives', findings.rawElements)
section('Hardcoded Tailwind color utilities in className/class', findings.hardcodedColors)
section('Legacy CSS classes in className/class', findings.legacyClasses)

console.log('\n')
const total = findings.rawElements.length + findings.hardcodedColors.length + findings.legacyClasses.length
console.log(`Total findings: ${total}`)
process.exit(total > 0 ? 1 : 0)
