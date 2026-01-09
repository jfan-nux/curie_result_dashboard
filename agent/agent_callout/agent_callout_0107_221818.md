# Experiment Callout - 2026-01-07

*Generated: 2026-01-07T22:18:18.209510*

---

## Daily experiment callout — 2026-01-07

### [App download bottom sheet TTL test](https://ops.doordash.team/decision-systems/experiments/909b3fdb-df4a-4a67-86d3-7a2f4363b3e1?analysisId=8869f3cc-db9b-4054-b0b3-45c64e86c941)
**Feature:** Shortens the cooldown on mWeb “open/download the app” prompts (30→21 days, and 14d arm) to push more users into native app.
**Status:** 8. Ramping | **Rollout:** (not set)

**Primary Metrics:** none significant.

**Secondary Metrics (significant):**
- **webx_new_cx_conversion_rate:** **-1.04%** (p=0.0017) — significant negative  
- **webx_web_new_cx_conversion_rate:** **-1.11%** (p=0.0056) — significant negative  
- **stex_new_rx_conversion:** **-0.45%** (p=0.0413) — significant negative  
- **core_quality_hqdr:** **-0.10%** (p=0.0027) — significant negative

**Analysis:**
The experiment is intended to *increase* downstream engagement by nudging users to native app sooner, but the only significant movement is *conversion softness* (especially New Cx) plus a small but statistically clear HQDR dip. That pattern is consistent with “extra prompt frequency” introducing friction for first-time/high-intent web users (more interruptions → fewer complete signup/checkout journeys), without yet generating enough incremental app orders to compensate within the 2-week window. The HQDR dip is small, but directionally concerning: if the prompt shifts marginal users into orders with weaker address/intent signals (or increases abandoned/reattempted flows), we can see slightly worse delivery outcomes.

**Likely Causes (ranked):**
1. **Incremental friction in the web funnel outweighs app reactivation benefit (short-term)** (Confidence: Medium)  
   - Evidence: New Cx conversion down while top-line primary metrics are flat.
2. **Composition shift toward riskier orders** (Confidence: Low/Medium)  
   - Evidence: HQDR down slightly alongside conversion declines.

**Recommendation:**
- **Do not ramp further yet.** Add an interim read focused on *where* New Cx conversion is lost (LP→storepage, storepage→checkout, checkout completion). If losses concentrate around prompt impressions, consider **frequency capping by user type** (e.g., suppress for first-session New Cx / pre-first-order users) before continuing.

---

### [Block bad address at checkout](https://ops.doordash.team/decision-systems/experiments/43e5e1fc-e857-4278-8f4d-5b46be452692?analysisId=944d4986-d1a7-4471-8279-0cbf8edca5e9)
**Feature:** Adds friction pre-checkout for new users with “risky” addresses to reduce non-delivery / improve delivery quality.
**Status:** 8. In experiment | **Rollout:** 100%

**Primary Metrics (significant):**
- **consumers_mau (overall):** **-0.90%** (p=0.0316) — significant negative  
  - *Interpretation: fewer distinct consumers placing 1+ deliveries; friction is likely suppressing completion for some users.*
- **order_rate_per_entity_7d (New Cx):** **-21.63%** (p=0.0223) — significant negative  
  - *Interpretation: among New Cx, the added address friction is materially reducing ordering frequency/throughput.*

- **dashpass_signup:** **+4.99%** (p=0.0033) — significant positive  
  - *Interpretation: users who make it through may be higher-intent / more subscription-inclined, but this is not offsetting the New Cx order-rate loss.*

**Secondary Metrics (notable):**
- **hqdr_ratio / core_quality_hqdr (overall):** **~+0.68%** (p≈0.002) — significant positive (quality improves overall)
- **active_share_7d:** **-0.67%** (p=0.0288) — significant negative

**Guardrails (significant negative only):**
- **core_quality_late20 (Active lifestage):** **+143% to +154%** (p=0.016 / 0.028) — **ALERT**  
  - *Risk: sharp increase in 20+ minute late deliveries for Active users suggests operational spillover or selection effects; this is a serious CX risk.*
