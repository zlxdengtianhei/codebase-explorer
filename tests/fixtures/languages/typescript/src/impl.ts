import type { Runner } from "./base";
export class Worker implements Runner {
  run(): string { return "ok"; }
}
export function same(): string { return "impl"; }
