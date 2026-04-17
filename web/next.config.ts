import type { NextConfig } from 'next'
import { withSentryConfig } from '@sentry/nextjs'

const apiOrigin =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000'

const nextConfig: NextConfig = {
  output: 'standalone',
  experimental: {},
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
