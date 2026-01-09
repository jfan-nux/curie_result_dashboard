# Experiment Callout - 2026-01-07

*Generated: 2026-01-07T22:15:19.044785*

---

### [App Download Bottom Sheet TTL Test](https://ops.doordash.team/decision-systems/experiments/909b3fdb-df4a-4a67-86d3-7a2f4363b3e1?analysisId=8869f3cc-db9b-4054-b0b3-45c64e86c941)
**Feature:** This experiment shortens the cooldown period for app open/download prompts from 30 days to 21 days, aiming to increase app usage and retention by nudging users more frequently.
**Status:** Ramping | **Rollout:** Not specified

**Secondary Metrics:**
- webx_web_new_cx_conversion_rate: -1.11% (p=0.0056) - significant negative
  - *Interpretation: The reduction in cooldown period seems to have negatively impacted the conversion rate of new customers on the web, possibly due to increased frequency leading to prompt fatigue.*

**Analysis:**
The hypothesis was that reducing the cooldown period would increase app engagement by reminding users more frequently. However, the significant negative impact on the web conversion rate suggests that users might be experiencing prompt fatigue, leading to a decrease in conversion. This could be particularly true for users who are not ready to engage with the app as frequently as prompted.

**Likely Causes (ranked by evidence):**
1. **Prompt Fatigue** (Confidence: High)
   - Evidence: Significant negative impact on web conversion rates.
   - Counter-evidence: None observed.

**Recommendation:**
- Investigate user feedback on prompt frequency to understand the threshold for prompt fatigue.
- Consider segmenting users based on engagement levels to tailor the frequency of prompts.

---

### [Block Bad Address at Checkout](https://ops.doordash.team/decision-systems/experiments/43e5e1fc-e857-4278-8f4d-5b46be452692?analysisId=944d4986-d1a7-4471-8279-0cbf8edca5e9)
**Feature:** This feature increases friction at checkout for new users with potentially risky addresses to reduce non-delivery incidents.
**Status:** In experiment | **Rollout:** 100%

**Primary Metrics:**
- dashpass_signup: +4.99% (p=0.0033) - significant positive
  - *Interpretation: The feature seems to encourage users to sign up for DashPass, possibly due to increased trust in delivery reliability.*

**Guardrails:**
- core_quality_late20: +1.53% (p=0.0162) - ALERT
  - *Risk: An increase in late deliveries suggests that while the feature may reduce non-delivery, it could be causing delays in delivery times.*

**Analysis:**
The feature aims to improve delivery reliability by ensuring accurate address information. The positive impact on DashPass signups indicates increased user trust. However, the increase in late deliveries is concerning and suggests a tradeoff between reducing non-delivery and maintaining timely deliveries.

**Likely Causes (ranked by evidence):**
1. **Increased Delivery Time Due to Address Verification** (Confidence: High)
   - Evidence: Significant increase in late deliveries.
   - Counter-evidence: None observed.

**Recommendation:**
- Investigate the address verification process to identify bottlenecks causing delays.
- Consider balancing the verification process to maintain delivery timeliness while ensuring address accuracy.

---

### [LiteGuests](https://ops.doordash.team/decision-systems/experiments/a34f5e72-1fb3-4fb1-aa04-ff2a5506abed?analysisId=6cb900be-d52b-4315-adbb-501541980ce6)
**Feature:** This experiment targets LiteGuests in Campaign Manager to show guest banners to web guests.
**Status:** In experiment | **Rollout:** Not specified

**Guardrails:**
- cx_app_quality_page_action_error_web: significant negative
  - *Risk: Increased errors in web page actions could degrade user experience, potentially affecting conversion rates.*

**Analysis:**
The experiment aims to enhance engagement with LiteGuests by displaying targeted banners. However, the increase in web page action errors suggests potential issues with the implementation, which could negatively impact user experience and conversion.

**Likely Causes (ranked by evidence):**
1. **Implementation Errors** (Confidence: Medium)
   - Evidence: Significant increase in web page action errors.
   - Counter-evidence: None observed.

**Recommendation:**
- Conduct a thorough review of the implementation to identify and resolve errors.
- Monitor user feedback to assess the impact on user experience and conversion.

---

### [Travel v2](https://ops.doordash.team/decision-systems/experiments/4b5d0888-2f28-4e68-9089-fac7bd38271c?analysisId=d1fa0d0d-6741-4d12-92c8-dbca63e3473c)
**Feature:** This feature uses geofencing to send notifications to users arriving at major airports, aiming to increase order rates by providing timely nudges.
**Status:** In experiment | **Rollout:** Not specified

**Primary Metrics:**
- order_rate_per_entity_7d: -0.19% (p=0.00001) - significant negative
  - *Interpretation: The geofencing notifications have not led to an increase in order rates as expected, possibly due to timing or relevance issues.*

**Analysis:**
The hypothesis was that timely notifications upon arrival at airports would increase order rates. However, the significant negative impact suggests that the notifications may not be as effective as anticipated, possibly due to timing, relevance, or user context.

**Likely Causes (ranked by evidence):**
1. **Timing and Relevance Issues** (Confidence: Medium)
   - Evidence: Significant negative impact on order rates.
   - Counter-evidence: None observed.

**Recommendation:**
- Review the timing and content of notifications to ensure they are relevant and timely.
- Consider user feedback to refine the notification strategy.

---

### [mWeb Onboarding](https://ops.doordash.team/decision-systems/experiments/3905f4a7-174a-407f-aebd-f91a309d0134?analysisId=775207ad-2e6d-4283-8e77-6aee61253ce3)
**Feature:** This experiment enhances the onboarding experience for new users on mobile web by prompting app downloads and SMS opt-ins.
**Status:** In experiment | **Rollout:** 100%

**Primary Metrics:**
- webx_order_rate: +15.99% (p=0.0000) - significant positive
  - *Interpretation: The enhanced onboarding experience has significantly increased order rates, indicating improved user engagement and conversion.*

**Analysis:**
The feature aims to improve the onboarding experience by encouraging app downloads and SMS opt-ins. The significant positive impact on order rates suggests that the strategy is effective in increasing user engagement and conversion.

**Likely Causes (ranked by evidence):**
1. **Improved Onboarding Experience** (Confidence: High)
   - Evidence: Significant positive impact on order rates.
   - Counter-evidence: None observed.

**Recommendation:**
- Consider scaling the enhanced onboarding experience to other segments.
- Monitor long-term retention and engagement to ensure sustained impact.