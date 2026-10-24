// Conflict detection and resolution (AGENTS.md section 10). The losing record
// is marked supersededBy (kept, penalized in ranking), never deleted.
// Auto-resolve only at decision confidence >= 0.70; everything else queues.

import { DEFAULTS, clamp01 } from "./types.ts";
import type { ConflictRecord, MemoryRecord } from "./types.ts";
import { cosine, foldAccents } from "./embeddings.ts";
import type { MemoryStoreService } from "./memoryStore.ts";
import { snapshot } from "./memoryStore.ts";
import type { TrustLedgerService } from "./trustLedger.ts";

const OPPOSING_PAIRS: [RegExp, RegExp][] = [
  [/\balways\b/i, /\bnever\b/i],
  [/\benable[ds]?\b/i, /\bdisable[ds]?\b/i],
  [/\bprefer[s]?\b/i, /\bavoid[s]?|dislike[s]?\b/i],
  [/\bon\b/i, /\boff\b/i],
  [/\byes\b/i, /\bno\b/i],
  // FocoCerto adaptation: Portuguese opposing pairs, tested on accent-folded text.
  [/\bsempre\b/i, /\bnunca\b/i],
  [/\b(habilitad|ativad)[oa]s?\b/i, /\b(desabilitad|desativad)[oa]s?\b/i],
  [/\b(liberad[oa]s?|abert[oa]s?|desbloquead[oa]s?|desimpedid[oa]s?|transitave(l|is))\b/i,
   /\b(alagad[oa]s?|bloquead[oa]s?|interditad[oa]s?|fechad[oa]s?|obstruid[oa]s?|intransitave(l|is))\b/i],
  [/\bdisponive(l|is)\b/i, /\bindisponive(l|is)\b/i],
];

export class ConflictDetectionService {
  private conflicts: ConflictRecord[] = [];
  private seq = 0;

  constructor(
    private store: MemoryStoreService,
    private ledger: TrustLedgerService,
    private clock: () => number,
    private actor: string
  ) {}

  scan(): ConflictRecord[] {
    const found: ConflictRecord[] = [];
    const all = this.store.all();
    for (let i = 0; i < all.length; i++) {
      for (let j = i + 1; j < all.length; j++) {
        const conflict = this.check(all[i], all[j]);
        if (conflict) {
          found.push(conflict);
          this.conflicts.push(conflict);
          this.ledger.log(conflict.memoryA, "conflict_detected", this.actor, {
            details: { with: conflict.memoryB, reason: conflict.reason, confidence: conflict.confidence },
          });
        }
      }
    }
    return found;
  }

  // FocoCerto adaptation (additive): scan only the pairs that involve one record,
  // typically the one just written. Same check() and ledger entries as scan(),
  // with the older record as memoryA (scan() order), without re-logging old pairs.
  scanFor(memoryId: string): ConflictRecord[] {
    const found: ConflictRecord[] = [];
    const target = this.store.get(memoryId);
    if (!target) return found;
    for (const other of this.store.all()) {
      if (other.id === memoryId) continue;
      const conflict = this.check(other, target);
      if (conflict) {
        found.push(conflict);
        this.conflicts.push(conflict);
        this.ledger.log(conflict.memoryA, "conflict_detected", this.actor, {
          details: { with: conflict.memoryB, reason: conflict.reason, confidence: conflict.confidence },
        });
      }
    }
    return found;
  }

