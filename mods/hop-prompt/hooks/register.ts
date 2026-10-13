// Asks once per session, when the context window reaches a threshold,
// whether to hop to a new session (csm's /hop skill).
//
// Context usage comes from the engine itself, `$.session.usage()`: the same
// figures the status line and /context show. Nothing is estimated and nothing
// needs configuring beyond the threshold.

import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

const HOP = 'Hop now'
const NOT_NOW = 'Not now'

const isAsked = atom({ plugin: 'hop-prompt', key: 'isAsked' } as const, false)

export const register: Register = (on, options) => {
  const limit = typeof options.percent === 'number' ? options.percent : 88

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)

    // Main loop only: a subagent's run raises turn.complete too.
    if (e.reason !== 'answer' || e.agentId !== undefined || (await read($, isAsked))) {
      return result
    }

    const { context } = await $.session.usage()
    const percent = context.percent ?? 0

    if (percent < limit) {
      return result
    }

    await update($, isAsked, () => true)
    // Not awaited: the turn ends now, the question stays up until answered.
    // A failure here must never surface as an unhandled rejection.
    void askToHop($, percent).catch(() => undefined)

    return result
  })
}

type Engine = Parameters<Parameters<Parameters<Register>[0]>[1]>[0]

const askToHop = async ($: Engine, percent: number) => {
  let answer: string

  try {
    answer = await $.ui.ask(
      `Context is at ${percent}%. Hop to a new session now? (Other: hop with a note for the next session)`,
      { options: [HOP, NOT_NOW], header: 'Hop' },
    )
  } catch {
    return // dismissed, or nobody to ask
  }

  if (answer === NOT_NOW) {
    return
  }

  // Anything typed under Other means yes, and is the note for the next session.
  const note = answer === HOP ? '' : answer.trim()
  const hasHop = (await $.command.list()).some(c => c.name === 'hop')

  if (hasHop) {
    await $.command.run({ command: 'hop', args: note })
  } else {
    $.ui.toast('hop-prompt: no /hop command in this session (install the csm hop skill)')
  }
}
