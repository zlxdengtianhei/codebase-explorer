interface Shape {
  area(): number;
}

type Alias = number | string;

enum Color {
  Red,
  Green,
}

export const apply = <T,>(value: T): T => value;

export class Circle implements Shape {
  radius = 0;
  area(): number {
    return 3 * this.radius * this.radius;
  }
}
