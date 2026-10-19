export interface Props { value: number; }
export const LIMIT = 8;
export const Widget = (p: Props) => <span>{p.value}</span>;
