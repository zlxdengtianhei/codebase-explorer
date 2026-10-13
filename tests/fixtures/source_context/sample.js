import { helper } from "./helper.js";

export function compute(x) {
  return helper(x) + 1;
}

export const double = (y) => y * 2;

class Widget {
  constructor(id) {
    this.id = id;
  }
  render() {
    return this.id;
  }
}

const asyncArrow = async (z) => {
  return z;
};

export default compute;
