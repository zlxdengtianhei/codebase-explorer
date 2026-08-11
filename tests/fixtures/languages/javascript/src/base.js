export class Base {
  run() { throw new Error("abstract"); }
}
export function same() { return "base"; }
