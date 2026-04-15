import re

with open('web/src/components/layout/Sidebar.tsx', 'r') as f:
    content = f.read()

# Add imports if missing
if 'import { useEffect, useState }' not in content:
    content = content.replace("import { PRIMARY_NAV", "import { useEffect, useState }\nimport { estimatesApi, type EstimateListItem } from '@/lib/api'\nimport { formatCurrency } from '@/lib/utils'\nimport { RecentJobsList, type RecentJobItem } from '@/components/workspace/RecentJobsList'\nimport { PRIMARY_NAV")

# Add mapEstimateToSidebarJob
map_fn = """
function mapEstimateToSidebarJob(item: EstimateListItem): RecentJobItem {
  return {
    id: item.id,
    title: item.title || `${item.county} job`,
    statusLabel: item.status === 'draft' ? 'Awaiting details' : 'Estimate ready',
    timeLabel: item.county,
    totalLabel: item.grand_total > 0 ? formatCurrency(item.grand_total) : 'Draft',
    href: `/estimator?estimateId=${item.id}`,
  }
}
"""
if 'function mapEstimateToSidebarJob' not in content:
    content = content.replace('function SidebarContent', map_fn + '\nfunction SidebarContent')

# Add hooks to SidebarContent
hooks = """  const [recentJobs, setRecentJobs] = useState<RecentJobItem[]>([])
  const [loadingRecentJobs, setLoadingRecentJobs] = useState(true)

  useEffect(() => {
    let active = true

    estimatesApi
      .list({ limit: 4 })
      .then(response => {
        if (!active) return
        const payload = Array.isArray(response.data)
          ? response.data
          : ((response.data as { estimates?: EstimateListItem[] }).estimates ?? [])
        setRecentJobs(payload.slice(0, 4).map(mapEstimateToSidebarJob))
      })
      .catch(() => {
        if (active) setRecentJobs([])
      })
      .finally(() => {
        if (active) setLoadingRecentJobs(false)
      })

    return () => {
      active = false
    }
  }, [])
"""
if 'const [recentJobs' not in content:
    content = content.replace('  const pathname = usePathname()', '  const pathname = usePathname()\n' + hooks)

# Add RecentJobs list block before the end of SidebarContent
recent_jobs_block = """
      <div className="hidden border-t border-[color:var(--line)] px-3 py-4 lg:block">
        <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-ink)]">Recent Jobs</p>
        <RecentJobsList jobs={recentJobs} loading={loadingRecentJobs} compact />
      </div>
"""
if 'RecentJobsList jobs=' not in content:
    content = content.replace('</nav>\n    </div>', '</nav>\n' + recent_jobs_block + '    </div>')

with open('web/src/components/layout/Sidebar.tsx', 'w') as f:
    f.write(content)
