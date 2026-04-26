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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user,    setUser]    = useState<AuthUser | null>(null)
  const [token,   setToken]   = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  // Hydrate from HttpOnly cookie-backed session.
  useEffect(() => {
    let active = true
    const hydrate = async () => {
      try {
        const res = await api.get<AuthUser>('/auth/me')
        if (!active) return
        setUser(res.data)
        setToken(null)
      } catch {
        if (!active) return
        setUser(null)
        setToken(null)
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

    const { access_token, user: userData } = res.data as { access_token?: string; user: AuthUser }
    setToken(access_token ?? null)
    setUser(userData)
  }, [])

  const logout = useCallback(() => {
    void api.post('/auth/logout').catch(() => {})
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
