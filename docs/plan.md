# Plan (STUB): B-ACDC (Access Control Door Controller) — C++ example

> **STATUS: STUB.** Seed facts below. Expand from
> [`bacnet-profile-plan-template.md`](../../bacnet-profile-plan-template.md) after the
> sample plans ([B-LD](../../BACnetProfileExample-B-LD-CPP/docs/plan.md),
> [B-BC](../../BACnetProfileExample-B-BC-CPP/docs/plan.md)) are reviewed.

**Profile:** B-ACDC · **Family:** Annex L.7 (Miscellaneous) · **Role:** B ·
**Archetype:** Specialized-object · **Difficulty:** 2/5 · **Build wave:** 1

**Thesis:** a door controller — locks/unlocks a door modeled by an **Access Door**
object. This example = B-SS baseline + writes + one Access Door object. **Canonical
source for F-ACCESS** (the first access-control object).

## Required BIBBs (profiles.md L.7)
`DS-RP-B, DS-WP-B, DS-ACAD-B; DM-DDB-B, DM-DOB-B`. No AE/SCHED/T.

## Services to enable
- ReadProperty (1), WriteProperty (15). Baseline discovery. Nothing else.

## Objects (baseline + )
- Access Door 1 (`OBJECT_TYPE_ACCESS_DOOR`) — commandable Present_Value
  (Door_Value enum: lock/unlock); confirm required props (`Door_Status`,
  `Lock_Status`, `Secured_Status`, `Door_Alarm_State`) in `CASBACnetStackDLL.h`.
  Colour name: extend the runbook colour table (propose a name, coordinate).

## Shared features
- **DEFINE:** F-ACCESS (Access Door — first access object).
- **REUSE:** F-OUTPUTS (B-SA — the door is commanded via WriteProperty).

## Known stack gaps
- None expected (profiles.md: ✅ S61, DS-ACAD-B verified RP+WP end-to-end against
  `accessDoor:1`). Confirm the Access Door required-property set empirically.

## Notes / open questions
- Is the Access Door Present_Value commandable (Priority_Array) or a plain
  writable enum? Confirm — it determines whether F-OUTPUTS applies as-is.
