# Purchase Analytic Budget Monitor

**Version:** 18.0.1.0.0 · **Author:** TwenTIC · **License:** LGPL-3
**Requires:** Odoo Enterprise — `account_budget` module

---

## Overview

This module enriches the Purchase Order workflow with a **real-time analytic budget progress bar**. It reads the active `budget.line` records linked to the analytic distributions of each order line and surfaces three key figures directly on the PO form:

| Field | Description |
|---|---|
| `budget_total` | Sum of the budgeted amounts across all matched budget lines |
| `budget_spent` | Already committed amount (invoiced + confirmed POs) from those budget lines |
| `budget_progress` | Projected consumption % including the current PO's pending amount |
| `is_over_budget` | Boolean flag when the order would push spending above the budget |

A **confirmation wizard** fires automatically when `budget_progress ≥ 90 %`, forcing the buyer to acknowledge the situation before proceeding.

---

## How it fits into the Odoo Purchase circuit

```
Purchase Order (draft / sent)
        │
        │  order_line.analytic_distribution
        │         │
        ▼         ▼
 budget.line  (account_budget)
   ├── budget_amount    ◄── configured by the budget manager
   ├── committed_amount ◄── computed from budget.report
   │         (all confirmed POs + vendor bills for this analytic)
   └── achieved_amount  ◄── only vendor bills (posted)
        │
        ▼
 purchase.order (this module adds)
   ├── budget_total    = Σ budget_amount
   ├── budget_spent    = Σ committed_amount
   ├── budget_progress = (spent + pending_PO) / total × 100
   └── is_over_budget  = pending > available
        │
        │  button_confirm() → budget_progress ≥ 90%?
        │         │
        ▼         ▼
  Normal confirm   PurchaseBudgetWarning wizard
                       → "Confirm Order" (skip_budget_warning=True)
                       → "Cancel" (wizard closes, PO stays in draft)
```

### Key behaviour notes

- **Pre-confirmation projection**: while the PO is still in `draft` or `sent`, the module adds the PO's pending amount on top of `committed_amount` to show the *future* budget impact — not just the current one.
- **Already-confirmed POs**: once the PO reaches `purchase` state, its amount is part of `committed_amount` in `budget.report`. The progress bar reflects the actual committed figure.
- **Multiple analytic accounts**: if several lines carry different analytic distributions, the module aggregates across all matched budget lines. If a line has no matching active budget, it is silently ignored.
- **Minimum invoices guard**: inherited from `account_budget` — budget lines are only matched when the analytic account belongs to a confirmed budget (`state = 'confirmed'`) that covers `date_order`.

---

## Prerequisites — configuring an analytic budget

Before the progress bar appears you need at least one active **Analytic Budget** that covers the purchase date.

### Step 1 — Enable Analytic Accounting

**Accounting → Configuration → Settings → Analytic Accounting** → activate *Analytic Accounting*.

### Step 2 — Create an Analytic Plan and Account

**Accounting → Configuration → Analytic Plans** → create a plan (e.g. *Projects*).

**Accounting → Accounting → Analytic Accounts** → create an account (e.g. *IT Infrastructure 2026*) under that plan.

### Step 3 — Create an Analytic Budget

**Accounting → Accounting → Analytic Budgets** → **New**:

| Field | Value |
|---|---|
| Budget Name | IT Infrastructure 2026 |
| Budget Type | Expense |
| Start Date | 01/01/2026 |
| End Date | 31/12/2026 |
| Status | Confirmed ← **must be Confirmed** |

Add a **Budget Line**:

| Column | Value |
|---|---|
| Analytic Account | IT Infrastructure 2026 |
| Budgeted | 50 000,00 € |

Click **Confirm Budget**.

---

## User guide — step by step

### 1. Create a Purchase Order

**Purchase → Orders → Purchase Orders → New**

Fill in vendor, date, and at least one order line.

### 2. Assign an Analytic Distribution to order lines

In the order line list, enable the optional **Analytic Distribution** column (⚙ icon in the column header) or open any line's detail form.

Assign the distribution to the analytic account linked to your budget (e.g. *IT Infrastructure 2026 — 100 %*).

> The **Analytic Distribution** column is visible only when *Analytic Accounting* is enabled and the user belongs to the *Analytic Accounting* group.

### 3. Read the budget progress bar

After assigning the analytic distribution, a bordered section labelled **Analytic Budget** appears between the order lines and the totals area.

```
┌─────────────────────────────────────────────────────┐
│  📊 Analytic Budget                                  │
│  ████████████████░░░░░░░░░░  67.4 %                 │
│  Committed: 33 700,00 €          Total Budget: 50 000,00 € │
└─────────────────────────────────────────────────────┘
```

**Badge colours:**

| Badge | Condition | Meaning |
|---|---|---|
| *(none)* | `budget_progress < 90 %` | Budget comfortable |
| 🟠 **Budget Limit Approaching** | `90 % ≤ progress < 100 %` | Review before confirming |
| 🔴 **Over Budget** | `progress ≥ 100 %` | Would exceed budget |

The bar recalculates instantly whenever you change a quantity, unit price, or analytic distribution on any line.

### 4. Confirm the order — normal flow (< 90 %)

Click **Confirm Order**. The order moves to `Purchase Order` state as usual.

### 5. Confirm the order — budget warning flow (≥ 90 %)

When `budget_progress ≥ 90 %`, clicking **Confirm Order** opens a pop-up wizard:

```
┌─────────────────────────────────────────────────────┐
│  ⚠  Budget Warning                                   │
│                                                      │
│  The analytic budget for this purchase order will    │
│  reach 94.2% after confirmation.                     │
│  Do you want to continue?                            │
│                                                      │
│  Purchase Order: PO/2026/0042                        │
│  Projected Budget Usage (%): 94.20                   │
│                                                      │
│  [Confirm Order]   [Cancel]                          │
└─────────────────────────────────────────────────────┘
```

- **Confirm Order** → confirms the PO (the warning will not appear again for this order once confirmed).
- **Cancel** → closes the wizard; the PO remains in draft for revision.

### 6. After confirmation

The progress bar continues to display on confirmed orders, now reflecting the *actual* committed amount from `budget.report` (which includes this order).

---

## Dependencies

| Module | Why |
|---|---|
| `purchase` | `purchase.order` and `purchase.order.line` models |
| `account_budget` *(Enterprise)* | `budget.line`, `budget.analytic`, `budget_line_ids` on PO line |

---

## Translations

Ships with `.po` files for: **es** · **ca** · **de** · **fr** · **pt** · **it**
