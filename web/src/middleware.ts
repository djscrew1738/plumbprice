import { NextRequest, NextResponse } from 'next/server'

const PUBLIC_PATHS = ['/login', '/register', '/_next', '/favicon', '/icons', '/manifest', '/api']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public paths and static assets
  if (PUBLIC_PATHS.some(p => pathname.startsWith(p)) || pathname.includes('.')) {
    return NextResponse.next()
  }

  // Check for auth token in cookies or localStorage isn't accessible in middleware,
  // so we check the pp_token cookie if set, otherwise let client-side handle it.
  // The primary guard is the 401 interceptor in api.ts, but this prevents the
  // flash of protected content before client-side redirect kicks in.
  const token = request.cookies.get('pp_token')?.value

  // If no cookie token, check Authorization header (for API-forwarded requests)
  if (!token && !request.headers.get('authorization')) {
    // For the homepage, allow access (it redirects to login if needed client-side)
    if (pathname === '/') return NextResponse.next()

    // For all other protected routes, redirect to login
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirect', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|icons|manifest).*)',
  ],
}
