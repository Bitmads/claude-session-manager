export type Asked = boolean

declare module 'claude-code' {
  interface PluginState {
    'hop-prompt': { isAsked: Asked }
  }
}
