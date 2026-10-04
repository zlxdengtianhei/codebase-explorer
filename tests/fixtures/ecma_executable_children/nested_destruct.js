export function pack({ a = () => 1, b: { c = function nested() { return 2; } } = {} } = {}) { return a(); }
