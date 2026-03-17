# Nekx SEO – AI Outreach Agent

- [Project Overview](#project-overview)
- [Objectives](#objectives)
- [Key Idea](#key-idea)
- [Legal Considerations](#legal-considerations)
- [Ethical Considerations](#ethical-considerations)
- [Project Scope](#project-scope)
- [Repository Structure](#repository-structure)

## Project Overview

This project explores how artificial intelligence can support outbound marketing for **Nekx SEO**, a Dutch SEO automation platform.

The goal is to design an **AI-powered outreach agent** capable of identifying potential prospects, generating personalized SEO insights, and sending targeted outreach emails.

Traditional outbound marketing often relies on generic cold emails sent to many companies. These messages frequently lack relevance and therefore generate low engagement.

This project investigates whether AI can improve this process by:

- analyzing company websites
- detecting SEO opportunities
- generating short SEO insights
- creating personalized outreach messages

The system is designed as an **experimentation engine** that continuously tests different outreach strategies and learns which combinations perform best.

---

# Objectives

The AI outreach agent should be able to automatically test:

- different **target audiences**
- different **email messages**
- different **email formats**

The goal is to identify which combinations generate the best results and progressively converge toward an optimal outreach strategy.

### Success metrics

The system evaluates performance using:

- Open rate
- Reply rate
- Positive reply rate
- Demo / trial conversions

---

# Key Idea

Instead of sending generic marketing emails, the system provides **immediate value to prospects** by including short SEO insights derived from their website.

Example:

Instead of:

> "We offer SEO services."

The email might say:

> "We noticed your site is missing structured schema markup and your pages load slowly on mobile. This may affect your visibility in Google and AI search results."

This approach aims to increase:

- relevance
- trust
- engagement

---

# Legal Considerations

Since the project operates in the Netherlands and targets European businesses, the outreach system must comply with:

### GDPR

The General Data Protection Regulation governs the processing of personal data within the European Union.

Key principles:

- lawful data processing
- transparency
- data minimization
- user rights (access, deletion)

### Dutch Telecommunications Act

This law regulates electronic marketing communication.

B2B outreach is allowed provided that:

- messages are relevant to the recipient’s business
- the sender is clearly identifiable
- an unsubscribe option is provided

---

# Ethical Considerations

Even when legally permitted, AI-supported marketing raises ethical questions.

Important principles include:

### Transparency

Recipients should not be misled regarding the nature of communication or how insights are generated.

### Avoiding spam-like automation

AI allows large-scale automation, but communication should remain:

- relevant
- targeted
- valuable

### Human oversight

AI should support marketing decisions, not fully replace human judgment.

---

# Project Scope

The objective of this project is **not to build a fully commercial product**, but to:

- design the architecture of an AI outreach system
- explore how it could work in practice
- test the concept through experimentation

---

# Repository Structure

## Quick tool: add a new prospect

Use the CLI helper to insert a lead into the local database:

```bash
python -m backend.tools.add_prospect \
  --company "Acme BV" \
  --contact-email "founder@acme.nl" \
  --website "https://acme.nl" \
  --segment "B2B SaaS"
```

You can also run it without arguments for interactive prompts:

```bash
python -m backend.tools.add_prospect
```

## Quick tool: view full database content

Print all tables and rows:

```bash
python -m backend.tools.view_db
```

Output a SQL-style full dump:

```bash
python -m backend.tools.view_db --dump
```

Output JSON (all tables):

```bash
python -m backend.tools.view_db --json
```
