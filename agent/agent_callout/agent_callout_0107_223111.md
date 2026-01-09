# Experiment Callout - 2026-01-07

*Generated: 2026-01-07T22:31:11.614996*

---

### [App download bottom sheet TTL test](https://ops.doordash.team/decision-systems/experiments/909b3fdb-df4a-4a67-86d3-7a2f4363b3e1?analysisId=8869f3cc-db9b-4054-b0b3-45c64e86c941)
**Feature:** Shorten the mWeb app-open/download prompt cooldown (30d → 21d / 14d) to push more high-intent users back into the native app sooner.  
**Status:** 8. Ramping | **Rollout:** —

**Secondary Metrics (Multi-arm; showing only significant):**
- **twoweek:**  
  - webx_new_cx_conversion_rate: **-1.0%** (p=0.0017) – significant negative  
  - webx_web_new_cx_conversion_rate: **-1.1%** (p=0.0056) – significant negative  
  - core_quality_hqdr: **-0.10%** (p=0.0027) – significant negative  
  - *Interpretation:* The more frequent prompt is likely adding friction for true web-new users (they’re less likely to complete as New Cx) and may be slightly degrading delivery quality mix (could be shifting volume into harder-to-serve cohorts/contexts, or simply noise but statistically real).

**Analysis:**
- Notably, **top-line WebX primary metrics are not significant** for either arm, but the **New Cx funnel is** (down) in the 21d arm—this is directionally opposite the “get me to the app” intent if it’s cannibalizing first web orders before users are ready to switch.
- The HQDR dip, while small, is a signal worth validating before ramping further (especially if the prompt changes who/when we acquire orders).

**Recommendation:**
- **Hold further ramp on the 21d (“twoweek”) arm** and run a quick cut: impact by **logged-in vs logged-out**, and **app-installed vs not** (hypothesis: we’re hurting truly new web users while helping “already-app” users, but the benefit isn’t showing in primaries yet).
- If we must proceed, **prefer the 14d (“twentyone”) arm** for now only because it shows **no significant negatives** (still verify it doesn’t hide the same issue as it gains power).

---

### [Block bad address at checkout](https://ops.doordash.team/decision-systems/experiments/43e5e1fc-e857-4278-8f4d-5b46be452692?analysisId=944d4986-d1a7-4471-8279-0cbf8edca5e9)
**Feature:** Adds friction/confirmation for “risky” new-user addresses pre-checkout to reduce NUX non-delivery (ND) and improve delivery quality.  
**Status:** 8. In experiment | **Rollout:** 100%  
**Arms:** treatment_cart, treatment_address

**Primary Metrics:**
- **dashpass_signup (treatment_cart): +5.0%** (p=0.0033) – significant positive  
  - *Interpretation:* The checkout/cart intervention is increasing DashPass attach—likely by keeping users in a more “committed” checkout state (or improving perceived trust/clarity at purchase time).
- **consumers_mau (treatment_cart): -0.9%** (p=0.0316) – significant negative  
  - *Interpretation:* Despite more DashPass signups, fewer unique consumers are completing ≥1 delivery. This is a classic friction tradeoff: we may be preventing some low-quality addresses, but also blocking/losing some would-have-ordered users.
- **order_rate_per_entity_7d (New Cx, treatment_cart): -21.6%** (p=0.0223) – significant negative  
  - *Interpretation:* This is a large move. It suggests the cart-based friction is disproportionately deterring (or filtering out) new customers, which is risky given the experiment’s goal is *quality without killing NUX conversion*.

**Guardrails (significant negative only):**
- **core_quality_late20 (Active Cx): +153.6%** (p=0.0162) – ALERT (treatment_address)  
- **core_quality_late20 (Active Cx): +143.0%** (p=0.0279) – ALERT (treatment_cart)  
  - *Risk:* A big relative increase in 20+ min late deliveries for Active Cx is a serious experience degradation. Even if absolute rates are small, this is a red flag that the change may be impacting fulfillment flow/timing assumptions (e.g., address edits/confirmations occurring later, causing tighter ETAs or operational mismatches).
- **Web performance regressions** in treatment_cart (page load latency / TBT / hitch): multiple significant negatives  
  - *Risk:* Suggests the cart-based UX is heavier; could directly explain the MAU/New Cx ordering drop via slower/buggier checkout.

**Analysis:**
- The pattern is consistent: **treatment_cart drives a business-positive attach (DashPass)** but comes with **meaningful funnel and performance costs**, and **both arms show lateness guardrail issues** for Active Cx. That lateness signal is particularly concerning because it contradicts the expected quality win narrative.
- Because this is 100% rollout, these are not small edge effects—this needs immediate scrutiny.

