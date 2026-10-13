export function classify(n: number): string {
  let label: string;
  if (n < 0) { label = 'neg'; } else { label = 'pos'; }
  return label;
}
