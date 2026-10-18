export function makeCounter(start) {
  let value = start;
  return {
    async bump(delta) {
      value += delta;
      return value;
    },
    read() {
      return value;
    },
  };
}

export const run = async (fn) => {
  const inner = () => fn();
  return inner();
};
