#!/usr/bin/env node
/**
 * Bundle size budget watchdog (a5-perf-budget, local complement to LHCI).
 *
 * Reads .next/build-manifest.json + .next/app-build-manifest.json and
 * sums the gzipped size of all JS/CSS chunks per route. Compares
 * against budgets below; exits 1 if any route blows its budget.
 *
 * Run locally after `npm run build`.
 *
 * Budgets are intentionally loose-but-realistic for a Next.js 15 app.
 * Tighten as we trim deps.
 */
import fs from 'node:fs'
import path from 'node:path'
import zlib from 'node:zlib'

const NEXT_DIR = path.resolve(process.cwd(), '.next')

const BUDGETS = {
  defaultRouteJs: 350_000,
  totalJs: 1_800_000,
  perRoute: {
    '/': 250_000,
    '/login': 220_000,
  },
}

function fileGzipSize(absPath) {
  if (!fs.existsSync(absPath)) return 0
  const buf = fs.readFileSync(absPath)
  return zlib.gzipSync(buf).length
}

function loadManifest(name) {
  const p = path.join(NEXT_DIR, name)
  if (!fs.existsSync(p)) return null
  return JSON.parse(fs.readFileSync(p, 'utf8'))
}

function main() {
  if (!fs.existsSync(NEXT_DIR)) {
    console.error('No .next/ dir — run `npm run build` first.')
    process.exit(2)
  }

  const buildManifest = loadManifest('build-manifest.json')
  const appManifest = loadManifest('app-build-manifest.json')
  const manifest = appManifest?.pages || buildManifest?.pages || {}

  if (!Object.keys(manifest).length) {
    console.error('No pages found in build manifest. Skipping (build may be partial).')
    process.exit(0)
  }

  let totalJs = 0
  const seenChunks = new Set()
  const violations = []

  for (const [route, chunks] of Object.entries(manifest)) {
    let routeBytes = 0
    for (const chunk of chunks) {
      const abs = path.join(NEXT_DIR, chunk)
      const sz = fileGzipSize(abs)
      routeBytes += sz
      if (!seenChunks.has(chunk)) {
        seenChunks.add(chunk)
        totalJs += sz
      }
    }
    const budget = BUDGETS.perRoute[route] ?? BUDGETS.defaultRouteJs
    const status = routeBytes > budget ? 'OVER' : 'ok'
    console.log(`${status.padEnd(4)}  ${route.padEnd(40)} ${(routeBytes / 1024).toFixed(1)} KB / ${(budget / 1024).toFixed(0)} KB`)
    if (routeBytes > budget) {
      violations.push({ route, routeBytes, budget })
    }
  }

  console.log('---')
  const totalStatus = totalJs > BUDGETS.totalJs ? 'OVER' : 'ok'
  console.log(`${totalStatus.padEnd(4)}  total JS (gz)                            ${(totalJs / 1024).toFixed(1)} KB / ${(BUDGETS.totalJs / 1024).toFixed(0)} KB`)
  if (totalJs > BUDGETS.totalJs) {
    violations.push({ route: '__total__', routeBytes: totalJs, budget: BUDGETS.totalJs })
  }

  if (violations.length) {
    console.error(`\n❌ ${violations.length} budget violation(s).`)
    process.exit(1)
  }
  console.log('\n✅ All routes within budget.')
}

main()
