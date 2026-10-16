import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { test } from 'node:test'
import vm from 'node:vm'
import React from 'react'
import ts from 'typescript'

async function loadModule(relativePath, dependencies = {}, globals = {}) {
  const source = await readFile(new URL(relativePath, import.meta.url), 'utf8')
  const { outputText } = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true,
    target: ts.ScriptTarget.ES2023,
  } })
  const module = { exports: {} }
  vm.runInNewContext(outputText, {
    module, exports: module.exports,
    require: name => {
      assert.ok(name in dependencies, `Unexpected dependency: ${name}`)
      return dependencies[name]
    },
    console, crypto: globalThis.crypto, ...globals,
  })
  return module.exports
}

const api = await loadModule('../src/services/api.ts', {}, {
  fetch: async () => new Response(JSON.stringify({ detail: {
    code: 'manual_reconciliation_required', message: 'unsafe external text',
  } }), { status: 409 }),
})

// Run the actual App handlers with deterministic hooks and mocked HTTP services.
// No browser, live API, or additional test framework is required.
async function chatHarness(responses, reconcile = async () => ({ status: 'pending' })) {
  const slots = []
  let cursor = 0
  const useState = initial => {
    const index = cursor++
    if (!(index in slots)) slots[index] = typeof initial === 'function' ? initial() : initial
    return [slots[index], value => { slots[index] = typeof value === 'function' ? value(slots[index]) : value }]
  }
  const hooks = { ...React, useState, useEffect: () => {}, useRef: value => useState(() => ({ current: value }))[0] }
  const { App } = await loadModule('../src/App.tsx', {
    react: hooks,
    'lucide-react': Object.fromEntries(['Send', 'Bot', 'Sparkles', 'RefreshCw'].map(name => [name, name])),
    '@/components/Header': { Header: 'Header' },
    '@/components/ChatMessageItem': { ChatMessageItem: 'ChatMessageItem' },
    '@/components/DeviceTelemetryWidget': { DeviceTelemetryWidget: 'DeviceTelemetryWidget' },
    '@/components/RecentTicketsList': { RecentTicketsList: 'RecentTicketsList' },
    '@/services/api': {
      ManualReconciliationError: api.ManualReconciliationError,
      startConversation: async () => ({ id: 'conversation-1' }),
      sendChatMessage: async () => responses.shift(),
      fetchConversations: async () => [],
      reconcileIncident: reconcile,
    },
  })
  function render() {
    cursor = 0
    const nodes = []
    function visit(node) {
      if (Array.isArray(node)) return node.forEach(visit)
      if (!node || typeof node !== 'object') return
      nodes.push(node)
      visit(node.props?.children)
    }
    visit(App())
    return nodes
  }
  return {
    render,
    async send(text) {
      render().find(n => n.type === 'input').props.onChange({ target: { value: text } })
      const button = render().find(n => n.type === 'button' && n.props.children?.type === 'Send')
      await button.props.onClick()
      return render()
    },
  }
}

const response = response_type => ({ session_id: 'conversation-1', response_type, message: 'Support reply', created_at: '2026-10-16T00:00:00Z', sources: [] })
const statusButton = nodes => nodes.find(n => n.type === 'button' && n.props.children === 'Check incident status')

for (const followUp of ['hello', 'No thanks, please do not create a ticket']) {
  test(`pending verification stays available after ${followUp}`, async () => {
    const chat = await chatHarness([response('pending_verification'), response('conversational')])
    assert.ok(statusButton(await chat.send('VPN failed. Please escalate this.')))
    assert.ok(statusButton(await chat.send(followUp)))
  })
}

test('a verified incident clears the pending control', async () => {
  const chat = await chatHarness([response('pending_verification')], async () => ({
    status: 'created', ticket: { sys_id: 'incident-1', number: 'INC0010001' },
  }))
  const pending = await chat.send('VPN failed. Please escalate this.')
  await statusButton(pending).props.onClick()
  assert.equal(statusButton(chat.render()), undefined)
})

test('manual reconciliation conflict is visible and keeps pending verification', async () => {
  const chat = await chatHarness([response('pending_verification')], async () => {
    throw new api.ManualReconciliationError()
  })
  await statusButton(await chat.send('VPN failed. Please escalate this.')).props.onClick()
  const nodes = chat.render()
  assert.ok(statusButton(nodes))
  const alert = nodes.find(n => n.props.role === 'alert')
  assert.match(alert.props.children, /Manual reconciliation in ServiceNow is required/)
})

test('both API entry points recognize safe manual-reconciliation errors', async () => {
  await assert.rejects(api.reconcileIncident('conversation-1'), error => {
    assert.ok(error instanceof api.ManualReconciliationError)
    assert.doesNotMatch(error.message, /unsafe external text/)
    return true
  })
  await assert.rejects(api.sendChatMessage('Create a ticket', 'conversation-1'), api.ManualReconciliationError)
})