- Multiple **app/web performance regressions** (page load latency / TBT / hitch) — significant negative  
  - *Risk: degraded UX can directly explain the MAU and New Cx order-rate declines (slower pages + more friction = more abandonment).*

**Analysis:**
This is a classic **quality vs growth trade**: overall HQDR improves (good), but New Cx order rate collapses and MAU declines (bad). The magnitude of the New Cx hit (>-20%) is too large to treat as “acceptable friction” without strong evidence that ND is dropping substantially (ND itself is not showing a significant change yet). The guardrail late20 spike in Active users is particularly concerning because the feature is targeted at NUX/risky addresses—yet the lateness impact appears in Active, which points to **system-level effects** (e.g., increased address edit flows, ETA recalculation issues, or latency/perf regressions influencing order creation/dispatch timing).

**Likely Causes (ranked):**
1. **UX/performance degradation amplifying friction effects** (Confidence: High)  
   - Evidence: multiple significant app/web latency/hitch guardrails + MAU down + New Cx order rate down.
2. **Over-triggering / false positives on “risky” classification** (Confidence: Medium)  
   - Evidence: New Cx order rate down massively; quality up suggests filtering out marginal orders rather than “fixing” them.
3. **Operational timing impact (late20 spike)** (Confidence: Medium)  
   - Evidence: late20 up sharply for Active users (unexpected segment).

**Recommendation:**
- **Immediate:** investigate and mitigate the **performance regressions** (page load latency/TBT/hitch) before interpreting product tradeoffs.
- **Product:** tighten eligibility (higher precision) and/or offer **lower-friction remediation** (inline address completion rather than blocking) to recover New Cx throughput.
- **Safety:** treat **late20 spike** as a release blocker until root cause is understood.

---

### [LiteGuests](https://ops.doordash.team/decision-systems/experiments/a34f5e72-1fb3-4fb1-aa04-ff2a5506abed?analysisId=6cb900be-d52b-4315-adbb-501541980ce6)
**Feature:** Enables Campaign Manager targeting to show guest banners/promos to web guests (“LiteGuests”).
**Status:** 8. In experiment | **Rollout:** (not set)

**Guardrails (significant negative only):**
- **cx_app_quality_crash_web (explore page):** significant negative (p=0.00047) — **ALERT**
- **cx_app_quality_page_action_error_web:** add payment / create address / delete cart actions — significant negative (p≤0.035) — **ALERT**
- **cx_app_quality_action_load_latency_web (delete cart):** **+177%** (p=0.0108) — **ALERT**

**Analysis:**
Even though business KPIs aren’t flagged significant here, the experiment is causing **core web action instability** in critical guest flows (address creation, payment method, cart deletion) plus higher crash rates. These are highly likely to translate into conversion loss and support contacts if allowed to ramp.

**Likely Causes (ranked):**
1. **Experiment UI/logic interfering with core guest funnel actions** (Confidence: High)  
   - Evidence: errors concentrated on guest-critical actions + crash signal.

**Recommendation:**
- **Pause ramp / hold at current exposure** until engineering confirms no overlap between banner rendering/promo logic and these action endpoints.
- Add logging around guest banner impressions → subsequent action errors to confirm causality.

---

### [Travel v2](https://ops.doordash.team/decision-systems/experiments/4b5d0888-2f28-4e68-9089-fac7bd38271c?analysisId=d1fa0d0d-6741-4d12-92c8-dbca63e3473c)
**Feature:** iOS geofence-triggered airport arrival push notifications (top 12 US airports).
**Status:** 8. In experiment | **Rollout:** (not set)

**Primary Metrics (significant):**
- **consumers_mau:** **-0.12%** (p=1.7e-06) — significant negative  
- **order_rate_per_entity_7d:** **-0.19%** (p=1.3e-05) — significant negative

**Secondary Metrics (significant):**
- **dsmp_same_day_conversion:** **-0.06%** (p=0.0150) — significant negative
- **hqdr_ratio:** **-0.01%** (p=0.0216) — significant negative

