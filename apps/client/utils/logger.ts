/**
 * Logger - 统一的前端日志工具
 *
 * 生产环境下静默 debug/log/warn，仅保留 error。
 * 开发环境下全部输出。
 */

const isDev = import.meta.env.DEV;

type LogArgs = Parameters<typeof console.log>;

export const logger = {
  debug(...args: LogArgs) {
    if (isDev) console.debug('[DEBUG]', ...args);
  },

  log(...args: LogArgs) {
    if (isDev) console.log(...args);
  },

  warn(...args: LogArgs) {
    if (isDev) console.warn(...args);
  },

  /** error 始终输出（生产环境也需要可观测性） */
  error(...args: LogArgs) {
    console.error(...args);
  },

  /** 仅开发环境输出的 info */
  info(...args: LogArgs) {
    if (isDev) console.info(...args);
  },
};

export default logger;
