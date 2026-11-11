import { helper } from "./util.js";
export function run(items: number[]): number {
  let total = 0;
  for (const item of items) total += helper(item);
  return total;
}
