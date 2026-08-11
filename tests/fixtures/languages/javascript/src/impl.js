import { Base } from "./base.js";
export class Worker extends Base {
  run() { return "ok"; }
}
export function same() { return "impl"; }
