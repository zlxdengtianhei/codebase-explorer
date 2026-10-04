export type Handler = (cb: () => void) => number;
export interface Sink { handle(cb: () => void): void; }
export function typed(cb: () => number): number { return cb(); }
