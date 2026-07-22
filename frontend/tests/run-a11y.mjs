import { AxeBuilder } from '@axe-core/playwright'
import { chromium, expect } from '@playwright/test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'

const baseUrl = 'http://127.0.0.1:4173'
const tokenStorageKey = 'personal-ai-assistant.access-token'

const server = spawn(
  process.execPath,
  ['./node_modules/vite/bin/vite.js', 'preview', '--host', '127.0.0.1'],
  {
    cwd: new URL('..', import.meta.url),
    stdio: 'pipe',
  },
)

let browser

try {
  await waitForServer()
  browser = await chromium.launch()

  await runCheck('authentication screen', async (page) => {
    await page.goto(baseUrl)
    assert(await page.getByRole('main', { name: /sign in/i }).isVisible())
    assert(await page.getByLabel('Email').isVisible())
    assert(await page.getByLabel('Password').isVisible())
    await assertNoAxeViolations(page)
  })

  await runCheck('main application surfaces', async (page) => {
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, 'test-token')
    }, tokenStorageKey)
    await page.goto(baseUrl)
    assert(await page.getByRole('navigation', { name: /conversation history/i }).isVisible())
    assert(await page.getByRole('main', { name: /conversation/i }).isVisible())
    assert(await page.getByRole('region', { name: /desktop settings/i }).isVisible())
    assert(await page.getByRole('region', { name: /memories/i }).isVisible())
    assert(await page.getByRole('region', { name: /knowledge documents/i }).isVisible())
    await page.getByRole('button', { name: /^Accessibility planning, 2 messages$/ }).click()
    assert(await page.getByText('Assistant response using project context.').isVisible())
    assert(await page.getByText('Used memory: 1 saved memory').isVisible())
    await assertNoAxeViolations(page)
  })

  await runCheck('streamed markdown response', async (page) => {
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, 'test-token')
    }, tokenStorageKey)
    await page.goto(baseUrl)
    await page.getByLabel('Message').fill('Show markdown')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByRole('heading', { name: 'Markdown heading' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Project link' })).toBeVisible()
    await expect(page.getByText('<script>alert("x")</script>')).toBeVisible()
    assert.equal(await page.locator('script', { hasText: 'alert("x")' }).count(), 0)
    await assertNoAxeViolations(page)
  })

  await runCheck('skip link keyboard focus', async (page) => {
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, 'test-token')
    }, tokenStorageKey)
    await page.goto(baseUrl)
    await page.keyboard.press('Tab')
    assert(await page.getByRole('link', { name: /skip to conversation/i }).evaluate(isFocused))
    await page.keyboard.press('Enter')
    assert(await page.locator('#conversation-main').evaluate(isFocused))
  })

  console.log('Accessibility checks passed: 4')
} finally {
  await browser?.close()
  server.kill()
}

async function runCheck(name, callback) {
  const context = await browser.newContext()
  const page = await context.newPage()
  await mockApi(page)

  try {
    await callback(page)
    console.log(`ok - ${name}`)
  } finally {
    await context.close()
  }
}

async function assertNoAxeViolations(page) {
  const results = await new AxeBuilder({ page }).analyze()
  assert.deepEqual(results.violations, [])
}

async function waitForServer() {
  const deadline = Date.now() + 30_000
  while (Date.now() < deadline) {
    try {
      const response = await fetch(baseUrl)
      if (response.ok) {
        return
      }
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 250))
    }
  }

  throw new Error('Vite preview server did not start.')
}

function isFocused(element) {
  return document.activeElement === element
}

async function mockApi(page) {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname.replace('/api', '')
    const method = request.method()

    if (path === '/health') {
      await route.fulfill({ json: { application: 'Personal AI Assistant', status: 'ok' } })
      return
    }

    if (path === '/desktop/status') {
      await route.fulfill({
        json: {
          desktop_mode: true,
          app_version: 'test',
          data_directory: 'C:\\Users\\Test\\AppData\\Local\\Personal AI Assistant',
          logs_directory: 'C:\\Users\\Test\\AppData\\Local\\Personal AI Assistant\\logs',
          database_backend: 'sqlite',
          backend_status: 'ready',
          openai_api_key_configured: true,
        },
      })
      return
    }

    if (path === '/desktop/secrets/openai' && method === 'GET') {
      await route.fulfill({ json: { configured: true, masked: 'sk-...test' } })
      return
    }

    if (path === '/conversations') {
      await route.fulfill({
        json: [
          {
            conversation_id: 'conversation-1',
            title: 'Accessibility planning',
            created_at: '2026-07-21T00:00:00Z',
            updated_at: '2026-07-21T00:01:00Z',
            message_count: 2,
            first_user_message: 'How should we harden the UI?',
          },
        ],
      })
      return
    }

    if (path === '/conversations/conversation-1') {
      await route.fulfill({
        json: {
          conversation_id: 'conversation-1',
          title: 'Accessibility planning',
          created_at: '2026-07-21T00:00:00Z',
          updated_at: '2026-07-21T00:01:00Z',
          message_count: 2,
          first_user_message: 'How should we harden the UI?',
          messages: [
            {
              id: 1,
              role: 'user',
              content: 'How should we harden the UI?',
              created_at: '2026-07-21T00:00:00Z',
            },
            {
              id: 2,
              role: 'assistant',
              content: 'Assistant response using project context.',
              response_metadata: {
                knowledge: {
                  enabled: true,
                  mode: 'explicit_enabled',
                  retrieval_count: 1,
                  sources: [
                    {
                      document_id: 1,
                      document_name: 'accessibility-notes.md',
                      chunk_id: 1,
                      chunk_index: 0,
                      start_character: 0,
                      end_character: 80,
                      distance: 0,
                    },
                  ],
                  warning: null,
                },
                memory: {
                  enabled: true,
                  mode: 'planner',
                  retrieval_count: 1,
                  sources: [{ category: 'preference', key: 'screen_reader' }],
                },
                actions: [],
              },
              created_at: '2026-07-21T00:01:00Z',
            },
          ],
        },
      })
      return
    }

    if (path === '/chat/stream' && method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          'event: start',
          'data: {"conversation_id":"streamed-conversation"}',
          '',
          'event: delta',
          'data: {"text":"# Markdown heading\\n\\n- One item\\n\\n[Project link](https://example.com)\\n\\n<script>alert(\\"x\\")</script>"}',
          '',
          'event: complete',
          'data: {"response":"# Markdown heading\\n\\n- One item\\n\\n[Project link](https://example.com)\\n\\n<script>alert(\\"x\\")</script>","conversation_id":"streamed-conversation","metadata":{"knowledge":{"enabled":false,"mode":"explicit_disabled","retrieval_count":0,"sources":[],"warning":null},"memory":{"enabled":false,"mode":"explicit_disabled","retrieval_count":0,"sources":[]},"actions":[]}}',
          '',
          '',
        ].join('\n'),
      })
      return
    }

    if (path === '/documents') {
      await route.fulfill({
        json: [
          {
            id: 1,
            original_filename: 'accessibility-notes.md',
            content_type: 'text/markdown',
            file_size: 1200,
            processing_status: 'completed',
            error_message: null,
            metadata: {},
            uploaded_at: '2026-07-21T00:00:00Z',
          },
        ],
      })
      return
    }

    if (path === '/memories') {
      await route.fulfill({
        json: [
          {
            id: 1,
            user_id: 1,
            category: 'preference',
            key: 'favorite_programming_language',
            value: 'TypeScript',
          },
        ],
      })
      return
    }

    await route.fulfill({ status: 404, json: { detail: `Unhandled mock route: ${path}` } })
  })
}
