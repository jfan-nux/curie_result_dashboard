# Experiment Callout - 2026-01-07

*Generated: 2026-01-07T12:12:22.663060*

---

### App Download Bottom Sheet TTL Test
**Feature:** Shorten app open/download prompt cooldown from 30 to 21 days
**Status:** Ramping | **Rollout:** 

**Primary Metrics:**
- webx_web_new_cx_conversion_rate: -11.15% (p=0.0056) - significant negative
- webx_new_cx_conversion_rate: -10.37% (p=0.0017) - significant negative

**Secondary Metrics:**
- stex_new_rx_conversion: -0.45% (p=0.0413) - significant negative

**Guardrails:**
- core_quality_hqdr: -0.10% (p=0.0027) - ALERT

**Analysis:**
The experiment aimed to increase app downloads by reducing the cooldown period for prompts. However, the conversion rates for new customers have decreased significantly, indicating potential user fatigue or annoyance with more frequent prompts.

**Likely Causes:**
1. Increased prompt frequency may lead to user fatigue, reducing conversion rates - evidenced by the significant drop in new customer conversion rates.
2. The negative impact on HQDR suggests potential quality issues, possibly due to rushed or incomplete orders.

**Recommendation:** Re-evaluate the prompt frequency and consider user feedback to balance engagement without causing fatigue.

---

### Block Bad Address at Checkout
**Feature:** Increase friction for risky addresses during checkout
**Status:** In experiment | **Rollout:** 100%

**Primary Metrics:**
- cx_app_quality_page_load_latency_web: +1.12% (p=0.0078) - significant negative

**Secondary Metrics:**
- cx_app_quality_page_action_error_web: -86.74% (p=0.0322) - significant positive

**Guardrails:**
- None

**Analysis:**
The experiment introduces friction for risky addresses, which has led to an increase in page load latency but a decrease in page action errors, suggesting improved error handling.

**Likely Causes:**
1. Additional checks for risky addresses may slow down page loads - evidenced by increased latency.
2. Improved error handling reduces action errors, indicating better system stability.

**Recommendation:** Optimize the address validation process to reduce latency while maintaining error handling improvements.

---

### LiteGuests
**Feature:** Targeting LiteGuests in Campaign Manager
**Status:** In experiment | **Rollout:** 

**Primary Metrics:**
- webx_in_app_new_cx_conversion_rate: +94.82% (p=0.0000) - significant positive
- webx_in_app_conversion_rate: +89.06% (p=0.0000) - significant positive

**Secondary Metrics:**
- webx_order_rate: +15.99% (p=0.0000) - significant positive

**Guardrails:**
- None

**Analysis:**
The experiment successfully increased conversion rates for LiteGuests, significantly boosting in-app conversions and overall order rates.

**Likely Causes:**
1. Targeted campaigns effectively engage LiteGuests, leading to higher conversion rates - supported by significant increases in conversion metrics.
2. Enhanced user experience for LiteGuests encourages more frequent app usage.

**Recommendation:** Consider expanding the campaign to a broader audience while monitoring for any potential negative impacts on user experience.

---

### Travel v2
**Feature:** Airport use case notifications
**Status:** In experiment | **Rollout:** 

**Primary Metrics:**
- mx_takehome_pay_7d: -0.19% (p=0.0012) - significant negative

**Secondary Metrics:**
- order_rate_per_entity_7d: -0.19% (p=0.0000) - significant negative

**Guardrails:**
- None

**Analysis:**
The experiment aimed to increase engagement through airport notifications but resulted in a slight decrease in takehome pay and order rates.

**Likely Causes:**
1. Notifications may not be effectively driving orders, leading to decreased order rates - evidenced by the negative impact on order metrics.
2. Potential mismatch between notification timing and user needs at airports.

**Recommendation:** Refine notification timing and content to better align with user needs and increase engagement.

---

### mWeb Onboarding
**Feature:** mWeb to mobile app onboarding
**Status:** In experiment | **Rollout:** 100%

**Primary Metrics:**
- webx_in_app_new_cx_conversion_rate: +94.82% (p=0.0000) - significant positive
- webx_in_app_conversion_rate: +89.06% (p=0.0000) - significant positive

**Secondary Metrics:**
- webx_order_rate: +15.99% (p=0.0000) - significant positive

**Guardrails:**
- None

**Analysis:**
The onboarding process from mWeb to the mobile app has significantly increased conversion rates, indicating a successful transition strategy.

**Likely Causes:**
1. Streamlined onboarding encourages app downloads and usage - supported by significant increases in conversion metrics.
2. Enhanced user experience in the app leads to higher engagement and order rates.

**Recommendation:** Continue optimizing the onboarding process and consider applying similar strategies to other user segments.