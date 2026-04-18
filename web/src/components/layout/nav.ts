import {
  BarChart3,
  BriefcaseBusiness,
  FileOutput,
  FileStack,
  FileText,
  House,
  Layers,
  MessageSquare,
  MoreHorizontal,
  Package,
  RefreshCw,
  Settings,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from 'lucide-react'

export interface AppNavItem {
  href: string
  label: string
  icon: LucideIcon
}

export interface PageMeta {
  title: string
  eyebrow: string
}

export const PRIMARY_NAV: AppNavItem[] = [
  { href: '/', label: 'Home', icon: House },
  { href: '/estimates', label: 'Jobs', icon: FileText },
  { href: '/pipeline', label: 'Pipeline', icon: BriefcaseBusiness },
]

export const SECONDARY_NAV: AppNavItem[] = [
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/sessions', label: 'Chat History', icon: MessageSquare },
  { href: '/suppliers', label: 'Suppliers', icon: Package },
  { href: '/documents', label: 'Documents', icon: FileStack },
  { href: '/admin', label: 'Admin', icon: Settings },
  { href: '/settings', label: 'Settings', icon: SlidersHorizontal },
]

export const MORE_LINKS: AppNavItem[] = [
  ...SECONDARY_NAV,
  { href: '/admin/users', label: 'Team', icon: Users },
  { href: '/admin/jobs', label: 'Failed Jobs', icon: RefreshCw },
  { href: '/blueprints', label: 'Blueprints', icon: Layers },
  { href: '/proposals', label: 'Proposals', icon: FileOutput },
]

export const MOBILE_TABS = [
  PRIMARY_NAV[0],
  PRIMARY_NAV[1],
  PRIMARY_NAV[2],
  { href: '#more', label: 'More', icon: MoreHorizontal },
] as const

export const PAGE_META: Record<string, PageMeta> = {
  '/': { title: 'Field Pricing', eyebrow: 'Start a quote or attach job files' },
  '/estimator': { title: 'Pricing Workspace', eyebrow: 'Build and review a live estimate' },
  '/estimates': { title: 'Saved Estimates', eyebrow: 'Resume and review recent pricing work' },
  '/pipeline': { title: 'Pipeline', eyebrow: 'Track open bids and won work' },
  '/analytics': { title: 'Analytics', eyebrow: 'Outcome insights and performance trends' },
  '/suppliers': { title: 'Suppliers', eyebrow: 'Compare catalog pricing' },
  '/admin': { title: 'Admin', eyebrow: 'Manage pricing rules and templates' },
  '/admin/users': { title: 'Team', eyebrow: 'Manage users, roles and invitations' },
  '/admin/jobs': { title: 'Failed Jobs', eyebrow: 'Worker observability and retries' },
  '/blueprints': { title: 'Blueprints', eyebrow: 'Upload-led estimating entry point' },
  '/proposals': { title: 'Proposals', eyebrow: 'Customer-ready bid outputs' },
  '/documents': { title: 'Documents', eyebrow: 'Manage uploaded documents' },
  '/sessions': { title: 'Chat History', eyebrow: 'Browse and resume past conversations' },
  '/settings': { title: 'Settings', eyebrow: 'Manage your account and organization' },
}

export function matchesPathname(pathname: string, href: string) {
  if (href === '/') {
    return pathname === '/' || pathname === '/estimator' || pathname.startsWith('/estimator/')
  }

  return pathname === href || pathname.startsWith(href + '/')
}

export function getPageMeta(pathname: string): PageMeta {
  if (PAGE_META[pathname]) return PAGE_META[pathname]

  // Match nested routes by longest prefix
  const match = Object.keys(PAGE_META)
    .filter(key => key !== '/' && pathname.startsWith(key + '/'))
    .sort((a, b) => b.length - a.length)[0]

  if (match) return PAGE_META[match]

  return PAGE_META['/']
}
