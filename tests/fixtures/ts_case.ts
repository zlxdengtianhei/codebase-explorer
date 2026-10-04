export interface Job<T> {
  id: string;
  payload: T;
}

export class Queue<T> {
  private items: Job<T>[] = [];

  enqueue(job: Job<T>): void {
    this.items.push(job);
  }

  async take(): Promise<Job<T> | undefined> {
    return this.items.shift();
  }
}

export function mapJobs<T, R>(jobs: Job<T>[], fn: (value: T) => R): R[] {
  return jobs.map((job) => fn(job.payload));
}

export type Result<T> = { ok: true; value: T } | { ok: false; error: string };
