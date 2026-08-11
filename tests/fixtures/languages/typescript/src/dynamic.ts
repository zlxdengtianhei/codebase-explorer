export * from "./impl";
export async function load(name: string) { return import(name); }
const dynamicExports: Record<string, unknown> = {};
Object.assign(dynamicExports, globalThis);
export default dynamicExports;
