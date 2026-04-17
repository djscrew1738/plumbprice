'use client'

import { useState } from 'react'
import { User, Building2 } from 'lucide-react'
import { TabsRoot, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs'
import { ProfilePage } from './ProfilePage'
import { OrganizationPage } from './OrganizationPage'

export function SettingsLayout() {
  const [activeTab, setActiveTab] = useState('profile')

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-[color:var(--ink)]">Settings</h1>
        <p className="text-sm text-[color:var(--muted-ink)] mt-1">
          Manage your account and organization
        </p>
      </div>

      <TabsRoot value={activeTab} onChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="profile" icon={User}>
            Profile
          </TabsTrigger>
          <TabsTrigger value="organization" icon={Building2}>
            Organization
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <ProfilePage />
        </TabsContent>

        <TabsContent value="organization">
          <OrganizationPage />
        </TabsContent>
      </TabsRoot>
    </div>
  )
}
