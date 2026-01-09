# Experiment Callout - 2026-01-07

*Generated: 2026-01-07T22:24:42.209044*

---

### [App download bottom sheet TTL test](https://ops.doordash.team/decision-systems/experiments/909b3fdb-df4a-4a67-86d3-7a2f4363b3e1?analysisId=8869f3cc-db9b-4054-b0b3-45c64e86c941)
**Feature:** Shortens the “open/download the app” prompt cooldown on mWeb (30d → 21d / 14d) to nudge more people into native app.
**Status:** 8. Ramping | **Rollout:** N/A  
**Arms:** twoweek, twentyone

#### Arm Comparison

| Metric | twoweek | twentyone | Winner |
|---|---:|---:|---|
| webx_new_cx_conversion_rate (secondary) | **-1.04%** (p=0.0017) | -0.28% (p=0.4000) | **twentyone** |
| webx_web_new_cx_conversion_rate (secondary) | **-1.11%** (p=0.0056) | -0.20% (p=0.6177) | **twentyone** |
| core_quality_hqdr (secondary) | **-0.10%** (p=0.0027) | -0.06% (p=0.0960) | **twentyone** |

#### By Arm Analysis

**twoweek:**
- Primary: none significant
- Secondary (negatives): webx_new_cx_conversion_rate **-1.04%** (p=0.0017), webx_web_new_cx_conversion_rate **-1.11%** (p=0.0056), stex_new_rx_conversion **-0.45%** (p=0.0413), core_quality_hqdr **-0.10%** (p=0.0027)
- Summary: Shortening too aggressively looks like it’s creating *incremental friction/fatigue*—we’re not seeing the intended app lift in the topline metrics here, but we *are* seeing measurable conversion softness (esp. new cx) plus a small quality degradation.

**twentyone:**
- Primary: none significant
- Secondary: none significant (directions mostly flat; small directional HQDR softness)
- Summary: Much “safer” behavior—no clear win yet, but avoids the statistically significant new-cx and quality downsides seen in **twoweek**.

**🏆 Winning Arm: twentyone**
- Rationale: twoweek introduces multiple significant negatives without offsetting primary wins; twentyone is neutral/less risky so far.
- Confidence: **Medium** (primary metrics still flat; we’re choosing the arm that minimizes harm).

**Recommendation:** Keep ramping **twentyone** and pause/limit **twoweek**. If the goal is native migration, add instrumentation/readouts for *app open/deeplink success* to confirm the mechanism is firing; right now the only clear signal is “more prompting hurts new-cx conversion.”

---

### [Block bad address at checkout](https://ops.doordash.team/decision-systems/experiments/43e5e1fc-e857-4278-8f4d-5b46be452692?analysisId=944d4986-d1a7-4471-8279-0cbf8edca5e9)
**Feature:** Adds friction for new users with risky/incomplete addresses before checkout to reduce ND and improve delivery quality/retention.
**Status:** 8. In experiment | **Rollout:** 100%  
**Arms:** treatment_cart, treatment_address

#### Arm Comparison

| Metric | treatment_cart | treatment_address | Winner |
|---|---:|---:|---|
| dashpass_signup (primary) | **+4.99%** (p=0.0033) | +1.46% (p=0.3871) | **treatment_cart** |
| consumers_mau (primary) | **-0.90%** (p=0.0316) | -1.00% (p=0.0481)\* | **treatment_cart** (slightly) |
| order_rate_per_entity_7d (New Cx) (primary) | **-21.63%** (p=0.0223) | n/a | **treatment_address** |

\*shown on cx_lifestage_NULL cut for treatment_address; overall is directional negative but not significant.

#### Guardrails (significant negatives only)
- **treatment_cart:** cx_app_quality_page_load_latency_web **+111.8%** (p=0.0078) – **ALERT**  
  - *Risk:* Material web perf regression (more page loads over SLO). Also multiple TBT/hitch regressions and late20 up for Active.
- **treatment_address:** core_quality_late20 (Active) **+153.6%** (p=0.0162) – **ALERT**  
  - *Risk:* Big increase in very-late deliveries for Active users—could outweigh any ND benefit if it’s real and persistent.

#### By Arm Analysis

