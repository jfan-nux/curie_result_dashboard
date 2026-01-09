# Experiment Callout - 2026-01-07

*Generated: 2026-01-07T22:19:55.059106*

---

## Daily experiment callout — 2026-01-07

### [App download bottom sheet TTL test](https://ops.doordash.team/decision-systems/experiments/909b3fdb-df4a-4a67-86d3-7a2f4363b3e1?analysisId=8869f3cc-db9b-4054-b0b3-45c64e86c941)
**Feature:** Reduces the cooldown for “open/download the app” prompts on mWeb (30 → 21 days, plus a 14d arm) to push more users into the native app experience.  
**Status:** 8. Ramping | **Rollout:** (not listed)

**Primary Metrics:** _(none significant)_

**Secondary Metrics (significant):**
- webx_new_cx_conversion_rate: **-1.04%** (p=0.00168) — **significant negative**
  - *Interpretation:* Fewer web visitors become **new** purchasers; earlier/more frequent prompts may be interrupting first-time conversion.
- webx_web_new_cx_conversion_rate: **-1.11%** (p=0.00564) — **significant negative**
- stex_new_rx_conversion: **-0.45%** (p=0.0413) — **significant negative**
- core_quality_hqdr: **-0.10%** (p=0.00269) — **significant negative**
  - *Interpretation:* Slight degradation in delivery quality among exposed traffic (small but statistically real).

**Analysis:**
The pattern is consistent with a **friction tradeoff**: surfacing app-open/download prompts more often can “win” long-term app adoption, but in the short run it can distract/interrupt high-intent sessions—especially **net-new** users who are least tolerant of extra steps. The simultaneous small HQDR dip suggests we may be shifting marginal users/orders into scenarios that are slightly harder to fulfill (or changing mix) rather than purely improving routing to app.

**Recommendation:**
- **Do not ramp further yet.** Add instrumentation/readout focused on: prompt impression rate → dismissal rate → subsequent checkout starts for **new users** specifically.
- Consider **new-user suppression** (or softer UX) until conversion stabilizes, since new-cx conversion is moving opposite the hypothesis.

---

### [mWeb onboarding](https://ops.doordash.team/decision-systems/experiments/3905f4a7-174a-407f-aebd-f91a309d0134?analysisId=775207ad-2e6d-4283-8e77-6aee61253ce3)
**Feature:** After mWeb signup, pushes users to **download/open the app** and complete app onboarding; fallback is lightweight SMS opt-in + promo awareness on web.  
**Status:** 8. In experiment | **Rollout:** 100%

**Primary Metrics:**
- webx_order_rate: **+16.00%** (p≈0) — **significant positive**
  - *Interpretation:* Exposed web visitors place more orders overall, consistent with successfully driving some users into a higher-converting app path.
- webx_conversion_rate: **+6.60%** (p≈0) — **significant positive**
- consumers_mau: **-11.92%** (p≈0) — **significant negative**
- order_rate_per_entity_7d: **-9.37%** (p≈0) — **significant negative**

**Guardrails (significant negative):**
- cx_app_quality_inp_web: **+6.64%** (p=0.00376) — **ALERT**
- cx_app_quality_page_load_latency_web: **+4.85%** (p=0.00043) — **ALERT**
- cx_app_quality_action_load_latency_web: **+3.57%** (p=0.00633) — **ALERT**
  - *Risk:* The treatment is measurably hurting web performance; this can create longer-term conversion/retention drag and makes the “MAU down” more concerning.

**Analysis (conflicting pattern, large movements):**
This is a classic **composition + denominator** story:
- The experiment likely **reclassifies some activity as “in-app”** (good for webx order rate/conversion) while simultaneously reducing the number of users who end up as “distinct consumers with a delivery” in the measured population (MAU down).  
- At the same time, “orders per exposed entity” metrics are down, which suggests we may be **increasing the count of exposed entities** (more people bucketed/triggered) faster than we’re increasing ordering—i.e., broader exposure with uneven engagement.
- The web performance guardrails degrading supports a plausible causal mechanism for MAU/order-rate-per-entity softness: extra onboarding surfaces / heavier page modules can slow down web, increasing drop-offs for users who *don’t* successfully transition to app.

