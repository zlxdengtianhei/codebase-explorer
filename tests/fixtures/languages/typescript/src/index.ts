import { Worker as Alias, same as implSame } from "./impl";
export { Alias };
export type { Runner } from "./base";
export function same(): string { return "index"; }
export function entry(worker: import("./base").Runner): string {
  worker.run();
  missing();
  console.log(worker);
  return implSame();
}
export function dynamic(obj: any) { return obj.run(); }
