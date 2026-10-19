export type Size = number;
export interface Box { value: Size; get(): number; }
export enum Color { Red, Blue }
export const LIMIT = 8;
export let mutable = 1;
export const helper = (x: Size) => x + LIMIT;
class Item { static FIELD = 4; get() { return LIMIT; } }
