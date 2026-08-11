export * from "./impl.js";
export async function load(name) { return import(name); }
const dynamicExports = {};
Object.assign(dynamicExports, globalThis.RUNTIME_EXPORTS);
export default dynamicExports;
