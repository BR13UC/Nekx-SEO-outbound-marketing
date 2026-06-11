# Nekx SEO Simulation Data

Simulation data - not live campaign results.

- Database backup: `/home/brieuc/AIAndYourProfession/Nekx-SEO-outbound-marketing/data/nekx.db.bak-simulation-20260611T154447Z`
- Sent mailbox: `k.harleen15@yahoo.fr`
- Sender mailbox: `onboarding@resend.dev`
- Total simulated leads/emails: 64
- Delivery status: Real Resend provider IDs were recorded for all 64 campaign messages.
- Opens to perform for Resend evidence: 35
- Replies to perform for report evidence: 9
- Positive replies: 4
- Demo interest replies: 1

## A/B Matrix

| Segment | Variant A | Variant B | Expected winner |
| --- | --- | --- | --- |
| Multi-Location Businesses | Time Savings | Scalability | B - Scalability |
| Premium / Fine Dining | Loss Framing | Growth Framing | A - Loss Framing |
| Independent Local Businesses | Convenience | Expertise | A - Convenience |

## Results

| Segment | Variant | Sent | Opened | Replies | Positive | Demo interest |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Multi-Location Businesses | A - Time Savings | 11 | 5 | 1 | 0 | 0 |
| Multi-Location Businesses | B - Scalability | 11 | 7 | 2 | 1 | 0 |
| Premium / Fine Dining | A - Loss Framing | 10 | 7 | 2 | 1 | 1 |
| Premium / Fine Dining | B - Growth Framing | 11 | 5 | 1 | 0 | 0 |
| Independent Local Businesses | A - Convenience | 10 | 6 | 2 | 1 | 0 |
| Independent Local Businesses | B - Expertise | 11 | 5 | 1 | 1 | 0 |

## Checklist

Use `data/simulation_open_reply_checklist.csv` to decide which messages to open and reply to in the safe inbox. Messages are identifiable by the `[NEKX-SIM-###]` subject prefix.

## Sample Emails

### NEKX-SIM-001 - Restaurant Niemeijer

Subject: [NEKX-SIM-001] Time Savings idea for Restaurant Niemeijer

```text
Simulation data - not live campaign results.
Safe inbox test for Restaurant Niemeijer; this was not sent to the prospect.

Hi Restaurant Niemeijer,

I looked at your market context around https://www.restaurantniemeijer.nl/ and put together a few opportunities based on comparable client cases:
- Simulation opportunity: missing meta description.
- Simulation opportunity: no Google Business Profile mention.

If useful, I can share a short walkthrough with practical next steps and expected impact ranges.

Best,
Nekx SEO

Unsubscribe: reply with "unsubscribe" and I will not contact you again.
```

### NEKX-SIM-002 - Restaurant Bisque

Subject: [NEKX-SIM-002] Time Savings idea for Restaurant Bisque

```text
Simulation data - not live campaign results.
Safe inbox test for Restaurant Bisque; this was not sent to the prospect.

Hi Restaurant Bisque,

I looked at your market context around https://www.restaurantbisque.nl/ and put together a few opportunities based on comparable client cases:
- Simulation opportunity: weak title tag.
- Simulation opportunity: missing structured data.

If useful, I can share a short walkthrough with practical next steps and expected impact ranges.

Best,
Nekx SEO

Unsubscribe: reply with "unsubscribe" and I will not contact you again.
```

### NEKX-SIM-003 - Paviljoen Sterrebos

Subject: [NEKX-SIM-003] Time Savings idea for Paviljoen Sterrebos

```text
Simulation data - not live campaign results.
Safe inbox test for Paviljoen Sterrebos; this was not sent to the prospect.

Hi Paviljoen Sterrebos,

I looked at your market context around https://www.paviljoensterrebos.nl/ and put together a few opportunities based on comparable client cases:
- Simulation opportunity: no local keywords on homepage.
- Simulation opportunity: slow mobile page.

If useful, I can share a short walkthrough with practical next steps and expected impact ranges.

Best,
Nekx SEO

Unsubscribe: reply with "unsubscribe" and I will not contact you again.
```

## Interpretation

This simulation proves that the workflow can process leads, generate email variants, send safe test messages through Resend, store provider IDs, and compare A/B performance across the three agreed segments. It does not prove real-world campaign performance because all engagement outcomes are simulated.
