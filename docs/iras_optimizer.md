# ⚖️ IRAS Tax & Wealth — Personal Tax Relief Optimizer

MerlionOS includes an interactive **CPF Special Account (RSTU) vs. SRS Top-up Optimizer** that helps you maximise tax savings within a given top-up budget, using Singapore's progressive resident tax brackets (YA 2024–2026).

## What it does
- **Progressive tax tiers** — a live table showing the effective and marginal rates applied to your reference income (assessable income minus pre-existing reliefs), recomputed dynamically from the shared bracket constant.
- **CPF SA (RSTU) top-up** — editable cap (default S$8,000 for citizens/PRs).
- **SRS top-up** — editable cap (default S$15,300 citizen/PR, S$35,700 foreigner; auto-switched by residency status).
- **Itemised pre-existing reliefs** — the reliefs you already claim (CPF employee, life insurance, WMCR, qualifying child, and more) auto-sum toward the S$80,000 cap. These are *inputs*, not top-up levers — the optimizer only allocates your budget between CPF SA and SRS. Life insurance relief is itself capped at S$5,000 minus your CPF employee contribution.
- **Dollar-saved calculator** — shows the tax saved by the recommended allocation, plus asset-liquidity trade-off advisories (CPF/SRS are locked longer than cash).

## The S$80,000 total relief cap
Singapore caps **total tax reliefs at S$80,000** (YA2018+). The optimizer:
1. Sums your **itemised pre-existing reliefs** (auto-summed from individual IRAS categories: CPF employee, WMCR, qualifying child, parent/handicapped sibling, NSman, life insurance, CPF cash top-up, SRS, earned income, other).
2. Adds your planned CPF SA + SRS top-ups (the only two levers the optimizer allocates).
3. Caps the combined amount at S$80,000 and flags if you're **capped out**, showing the effective deduction used.

> **Note on donations:** charitable **donations** (e.g. the S$1,050 in a typical YA2026 notice) are a separate *deduction*, not a relief, and are not modelled in the relief cap pool. The optimizer's reference income therefore uses income − reliefs only.

## Form layout
The optimizer form is ordered for clarity:
1. **Your Profile** — Residency Status → Annual Assessable Income → Top-up Budget → **Donations**
2. **Relief Caps** — Max CPF SA and Max SRS (in their own section, outside the profile grid)
3. **Pre-existing Reliefs** — itemised inputs (CPF employee, life insurance, WMCR, qualifying child, NSman, CPF cash top-up, SRS, earned income, etc.) that auto-sum into the S$80k cap

> **Donations are a separate deduction**, not a relief. They reduce your chargeable income (and thus tax) but do **not** consume the S$80k relief-cap headroom. Enter any charitable donations in the Profile section.
