import type { Metadata, Viewport } from 'next'
import { ClientLayout } from '@/components/layout/ClientLayout'
import './globals.css'

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#d4702c',
}

export const metadata: Metadata = {
  title: 'PlumbPrice AI',
  description: 'AI-powered plumbing estimator for DFW contractors',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
  },
  icons: {
    icon: '/favicon.ico',
    apple: '/icon-192.png',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* Dark mode init — must run before first paint to avoid flash */}
        <script dangerouslySetInnerHTML={{ __html: `(function(){var t=localStorage.getItem('pp_theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark');}})();` }} />
        {/* Auto-reload on stale chunk errors (CDN cache mismatch) */}
        <script dangerouslySetInnerHTML={{ __html: `(function(){var KEY='pp_chunk_reload',MAX=2;window.addEventListener('error',function(e){var src=e.target&&(e.target.src||'');if(e.target&&e.target.tagName==='SCRIPT'&&src.indexOf('/_next/')!==-1){var count=parseInt(sessionStorage.getItem(KEY)||'0',10);if(count<MAX){sessionStorage.setItem(KEY,String(count+1));window.location.reload();}}},true);window.addEventListener('load',function(){sessionStorage.removeItem(KEY);});})();` }} />
      </head>
      <body className="bg-[hsl(var(--background))] text-[color:var(--ink)] antialiased">
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  )
}
