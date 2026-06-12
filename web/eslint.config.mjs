import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { FlatCompat } from '@eslint/eslintrc'
import jsxA11y from 'eslint-plugin-jsx-a11y'
import reactHooks from 'eslint-plugin-react-hooks'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const compat = new FlatCompat({
  baseDirectory: __dirname,
})

// ---------------------------------------------------------------------------
// UI cleanup rules (Phase 0)
//
// These rules are intentionally OFF during the migration so that the existing
// `npm run lint` baseline stays green. They will be enabled file-by-file as
// each domain is migrated to the primitive-first, token-driven design system.
// ---------------------------------------------------------------------------
const uiCleanupRules = {
  'no-raw-button-input': {
    meta: {
      type: 'suggestion',
      docs: {
        description: 'Disallow raw <button> and <input> JSX elements outside of src/components/ui/.',
      },
      schema: [],
    },
    create(context) {
      return {
        JSXElement(node) {
          const name = node.openingElement.name.name
          if (name === 'button' || name === 'input') {
            context.report({
              node,
              message: `Raw <${name}> should be replaced with the corresponding primitive from src/components/ui/.`,
            })
          }
        },
      }
    },
  },
  'no-hardcoded-tailwind-colors': {
    meta: {
      type: 'suggestion',
      docs: {
        description: 'Disallow hardcoded Tailwind color utilities (e.g. bg-blue-500).',
      },
      schema: [],
    },
    create(context) {
      const COLOR_UTIL_REGEX =
        /\b(?:bg|text|border|ring|shadow|from|via|to|fill|stroke|outline|decoration|placeholder|caret|divide|ring-offset|accent)-(?:blue|red|green|emerald|amber|zinc|slate|gray|neutral|stone|orange|yellow|lime|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose)(?:-[0-9]{2,3})?(?:\/\d+)?\b/g
      return {
        JSXAttribute(node) {
          if (node.name.name !== 'className' && node.name.name !== 'class') return
          const getValue = () => {
            if (node.value?.type === 'Literal') return node.value.value
            if (node.value?.type === 'JSXExpressionContainer' && node.value.expression.type === 'TemplateLiteral') {
              return node.value.expression.quasis.map(q => q.value.raw).join(' ')
            }
            return null
          }
          const value = getValue()
          if (!value) return
          const matches = value.match(COLOR_UTIL_REGEX)
          if (matches) {
            context.report({
              node,
              message: `Hardcoded Tailwind color utilities found: ${[...new Set(matches)].join(', ')}. Use design tokens instead.`,
            })
          }
        },
      }
    },
  },
  'no-legacy-css-classes': {
    meta: {
      type: 'suggestion',
      docs: {
        description: 'Disallow legacy CSS classes (btn-primary, card, input, etc.).',
      },
      schema: [],
    },
    create(context) {
      const LEGACY_CLASSES = [
        'btn-primary', 'btn-ghost', 'btn-secondary', 'input',
        'badge-high', 'badge-medium', 'badge-low',
        'badge-success', 'badge-warning', 'badge-danger',
        'card', 'card-sm', 'glass-card', 'glass',
        'shell-button-primary', 'shell-card',
      ]
      const LEGACY_CLASS_REGEX = new RegExp(
        `\\b(?:${LEGACY_CLASSES.map(c => c.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')).join('|')})\\b`,
        'g'
      )
      return {
        JSXAttribute(node) {
          if (node.name.name !== 'className' && node.name.name !== 'class') return
          const getValue = () => {
            if (node.value?.type === 'Literal') return node.value.value
            if (node.value?.type === 'JSXExpressionContainer' && node.value.expression.type === 'TemplateLiteral') {
              return node.value.expression.quasis.map(q => q.value.raw).join(' ')
            }
            return null
          }
          const value = getValue()
          if (!value) return
          const matches = value.match(LEGACY_CLASS_REGEX)
          if (matches) {
            context.report({
              node,
              message: `Legacy CSS classes found: ${[...new Set(matches)].join(', ')}. Migrate to primitives or design tokens.`,
            })
          }
        },
      }
    },
  },
}

const config = [
  {
    ignores: ['.next/**', 'node_modules/**', 'out/**', 'build/**', 'coverage/**', 'playwright-report/**', 'test-results/**', 'next-env.d.ts'],
  },
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  {
    plugins: {
      'jsx-a11y': jsxA11y,
      'react-hooks': reactHooks,
      'ui-cleanup': { rules: uiCleanupRules },
    },
    rules: {
      ...jsxA11y.flatConfigs.recommended.rules,
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // Migration rules — OFF until each domain is cleaned up.
      'ui-cleanup/no-raw-button-input': 'off',
      'ui-cleanup/no-hardcoded-tailwind-colors': 'off',
      'ui-cleanup/no-legacy-css-classes': 'off',
    },
  },
]

export default config
