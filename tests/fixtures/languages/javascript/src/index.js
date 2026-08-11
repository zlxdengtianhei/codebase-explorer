import { Worker as Alias, same as implSame } from "./impl.js";
export { Alias };
export { Base } from "./base.js";
export function same() { return "index"; }
export function entry(worker) {
  worker.run();
  missing();
  console.log(worker);
  return implSame();
}
export function dynamic(obj) { return obj.run(); }