**treatment_cart:**
- Primary: dashpass_signup **+4.99%** (p=0.0033); consumers_mau **-0.90%** (p=0.0316); New Cx order rate **-21.63%** (p=0.0223)
- Guardrails: **major web perf regression** + lateness up for Active
- Summary: This looks like a classic “added checkout friction” tradeoff: pushing some users into DP signup (possibly by increasing perceived value / deal-sensitivity at checkout), but *meaningfully suppressing new customer ordering* and introducing serious performance + lateness risk.

**treatment_address:**
- Primary: consumers_mau (cx_lifestage_NULL) **-1.00%** (p=0.0481)
- Secondary: nv_fco_all **-15.35%** (p=0.0272) (good: lower NV fulfillment cost)
- Guardrails: late20 (Active) **+153.6%** (p=0.0162)
- Summary: Less upside than treatment_cart, but also avoids the huge New Cx order-rate hit (not flagged). However, the lateness guardrail is severe and needs immediate validation.

**🏆 Winning Arm: treatment_address**
- Rationale: treatment_cart’s -21.6% New Cx order rate + broad performance regressions is too costly. treatment_address still has a lateness guardrail, but overall appears less damaging to growth.
- Confidence: **Low/Medium** (because late20 guardrail is extremely large; need to confirm it’s not a data/seasonality artifact).

**Recommendation:** Do **not** expand treatment_cart. For treatment_address, immediately investigate late20 spike (check ETA-service changes, batching/assignment side effects, or segment leakage into Active). If late20 holds, neither arm is shippable without mitigation (e.g., limit to true NUX only / exclude Active, or soften the blocking UX).

---

### [mWeb onboarding](https://ops.doordash.team/decision-systems/experiments/3905f4a7-174a-407f-aebd-f91a309d0134?analysisId=775207ad-2e6d-4283-8e77-6aee61253ce3)
**Feature:** After mWeb signup, prompts users to download the app (or SMS opt-in fallback) to shift onboarding into native app.
**Status:** 8. In experiment | **Rollout:** 100%

**Primary Metrics:**
- webx_order_rate: **+16.00%** (p≈0) – significant positive  
  - *Interpretation:* More orders per web visitor—this suggests the flow is successfully converting browsing/intent into checkouts somewhere in the ecosystem (web or in-app).
- consumers_mau: **-11.92%** (p≈0) – significant negative  
  - *Interpretation:* Fewer distinct purchasers despite higher order rate per visitor; implies concentration into fewer buyers or measurement population mismatch (e.g., repeat purchasers ordering more, while marginal users drop).
- order_rate_per_entity_7d: **-9.37%** (p≈0) – significant negative  
  - *Interpretation:* On a per-entity basis, ordering intensity is down—consistent with added friction causing more users to churn before first purchase.

**Guardrails:** (significant negative)
- cx_app_quality_inp_web: **+6.64%** (p=0.0038) – ALERT  
- cx_app_quality_page_load_latency_web: **+4.85%** (p=0.0004) – ALERT  
- cx_app_quality_action_load_latency_web: **+3.57%** (p=0.0063) – ALERT  
  - *Risk:* The onboarding experience is likely adding client-side work/extra steps that degrade web responsiveness; that can directly drive the MAU/order-rate-per-entity downsides.

**Analysis:**
The pattern is internally inconsistent unless the treatment is (a) pushing a subset of high-intent users to complete purchase more often (driving webx_order_rate and conversion up), while (b) increasing friction/perf costs that cause many marginal/new users to abandon (driving MAU and per-entity order rates down). The very large “shift” metrics (e.g., web conversion down while in-app conversion up) strongly indicate a **channel mix shift**: we’re moving conversion from web → app, but at a cost of losing breadth of purchasers and hurting web performance.

**Recommendation:**
Before calling this a win, gate on fixing the **web perf regressions** and re-evaluate “success” using ecosystem-wide purchaser counting that aligns with the experiment’s objective (app migration). If the goal is app adoption, report out explicitly: (1) incremental app orders vs cannibalized web orders, and (2) net new purchasers (not just orders). If MAU remains deeply negative after perf fixes, consider softening the post-signup prompt (delay it, reduce blocking, or target only high-likelihood-to-install cohorts).