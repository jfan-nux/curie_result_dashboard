# Experiment Callout - 2026-01-07

*Generated: 2026-01-07T22:22:51.405284*

---

### [App download bottom sheet TTL test](https://ops.doordash.team/decision-systems/experiments/909b3fdb-df4a-4a67-86d3-7a2f4363b3e1?analysisId=8869f3cc-db9b-4054-b0b3-45c64e86c941)
**Feature:** Shortens the cooldown on app open/download prompts (30d → 14d/21d) so mWeb visitors are nudged back into the native app sooner.  
**Status:** 8. Ramping | **Rollout:** (not set)

**Secondary Metrics (significant):**
- webx_web_new_cx_conversion_rate: **-1.11%** (p=0.0056) – significant negative  
- webx_new_cx_conversion_rate: **-1.04%** (p=0.0017) – significant negative  
- stex_new_rx_conversion: **-0.45%** (p=0.0413) – significant negative  
- core_quality_hqdr: **-0.10%** (p=0.0027) – significant negative  

**Analysis:**
This is an early warning that increasing prompt frequency may be adding enough friction/annoyance to reduce new-customer conversion and slightly degrade delivery quality (HQDR). The direction is opposite the hypothesis (move users to app without harming mWeb conversion), and while the impacts are small, they’re consistent across “new” conversion metrics—suggesting a real funnel interruption rather than noise.

**Recommendation:**
Hold ramp until we confirm the mechanism: check whether the prompt is firing more often for true NUX/high-intent sessions (vs. low-intent traffic) and whether dismiss→bounce increased. If it’s a frequency/targeting issue, consider capping prompts for first-time visitors or adding stricter eligibility (e.g., only show after engagement threshold).

---

### [LiteGuests](https://ops.doordash.team/decision-systems/experiments/a34f5e72-1fb3-4fb1-aa04-ff2a5506abedhttps://ops.doordash.team/decision-systems/experiments/a34f5e72-1fb3-4fb1-aa04-ff2a5506abed?analysisId=6cb900be-d52b-4315-adbb-501541980ce6)
**Feature:** Enables Campaign Manager targeting so guest banners can be shown to web guests (LiteGuests).  
**Status:** 8. In experiment | **Rollout:** (not set)

**Guardrails:** (significant negative)
- cx_app_quality_crash_web (cx_explore_page): **crash rate ↑** (p=0.00047) – **ALERT**
- cx_app_quality_page_action_error_web (create_address): **error rate ↑** (p=0.00217) – **ALERT**
- cx_app_quality_page_action_error_web (add_payment_method): **error rate ↑** (p=0.0346) – **ALERT**
- cx_app_quality_action_load_latency_web (delete_cart): **+177%** (p=0.0108) – **ALERT**

**Analysis:**
Even without business-metric wins flagged yet, the web reliability regressions are severe and concentrated in core checkout primitives (address, payment) + general explore crashes. That combination typically translates into downstream conversion losses and support burden, but may not show immediately if ramp is low or traffic mix is changing.

**Recommendation:**
Treat as a launch-blocker: roll back or hotfix before continuing exposure. Triage likely causes around guest-session state handling (missing IDs/session hydration) impacting address/payment flows.

---

### [Travel v2](https://ops.doordash.team/decision-systems/experiments/4b5d0888-2f28-4e68-9089-fac7bd38271c?analysisId=d1fa0d0d-6741-4d12-92c8-dbca63e3473c)
**Feature:** iOS geofence push notifications at top US airports to drive post-arrival ordering.  
**Status:** 8. In experiment | **Rollout:** (not set)

**Primary Metrics (significant):**
- order_rate_per_entity_7d: **-0.19%** (p=1.29e-05) – significant negative  
- consumers_mau: **-0.12%** (p=1.7e-06) – significant negative  

**Secondary Metrics (significant):**
- dsmp_same_day_conversion: **-0.06%** (p=0.0150) – significant negative  
- hqdr_ratio: **-0.01%** (p=0.0216) – significant negative  
- mx_takehome_pay_7d: **-0.19%** (p=0.00117) – significant negative  

**Analysis:**
Despite the intended “timely nudge” hypothesis, we’re seeing a broad (small but highly significant) negative shift in ordering and engagement, plus slight quality/take-rate degradation. This pattern is consistent with *notification fatigue / poor relevance targeting* (users receiving a push when they’re not actually in a “ready to order” moment), or *false-positive geofence hits* causing annoyance without incremental demand.

**Recommendation:**
Before scaling, re-check targeting precision and timing: validate false-positive rate by airport + dwell time, and consider adding a suppression rule (e.g., only send if user has recent browse intent, or within certain local times). If we can’t improve relevance quickly, pause and revisit geofence allocation vs. other push programs.

---

### [mWeb onboarding](https://ops.doordash.team/decision-systems/experiments/3905f4a7-174a-407f-aebd-f91a309d0134?analysisId=775207ad-2e6d-4283-8e77-6aee61253ce3)
**Feature:** Post–mWeb signup “get me to the app” flow (app download prompt; SMS fallback) to increase app adoption and retention.  
**Status:** 8. In experiment | **Rollout:** 100%

**Primary Metrics (significant):**
- webx_order_rate: **+16.00%** (p≈0) – significant positive  
  - *Interpretation: More orders per web visitor overall, consistent with driving higher downstream purchase activity.*
- webx_conversion_rate: **+6.60%** (p≈0) – significant positive  
- consumers_mau: **-11.92%** (p≈0) – significant negative  
- order_rate_per_entity_7d: **-9.37%** (p≈0) – significant negative  

**Guardrails:** (significant negative)
- cx_app_quality_inp_web: **+6.64%** (p=0.00376) – **ALERT**
- cx_app_quality_page_load_latency_web: **+4.85%** (p=0.00043) – **ALERT**
- cx_app_quality_action_load_latency_web: **+3.57%** (p=0.00633) – **ALERT**

**Analysis:**
This experiment is sending *mixed signals* because “WebX” metrics (per web visitor) jump strongly (+conversion, +order rate), while “per exposed entity” and MAU drop sharply. That divergence usually indicates a **denominator/identity shift**: the flow is likely pushing a subset of visitors into in-app ordering (which boosts WebX “web visitor orders”), while simultaneously reducing the number of distinct “consumers with deliveries” counted in this experiment population (e.g., if some users are completing in-app under different identity stitching, or if fewer users make it to a delivery at all but the remaining ones order more).
The huge lift in **in-app conversion/order rate** among web visitors (secondary metrics) supports the “move to app” mechanism, but the reliability regressions (INP/latency) are concerning because they can artificially depress MAU and “active share” by creating friction in the onboarding steps.

**Recommendation:**
Do not interpret this as a clean win yet. Action items:
1) Validate identity stitching: confirm whether “consumers_mau” is undercounting due to web→app transitions (device_id/cx_id linkage) vs. a true drop in delivered consumers.  
2) Triage performance regressions immediately (INP + load latency). If the onboarding sheet or refresh is causing extra work on the explore page, fixing that could recover the MAU/order-rate-per-entity losses while keeping the WebX conversion gains.