**Recommendation:**
- Treat as **promising but not ready to ship** until performance issues are addressed.
- Action items:
  1. **Fix web perf regressions** (INP + latency): audit added scripts/modules and reduce blocking work on the signup→address flow.
  2. Validate whether MAU drop is **measurement/migration** (users moving to app) vs true loss: check net new app sessions + app orders among exposed.
  3. If migration is real, consider optimizing to **retain web fallback quality** (faster fallback, fewer steps) to prevent losing users who won’t install.

---

### [Block bad address at checkout](https://ops.doordash.team/decision-systems/experiments/43e5e1fc-e857-4278-8f4d-5b46be452692?analysisId=944d4986-d1a7-4471-8279-0cbf8edca5e9)
**Feature:** Adds friction at checkout to force risky new-user addresses to be corrected (aim: reduce ND / improve HQDR, especially for NUX).  
**Status:** 8. In experiment | **Rollout:** 100%

**Primary Metrics (significant):**
- dashpass_signup: **+4.99%** (p=0.00332) — **significant positive**
  - *Interpretation:* The address confirmation step may be acting like a “commitment moment” (users who proceed are more likely to subscribe), or it’s selecting for higher-intent users.
- consumers_mau: **-0.90%** (p=0.0316) — **significant negative**
- order_rate_per_entity_7d (New Cx): **-21.63%** (p=0.0223) — **significant negative** ⚠️
  - *Interpretation:* For New Cx, the added friction is likely causing meaningful drop-off or deferring first orders.

**Secondary Metrics (selected):**
- core_quality_hqdr: **+0.68%** (p=0.00254) — **significant positive**
- hqdr_ratio: **+0.70%** (p=0.00195) — **significant positive**
  - *Interpretation:* Quality is improving in the intended direction, consistent with catching bad addresses before order placement.

**Guardrails (significant negative only):**
- core_quality_late20 (Active): **+143–154%** (p=0.016–0.028) — **ALERT**
  - *Risk:* A large relative increase in 20+ min late among Active users (even if base rate is small) is a service-quality red flag.
- Multiple app quality guardrails (web latency/TBT/hitch, etc.) show significant negatives.
  - *Risk:* Potential UX/perf regressions compounding funnel drop-off.

**Analysis:**
This is a **quality vs conversion tradeoff** showing up strongly where we’d expect:
- Improved HQDR indicates the intervention is filtering/fixing problematic deliveries.
- The steep New Cx order-rate drop suggests the friction is too blunt (or triggering too often / too early), turning away exactly the segment we’re trying to retain.
- The late20 spike for Active users is unexpected and may indicate: (a) spillover to non-NUX traffic, (b) operational changes in delivery preference defaults, or (c) selection effects (harder deliveries making it through).

**Recommendation:**
- **Immediate deep dive on the late20 guardrail** and traffic targeting:
  - Confirm the treatment is truly scoped to risky NUX addresses; if not, tighten targeting.
  - Audit “risky address” classifier thresholds (false positives could be adding friction without benefit).
- Consider a **softer step** (inline suggestions/autofill, one-tap confirm) before hard-blocking checkout for New Cx.

---

### [LiteGuests](https://ops.doordash.team/decision-systems/experiments/a34f5e72-1fb3-4fb1-aa04-ff2a5506abedhttps://ops.doordash.team/decision-systems/experiments/a34f5e72-1fb3-4fb1-aa04-ff2a5506abed?analysisId=6cb900be-d52b-4315-adbb-501541980ce6)
**Feature:** Enables Campaign Manager targeting/promos for “LiteGuests” (web guests) to show guest banners.  
**Status:** 8. In experiment | **Rollout:** (not listed)

**Guardrails (significant negative):**
- cx_app_quality_crash_web (explore page): **significant negative** (p=0.00047) — **ALERT**
- cx_app_quality_page_action_error_web (create address / add payment / delete cart): **significant negative** (p=0.002–0.035) — **ALERT**
- cx_app_quality_action_load_latency_web (delete cart): **+176.96%** (p=0.0108) — **ALERT**

**Analysis:**
Even without primary metric wins called out today, the guardrail cluster strongly suggests **stability/performance regressions on core guest flows** (address creation, payment add, cart ops). Because this experiment changes promo/banner logic, the likely mechanism is additional client-side logic/requests firing during sensitive actions.

**Recommendation:**
- **Pause ramp / reduce exposure** until web crashes & action errors are understood.
- Triage by correlating error/crash spikes with the new banner rendering + promo evaluation calls (especially around cart mutation endpoints).

---

**No-callout:** Travel v2 had no significant movements flagged today.