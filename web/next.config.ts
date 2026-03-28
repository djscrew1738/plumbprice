import type { NextConfig } from 'next'

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

export default nextConfig
