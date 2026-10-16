import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import ts from 'typescript'

let compiledDirectory
let ChatMessageItem
before(async () => {
  compiledDirectory = await mkdtemp(path.join(process.cwd(), 'node_modules/.priority-test-'))
  const source = await readFile(new URL('../src/components/ChatMessageItem.tsx', import.meta.url), 'utf8')
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2023 } })
  const compiledFile = path.join(compiledDirectory, 'ChatMessageItem.mjs')
  await writeFile(compiledFile, outputText)
  ;({ ChatMessageItem } = await import(pathToFileURL(compiledFile).href))
})
after(async () => { if (compiledDirectory) await rm(compiledDirectory, { recursive: true }) })

function render(priority, ticketPriority, hasTicket = true) {
  return renderToStaticMarkup(React.createElement(ChatMessageItem, {
    message: {
      id: 'saved-message', sender: 'assistant', text: 'Incident recorded.',
      timestamp: '2026-10-15T12:00:00Z', responseType: hasTicket ? 'ticket_created' : 'escalation_offered',
      classification: { intent: 'knowledge_inquiry', priority, assignment_group: 'Network Support' },
      ticket: hasTicket ? { number: 'INC0010001', sys_id: 'a'.repeat(32), provider: 'servicenow', priority: ticketPriority } : undefined,
    },
  }))
}

test('saved P4 classification displays the returned P5 ticket priority everywhere', () => {
  const html = render('P4', 'P5')
  assert.match(html, /P5/)
  assert.doesNotMatch(html, /P4/)
})

test('missing provider priority stays unspecified instead of using a prediction', () => {
  const html = render('P3', undefined)
  assert.match(html, /Unspecified/)
  assert.doesNotMatch(html, /P3/)
})

test('P5 classification renders before a ticket exists', () => {
  assert.match(render('P5', undefined, false), /P5/)
})
