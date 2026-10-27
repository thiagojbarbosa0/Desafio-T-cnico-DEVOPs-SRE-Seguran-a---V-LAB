/**
 * Drop asynchronous results from an earlier authenticated session.
 * A UID alone is insufficient: A -> B -> A must invalidate work started by
 * the first A session. This module has no Firebase/React runtime dependency.
 */
export class SessionGate {
  private generation = 0;
  private uid: string | null = null;

  begin(uid: string | null): number {
    this.generation += 1;
    this.uid = uid;
    return this.generation;
  }

  isCurrent(uid: string | null, generation: number): boolean {
    return this.uid === uid && this.generation === generation;
  }
}