**Recommendation:**
- **Do not ramp/ship as-is.** Treat this as a rollback candidate pending investigation.
- Immediate debug checklist:
  1. Verify whether the lateness lift is due to **ETA math changes** (e.g., address “correction” happening after quote) vs real delivery delays.
  2. Compare lateness impact on orders with **address edit / pin adjust / apt add** events.
  3. For treatment_cart, address the **web perf regressions** (likely causal for the NUX order-rate drop).
- If we keep testing, **treatment_address is the lesser evil** (no significant DashPass win, but also fewer broad negatives); however, lateness guardrail still blocks shipping.

---

### [Travel v2](https://ops.doordash.team/decision-systems/experiments/4b5d0888-2f28-4e68-9089-fac7bd38271c?analysisId=d1fa0d0d-6741-4d12-92c8-dbca63e3473c)
**Feature:** iOS geofence-triggered push notifications at major US airports to drive post-landing ordering.  
**Status:** 8. In experiment | **Rollout:** —

**Primary Metrics:**
- order_rate_per_entity_7d: **-0.19%** (p=1.3e-05) – significant negative  
- consumers_mau: **-0.12%** (p=1.7e-06) – significant negative  
  - *Interpretation:* At current reach/copy/frequency, the airport push is not translating into incremental ordering; instead it’s slightly suppressing engagement.

**Guardrails (significant negative only):**
- cx_app_quality_page_load_latency_ios: **+0.14%** (p=0.024) – ALERT  
  - *Risk:* Small but real iOS perf regression; could be incidental, but given the core metrics are negative, there’s no upside to justify additional risk.

**Recommendation:**
- **Pause expansion** and confirm whether we’re measuring the right population: this should be evaluated on the *geofence-exposed cohort* (not overall iOS) and by airport. If this is diluted exposure, consider tightening targeting (only high-intent, lapsed, or travelers with recent browse).
- If cohort-level still negative, **iterate on notification relevance** (copy, timing window after landing, and suppression rules) before re-running.

---

### [mWeb onboarding](https://ops.doordash.team/decision-systems/experiments/3905f4a7-174a-407f-aebd-f91a309d0134?analysisId=775207ad-2e6d-4283-8e77-6aee61253ce3)
**Feature:** Post-mWeb signup “get me to the app” flow (app download prompt + fallback SMS/promo) to increase app adoption and retention.  
**Status:** 8. In experiment | **Rollout:** 100%

**Primary Metrics (WebX-first):**
- webx_order_rate: **+16.0%** (p≈0) – significant positive  
- webx_conversion_rate: **+6.6%** (p≈0) – significant positive  
  - *Interpretation:* This is a strong funnel win: more visitors are converting and placing orders when we introduce the onboarding flow.

**Key Context / Conflicts:**
- consumers_mau: **-11.9%** (p≈0) – significant negative  
  - *Interpretation:* For web experiments, MAU can be misleading due to identity stitching; the **WebX metrics suggest real conversion lift**, and the MAU drop likely reflects users shifting into app ordering / different identity resolution rather than true demand loss.
- Channel mix shift explains the win:
  - webx_in_app_order_rate: **+81.4%** (p≈0) – significant positive
  - webx_web_order_rate: **-8.2%** (p≈0) – significant negative  
  - *Interpretation:* We are successfully moving ordering from web → app (desired), not necessarily creating entirely new demand on web.

**Guardrails (significant negative only):**
- cx_app_quality_page_load_latency_web: **+4.8%** (p=0.00043) – ALERT  
- cx_app_quality_inp_web: **+6.6%** (p=0.00376) – ALERT  
- cx_app_quality_action_load_latency_web: **+3.6%** (p=0.00633) – ALERT  
  - *Risk:* The experience is heavier/slower. If unaddressed, these could erode the conversion gains over time (especially on lower-end devices).

**Recommendation:**
- **Keep running / prep to ship** given the large WebX primary wins, but **treat web performance as the gating item**:
  - Profile the new bottom sheet + fallback logic on the explore/signup path; optimize bundle size and reduce blocking scripts.
  - Monitor whether conversion gains decay as the experiment matures (perf regressions often show delayed impact).
- Add a breakdown of WebX lift by **device class / network** to ensure we’re not winning only on high-end devices.

---

### Skipped (no significant movements)
- **LiteGuests** (only guardrail-significant web errors; no meaningful metric movement yet to justify callout—monitor but not actioned today).