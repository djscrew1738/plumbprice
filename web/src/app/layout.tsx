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
        <script dangerouslySetInnerHTML={{ __html: `(function(){var KEY='pp_chunk_reload',MAX=3;function getCount(){return parseInt(sessionStorage.getItem(KEY)||'0',10)||0;}function bump(){var c=getCount()+1;sessionStorage.setItem(KEY,String(c));return c;}function canRetry(){return getCount()<MAX;}function hardReload(){var c=bump();var u=new URL(window.location.href);u.searchParams.set('__pp_reload',String(c));u.searchParams.set('__pp_ts',String(Date.now()));window.location.replace(u.toString());}function isChunkMessage(msg){if(!msg)return false;return msg.indexOf('ChunkLoadError')!==-1||msg.indexOf('Loading chunk')!==-1||msg.indexOf('/_next/static/chunks/')!==-1;}window.addEventListener('error',function(e){var target=e&&e.target;var src=target&&(target.src||'');var msg=(e&&e.message)||((e&&e.error&&e.error.message)||'');if((target&&target.tagName==='SCRIPT'&&src.indexOf('/_next/static/chunks/')!==-1)||isChunkMessage(msg)){if(canRetry())hardReload();}},true);window.addEventListener('unhandledrejection',function(e){var reason=e&&e.reason;var msg=(reason&&reason.message)||String(reason||'');if(isChunkMessage(msg)&&canRetry())hardReload();});window.addEventListener('pageshow',function(){if(!window.location.search.includes('__pp_reload=')){sessionStorage.removeItem(KEY);}});})();` }} />
      </head>
      <body className="bg-[hsl(var(--background))] text-[color:var(--ink)] antialiased">
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  )
}
