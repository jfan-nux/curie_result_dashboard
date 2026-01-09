# Experiment Callout - 2026-01-07

*Generated: 2026-01-07T18:37:51.752332*

---

### App Download Bottom Sheet TTL Test
**Feature:** Shorten app open/download prompt cooldown from 30 to 21 days
**Status:** Ramping | **Rollout:** N/A

**Primary Metrics:**
- No significant primary metrics reported.

**Secondary Metrics:**
- Web New Cx Conversion Rate: -1.11% (p=0.0056) - significant negative
- New Cx Conversion Rate: -1.04% (p=0.0017) - significant negative
- Core Quality HQDR: -0.10% (p=0.0027) - significant negative

**Guardrails:**
- None reported.

**Analysis:**
The decrease in conversion rates suggests that the shortened cooldown period may not be effectively encouraging new customer conversions. The negative movement in HQDR indicates a potential decline in delivery quality.

**Recommendation:** Investigate the user experience during the shortened cooldown period to identify friction points. Consider A/B testing different messaging or incentives to improve conversion rates.

---

### Block Bad Address at Checkout
**Feature:** Increase friction before checkout for risky addresses
**Status:** In experiment | **Rollout:** 100%

**Primary Metrics:**
- DashPass Signup: +4.99% (p=0.0033) - significant positive
- Consumers MAU: -0.90% (p=0.0316) - significant negative

**Secondary Metrics:**
- NV FCO All: -15.35% (p=0.0272) - significant positive
- HQDR Ratio: +0.70% (p=0.0019) - significant positive

**Guardrails:**
- Core Quality Late20: +1.53% (p=0.0162) - ALERT

**Analysis:**
The increase in DashPass signups is promising, but the decline in MAU suggests potential user dissatisfaction. The improvement in HQDR indicates better delivery quality, but the increase in late deliveries is concerning.

**Recommendation:** Focus on addressing the causes of late deliveries while maintaining the improvements in delivery quality. Consider additional user feedback to understand the drop in MAU.

---

### LiteGuests
**Feature:** Targeting LiteGuests in Campaign Manager
**Status:** In experiment | **Rollout:** N/A

**Primary Metrics:**
- No significant primary metrics reported.

**Secondary Metrics:**
- None reported.

**Guardrails:**
- Page Action Error Web: +0.17% (p=0.0346) - ALERT

**Recommendation:** Investigate the source of page action errors to ensure a smooth user experience for LiteGuests. Consider technical audits or user testing to identify and resolve issues.

---

### Travel v2
**Feature:** Top Airports Notification
**Status:** In experiment | **Rollout:** N/A

**Primary Metrics:**
- Order Rate per Entity 7d: -0.19% (p=0.00001) - significant negative
- Consumers MAU: -0.12% (p=0.0000017) - significant negative

**Secondary Metrics:**
- MX Takehome Pay 7d: -0.19% (p=0.0012) - significant negative

**Guardrails:**
- Page Load Latency iOS: +0.13% (p=0.0241) - ALERT

**Analysis:**
The negative impact on order rates and MAU suggests that the airport notifications may not be effectively driving engagement. The increase in page load latency on iOS could be affecting user experience.

**Recommendation:** Re-evaluate the notification strategy to ensure relevance and timing. Address the iOS latency issues to improve user experience.

---

### mWeb Onboarding
**Feature:** mWeb to mobile app onboarding
**Status:** In experiment | **Rollout:** 100%

**Primary Metrics:**
- Webx Order Rate: +15.99% (p=0.0000) - significant positive
- Consumers MAU: -11.92% (p=0.0000) - significant negative

**Secondary Metrics:**
- Webx In-App New Cx Conversion Rate: +94.82% (p=0.0000) - significant positive

**Guardrails:**
- Page Load Latency Web: +4.85% (p=0.0004) - ALERT

**Analysis:**
The increase in order rate and in-app conversion is promising, but the decline in MAU and increase in page load latency suggest potential user experience issues.

**Recommendation:** Focus on optimizing the onboarding flow to reduce latency and improve user retention. Consider additional user feedback to understand the drop in MAU.