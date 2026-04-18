'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api'

interface AuthUser {
  id: number
  email: string
  full_name: string
  role: string
  is_admin: boolean
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TOKEN_KEY = 'pp_token'
const USER_KEY  = 'pp_user'

/** Return the remaining JWT lifetime in seconds (capped at 0). */
function cookieLifetimeFromJwt(token: string): number {
  try {
    const payload = token.split('.')[1]
    if (!payload) return 3600
    // Base64URL -> Base64 -> JSON
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized + '==='.slice((normalized.length + 3) % 4)
    const decoded = JSON.parse(atob(padded)) as { exp?: number }
    if (typeof decoded.exp !== 'number') return 3600
    const remaining = decoded.exp - Math.floor(Date.now() / 1000)
    // Clamp to [60s, 7d] so a clock skew doesn't produce a useless cookie.
    return Math.max(60, Math.min(remaining, 60 * 60 * 24 * 7))
  } catch {
    return 3600
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user,    setUser]    = useState<AuthUser | null>(null)
  const [token,   setToken]   = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Hydrate from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    const storedUser  = localStorage.getItem(USER_KEY)
    if (storedToken && storedUser) {
      try {
        const remaining = cookieLifetimeFromJwt(storedToken)
        if (remaining <= 60) {
          // Token is already expired (or within the 60s clamp floor) — clear state.
          localStorage.removeItem(TOKEN_KEY)
          localStorage.removeItem(USER_KEY)
          document.cookie = 'pp_token=; path=/; max-age=0'
        } else {
          setToken(storedToken)
          setUser(JSON.parse(storedUser) as AuthUser)
          api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
          document.cookie = `pp_token=${storedToken}; path=/; max-age=${remaining}; SameSite=Lax`
        }
      } catch {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    // Backend login uses OAuth2PasswordRequestForm (form-encoded)
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)

    const res = await api.post('/auth/login', form.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })

    const { access_token, user: userData } = res.data as { access_token: string; user: AuthUser }

    localStorage.setItem(TOKEN_KEY, access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    // Derive cookie lifetime from the JWT's actual exp so middleware and the
    // token expire together. Falls back to 1h if the token is malformed.
    const cookieMaxAge = cookieLifetimeFromJwt(access_token)
    document.cookie = `pp_token=${access_token}; path=/; max-age=${cookieMaxAge}; SameSite=Lax`
    api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
    setToken(access_token)
    setUser(userData)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    // Clear auth cookie used by middleware
    document.cookie = 'pp_token=; path=/; max-age=0'
    delete api.defaults.headers.common['Authorization']
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
