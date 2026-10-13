import { expect, test } from 'claude-code/testing'

const turn = { answer: 'done', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' } as const

// Stands in for the engine: context usage, the ask dialog, the command list.
const DISMISS = '<dismissed>'

// The plugin asks without holding the turn open, so a test that expects the
// hop waits for the command itself: `ran` resolves when /hop runs.
const engine = (on: any, percent: number, answer: string, log: string[]) => {
  let hopRan = () => {}
  const ran = new Promise<void>(resolve => {
    hopRan = resolve
  })

  on('session.usage', () => ({
    value: { startedAt: 0, context: { window: 1_000_000, tokens: percent * 10_000, percent }, rateLimits: [] },
  }))
  on('turn.complete', (_$: unknown, e: { answer: string }) => ({ text: e.answer }))
  on('tool.call', { tool: 'AskUserQuestion' }, (_$: unknown, e: any) => {
    log.push(`ask: ${e.questions[0].question}`)
    if (answer === DISMISS) return { deny: 'dismissed' }
    // The dialog answers with the chosen label, or the text typed under Other.
    return { result: { questions: e.questions, answers: { [e.questions[0].question]: answer } } }
  })
  on('command.list', () => ({ value: [{ name: 'hop', description: 'hop', source: 'skill' }] }))
  on('command.run', (_$: unknown, e: { command: string; args: string }) => {
    log.push(`run: /${e.command} [${e.args}]`)
    hopRan()
    return {}
  })

  return ran
}

test('stays silent below the threshold', async ($, on) => {
  const log: string[] = []
  engine(on, 87, 'Hop now', log)
  await $.turn.complete(turn)
  expect(log).toEqual([])
})

test('at the threshold asks, and "Hop now" runs /hop', async ($, on) => {
  const log: string[] = []
  const ran = engine(on, 88, 'Hop now', log)
  await $.turn.complete(turn)
  await ran
  expect(log.length).toEqual(2)
  expect(log[0].startsWith('ask: Context is at 88%.')).toEqual(true)
  expect(log[1]).toEqual('run: /hop []')
})

test('text typed under Other becomes the note', async ($, on) => {
  const log: string[] = []
  const ran = engine(on, 91, 'start with the failing test', log)
  await $.turn.complete(turn)
  await ran
  expect(log[1]).toEqual('run: /hop [start with the failing test]')
})

test('"Not now" runs nothing and it never asks again', async ($, on) => {
  const log: string[] = []
  engine(on, 95, 'Not now', log)
  await $.turn.complete(turn)
  await $.turn.complete({ ...turn, turnId: 't2' })
  expect(log.length).toEqual(1)
})

test('ignores subagent turns and interrupted turns', async ($, on) => {
  const log: string[] = []
  engine(on, 99, 'Hop now', log)
  await $.turn.complete({ ...turn, agentId: 'a1' })
  await $.turn.complete({ ...turn, reason: 'aborted', isAborted: true })
  expect(log).toEqual([])
})

test('a dismissed dialog runs nothing', async ($, on) => {
  const log: string[] = []
  engine(on, 90, DISMISS, log)
  await $.turn.complete(turn)
  expect(log.length).toEqual(1)
})
