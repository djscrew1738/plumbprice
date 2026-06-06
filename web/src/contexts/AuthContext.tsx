'use client'

import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
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
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user,    setUser]    = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  // Hydrate from HttpOnly cookie-backed session.
  useEffect(() => {
    let active = true
    const hydrate = async () => {
      try {
        const res = await api.get<AuthUser>('/auth/me')
        if (!active) return
        setUser(res.data)
      } catch {
        if (!active) return
        setUser(null)
      } finally {
        if (active) setLoading(false)
      }
    }
    void hydrate()
    return () => { active = false }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    // Backend login uses OAuth2PasswordRequestForm (form-encoded)
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)

    const res = await api.post('/auth/login', form.toString(), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })

    const { user: userData } = res.data as { access_token?: string; user: AuthUser }
    setUser(userData)
  }, [])

  const logout = useCallback(() => {
    void api.post('/auth/logout').catch((err) => {
      if (process.env.NODE_ENV === 'development') {
        console.warn('Logout request failed', err)
      }
    })
    setUser(null)
  }, [])

  // Memoize the context value so consumers only re-render when user or
  // loading actually changes — not on every unrelated AuthProvider render.
  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout]
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
