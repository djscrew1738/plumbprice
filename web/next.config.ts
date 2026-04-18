import type { NextConfig } from 'next'
import { withSentryConfig } from '@sentry/nextjs'

const apiOrigin =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000'

const nextConfig: NextConfig = {
  output: 'standalone',
  experimental: {},
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    minimumCacheTTL: 60 * 60 * 24 * 7, // 7 days
  },
  eslint: { ignoreDuringBuilds: true },
  async headers() {
    return [
      {
        // HTML pages: force CDN revalidation on every request
        source: '/((?!_next/static|_next/image|favicon.ico|icon|manifest|sw\\.js).*)',
        headers: [
          { key: 'Cache-Control', value: 'no-cache, no-store, must-revalidate' },
          { key: 'Pragma', value: 'no-cache' },
          { key: 'Expires', value: '0' },
          { key: 'CDN-Cache-Control', value: 'no-cache, no-store' },
          { key: 'Cloudflare-CDN-Cache-Control', value: 'no-cache, no-store' },
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
