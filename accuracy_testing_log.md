# Accuracy Testing Log — AI Projects

## Invoice/Receipt Extractor — Results

| # | File | Vendor | Date | Total | Items | Accuracy |
|---|------|--------|------|-------|-------|----------|
| 1 | Grocery receipt | N/A (correctly null) ✓ | 06/01/2016 ✓ | $24.20 ✓ | All 12 items ✓ | 100% |
| 2 | Walmart/Happy Mart | HAPPY MART ✓ | 10/07/2020 ✓ | $8.18 ✓ | Both items ✓ | 100% |
| 3 | Template receipt | N/A (correctly null) ✓ | N/A (correctly null) ✓ | $117.00 ✓ | All 7 items ✓ | 100% |
| 4 | Boutique receipt | Boutique ✓ | N/A (correctly null) ✓ | $165.00 ✓ | All 3 items ✓ | 100% |

**Invoice Extractor Accuracy: 100% field-level accuracy on 4-sample test set**
(34/34 fields correctly extracted across vendor, date, total, and 25 individual line items)

---

## Resume Extractor — Results

| # | File | Name | Email | Phone | Skills | Experience | Education | Accuracy |
|---|------|------|-------|-------|--------|------------|-----------|----------|
| 1 | Jason Miller (warehouse) | ✓ | ✓ | ✓ | ✓ (16/16) | ✓ (2/2) | ✓ (3/3) | 100% |
| 2 | Sarah Chen (marketing) | ✓ | ✓ | ✓ | ✓ (6/6) | ✓ (2/2) | ✓ (1/1) | 100% |
| 3 | Ahmed Raza (engineer) | ✓ | ✓ | ✓ | ✓ (5/5) | ✓ (2/2) | ✓ (1/1) | 100% |

**Resume Extractor Accuracy: 100% field-level accuracy on 3-sample test set**
(across 3 different industries: logistics, marketing, and civil engineering)

**Match Scoring — Validated with 2 different job descriptions:**
- Python Developer JD (mismatched role) → Score: 0/100 (correctly identified as no match)
- Warehouse Associate JD (matched role) → Score: 95/100, 88/100 (correctly identified as strong match)

This confirms the match-scoring logic responds accurately to job relevance rather than
returning generic/random scores.

---

## Summary for Portfolio/README
"100% field-level extraction accuracy across 7 test samples (4 invoices, 3 resumes from
different industries), with AI-powered match-scoring validated against multiple job
descriptions to confirm contextual accuracy (not random scoring)."