  private check(a: MemoryRecord, b: MemoryRecord): ConflictRecord | undefined {
    // supersedes relation suppresses conflict: it is an intended replacement.
    if (a.supersedes === b.id || b.supersedes === a.id || a.supersededBy === b.id || b.supersededBy === a.id) return undefined;

    const sim = cosine(a.embedding, b.embedding);
    let reason = "";
    let confidence = 0;

    for (const [p, q] of OPPOSING_PAIRS) {
      // FocoCerto adaptation: test on accent-folded text (identity for ASCII).
      const ca = foldAccents(a.content);
      const cb = foldAccents(b.content);
      if ((p.test(ca) && q.test(cb)) || (q.test(ca) && p.test(cb))) {
        if (sim > 0.5) {
          reason = "opposing phrase pair on similar content";
          confidence = 0.5 + 0.3 * sim;
        }
      }
    }
    if (!reason && sim > 0.8) {
      const numsA = a.content.match(/\d+(\.\d+)?/g) ?? [];
      const numsB = b.content.match(/\d+(\.\d+)?/g) ?? [];
      if (numsA.length && numsB.length && numsA.join() !== numsB.join()) {
        reason = "high-similarity conflicting numeric values";
        confidence = 0.55 + 0.25 * sim;
      }
    }
    if (!reason) return undefined;

    // Confidence modifiers (section 10.1).
    const sharedEntities = a.entities.filter((e) => b.entities.includes(e));
    if (sharedEntities.length > 0) confidence += 0.1;
    if (a.domain === b.domain) confidence += 0.05;
    if (a.relatedTo.includes(b.id)) confidence -= 0.1; // explicit relation lowers false positives

    return {
      id: `conflict-${++this.seq}`,
      memoryA: a.id,
      memoryB: b.id,
      reason,
      confidence: clamp01(confidence),
      resolved: false,
    };
  }

  // Weighted auto-decision heuristics (section 10.2).
  autoResolve(conflict: ConflictRecord): "resolved" | "queued" {
    const a = this.store.get(conflict.memoryA)!;
    const b = this.store.get(conflict.memoryB)!;
    const scoreOf = (m: MemoryRecord) =>
      0.3 * (m.lastAccessed / Math.max(1, this.clock())) +
      0.2 * Math.min(1, m.accessCount / 10) +
      0.25 * m.confidence +
      0.1 * Math.min(1, m.content.length / 200) +
      0.15 * (m.provenance.origin === "user_correction" ? 1 : 0.5);
    const sa = scoreOf(a);
    const sb = scoreOf(b);
    const margin = Math.abs(sa - sb) / Math.max(sa, sb);
    const decisionConfidence = clamp01(conflict.confidence * 0.6 + margin * 0.8);

    if (decisionConfidence < DEFAULTS.conflictAutoResolveGate) return "queued";

    const winner = sa >= sb ? a : b;
    const loser = sa >= sb ? b : a;
    const prev = snapshot(loser);
    loser.supersededBy = winner.id; // kept and penalized, never deleted
    conflict.resolved = true;
    conflict.resolution = winner.id === conflict.memoryA ? "keep_a" : "keep_b";
    this.ledger.log(loser.id, "conflict_resolved", this.actor, {
      previousState: prev,
      newState: snapshot(loser),
      details: { conflictId: conflict.id, winner: winner.id, decisionConfidence: Number(decisionConfidence.toFixed(3)) },
    });
    this.store.persist();
    return "resolved";
  }

  // FocoCerto adaptation (additive): supervisor-mode resolution for a conflict
  // the auto-decision queued (spec: "only flagged-uncertain conflicts escalate
  // to a supervisor agent or queue"). Same effect as a resolved autoResolve:
  // the loser is marked supersededBy, nothing is deleted, and the ledger gets
  // conflict_resolved with previous and new state.
  resolveBySupervisor(conflict: ConflictRecord, winnerId: string, actor: string, details: Record<string, unknown> = {}): "resolved" {
    if (winnerId !== conflict.memoryA && winnerId !== conflict.memoryB) {
      throw new Error(`H-MEM: ${winnerId} is not part of ${conflict.id}`);
    }
    const winner = this.store.get(winnerId)!;
    const loser = this.store.get(winnerId === conflict.memoryA ? conflict.memoryB : conflict.memoryA)!;
    const prev = snapshot(loser);
    loser.supersededBy = winner.id;
    conflict.resolved = true;
    conflict.resolution = winner.id === conflict.memoryA ? "keep_a" : "keep_b";
    this.ledger.log(loser.id, "conflict_resolved", actor, {
      previousState: prev,
      newState: snapshot(loser),
      details: { conflictId: conflict.id, winner: winner.id, mode: "supervisor", ...details },
    });
    this.store.persist();
    return "resolved";
  }

  queue(): ConflictRecord[] {
    return this.conflicts.filter((c) => !c.resolved);
  }
}