**Guardrails (significant negative only):**
- **cx_app_quality_page_load_latency_ios:** **+0.14%** (p=0.0241) — **ALERT**

**Analysis:**
The feature hypothesis is “relevant travel-time nudges increase ordering,” but we’re seeing small, consistent *negative* movement across order/MAU/conversion plus a minor iOS performance regression. While the business metric deltas are tiny, they’re very statistically significant—suggesting **high volume + systematic effect**. The most plausible story is that the geofence/push pipeline is adding background work or foreground latency (confirmed by iOS page load latency regression), and that small UX drag is enough to offset any incremental “airport hunger” lift at scale.

**Likely Causes (ranked):**
1. **iOS performance regression from geofence/push handling** (Confidence: Medium/High)  
   - Evidence: significant iOS page load latency regression + small but consistent funnel softness.
2. **Notification relevance mismatch / annoyance for some travelers** (Confidence: Low/Medium)  
   - Evidence: conversion/MAU down without any countervailing lift signal.

**Recommendation:**
- **Performance-first fix**: profile iOS app start / resume path for geofence-triggered states; verify push handling doesn’t block critical rendering.
- If perf is clean, add tighter targeting (e.g., only opted-in/high intent, time-of-day, recent inactivity) before scaling.

---

### [mWeb onboarding](https://ops.doordash.team/decision-systems/experiments/3905f4a7-174a-407f-aebd-f91a309d0134?analysisId=775207ad-2e6d-4283-8e77-6aee61253ce3)
**Feature:** Post-mWeb signup “get me to the app” flow (app download prompt + SMS fallback).
**Status:** 8. In experiment | **Rollout:** 100%

**Primary Metrics (significant):**
- **webx_order_rate:** **+16.00%** (p≈0) — significant positive  
- **webx_conversion_rate:** **+6.60%** (p≈0) — significant positive  
- **consumers_mau:** **-11.92%** (p≈0) — significant negative  
- **order_rate_per_entity_7d:** **-9.37%** (p≈0) — significant negative  

**Guardrails (significant negative only):**
- **cx_app_quality_inp_web:** **+6.64%** (p=0.0038) — **ALERT**
- **cx_app_quality_page_load_latency_web:** **+4.85%** (p=0.00043) — **ALERT**
- **cx_app_quality_action_load_latency_web:** **+3.57%** (p=0.0063) — **ALERT**

**Analysis:**
This is a **conflicting metric pattern** that strongly suggests a **measurement-population mismatch**: web-exposure metrics (web order rate / web conversion) are up sharply, but actual delivered-consumer MAU and orders-per-entity are down sharply.

A plausible interpretation: the new onboarding flow is **increasing web ordering among those who stay/continue**, but also **reducing the number of users who reach “1+ deliveries”** (MAU definition) because the experience is slower/more fragile (guardrail web perf regressions) and/or because a meaningful share is diverted into app download paths that aren’t being captured as “consumer with delivery” within the same identity window. The secondary metrics reinforce the channel shift story: **in-app conversion/order rates are up ~+80–95%**, while **web-only conversion is down ~-12–13%**.

**Likely Causes (ranked):**
1. **Channel shift from web → in-app ordering, plus identity stitching loss (device_id ↔ consumer_id)** (Confidence: Medium/High)  
   - Evidence: in-app conversion/order rates massively up, web-only rates down, while top-line web exposure metrics rise.
2. **Web performance regressions causing drop-off before first delivery** (Confidence: High)  
   - Evidence: significant INP + page load + action load latency regressions, coincident with large MAU/order-rate declines.

**Recommendation:**
- **Treat web performance regressions as priority-0**; fix INP/page load/action latency before concluding impact.
- Validate measurement: ensure app-download path properly attributes downstream deliveries back to the web-exposed entity (device_id/cx_id linkage). If attribution is broken, current “MAU down” could be partly an instrumentation artifact.
- If attribution is correct, consider **reducing friction in the post-signup prompt** (e.g., defer prompt until after first address entry or first meaningful browse) to protect first-delivery completion.

---