import type { NextConfig } from 'next'
import { withSentryConfig } from '@sentry/nextjs'

const apiOrigin =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000'

const nextConfig: NextConfig = {
  output: 'standalone',
  experimental: {
    // Tree-shake these heavy libraries by importing only what we use.
    // Without this, e.g. `import { X } from 'lucide-react'` pulls in 1k+ icons.
    optimizePackageImports: [
      'lucide-react',
      'framer-motion',
      'date-fns',
      'recharts',
      '@tanstack/react-query',
    ],
  },
  webpack(config, { isServer }) {
    if (!isServer) {
      // Rename the polyfills chunk to avoid Cloudflare WAF false-positive that
      // blocks any URL containing "polyfills" (anti-polyfill.io supply-chain rule).
      const splitChunks = config.optimization?.splitChunks as Record<string, unknown> & { cacheGroups?: Record<string, { name?: string }> } | undefined
      if (splitChunks?.cacheGroups?.polyfills) {
        splitChunks.cacheGroups.polyfills.name = 'pf'
      }
    }
    return config
  },
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    minimumCacheTTL: 60 * 60 * 24 * 7, // 7 days
  },
  eslint: { ignoreDuringBuilds: true },
  async headers() {
    return [
      {
        // HTML pages: short browser-side TTL but allow Cloudflare to cache &
        // revalidate so most page loads are served from the edge instead of
        // round-tripping to the Node origin (which is on a tunnel, not local
        // to most visitors). The chunk-error auto-reload script in layout.tsx
        // handles the rare stale-HTML / fresh-chunks mismatch.
        source: '/((?!_next/static|_next/image|favicon.ico|icon|manifest|sw\\.js).*)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=30, stale-while-revalidate=300' },
          // Cloudflare: cache at edge for 60s, serve stale up to 1h while
          // revalidating in background. s-maxage applies to shared caches only.
          { key: 'CDN-Cache-Control', value: 'public, s-maxage=60, stale-while-revalidate=3600' },
          { key: 'Cloudflare-CDN-Cache-Control', value: 'public, s-maxage=60, stale-while-revalidate=3600' },
        ],
      },
    ]
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${apiOrigin.replace(/\/$/, '')}/api/:path*`,
      },
    ]
  },
}

export default process.env.NEXT_PUBLIC_SENTRY_DSN
  ? withSentryConfig(nextConfig, {
      org: process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,
      silent: true,
      widenClientFileUpload: true,
      tunnelRoute: '/monitoring',
      disableLogger: true,
    })
  : nextConfig
