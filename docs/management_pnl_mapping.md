# Management P&L: Group, Account, and Formula Reference

**Applies to:** `THUKHA SAYTANAR CO. Ltd (Victoria Hospital)`  
**Reports:** Management Profit and Loss Summary and Management Profit and Loss Notes  
**Source of truth:** the account mapping in `models/profit_and_loss_report.py`

## 1. How a balance enters either report

1. The report reads posted accounting move-line balances for the selected company, dates, journals, analytic filters, and posted/draft setting.
2. Only Profit & Loss account types are considered: Income, Other Income, Expense, Depreciation Expense, and Direct Cost Expense.
3. An account is included only when its **account code** is in the mapping below. Any unmapped P&L account is excluded.
4. Revenue account balances are multiplied by **-1**, so revenue displays as a positive amount. Expense account balances keep their normal **+1** sign.
5. The source balance is `Debit - Credit`, converted through Odoo's report currency table when required.

> The Notes report can be expanded to show the live account code and name below each group. The Summary report shows only group and total lines.

## 2. Account mapping

| No. | Group in report | Sign | Included account codes |
|---:|---|:---:|---|
| 1 | Inpatients | Revenue (-1) | 500095, 500100, 500150, 500115, 500135 |
| 2 | Outpatients | Revenue (-1) | 500020, 500030, 500060, 500125, 500130, 500085, 500145, 500070, 500190, 500010, 500015, 500025, 500065, 500035, 500040, 500075, 500080, 500090, 500105, 500110, 500120, 500140, 500155, 500186, 500160, 500165, 500170, 500175, 500180, 500187 |
| 3 | Other (EOPD, Day care) | Revenue (-1) | 500050, 500055, 500146, 500045 |
| 4 | Direct Cost | Expense (+1) | 600010, 600020, 600030, 600035, 600040, 600045, 600180 |
| 5 | Other Hospital Revenue | Revenue (-1) | 510030, 510015, 510000, 510010, 510035, 510020, 510025, 500185, 500400, 500405, 500410, 500415, 500420, 500425, 500600, 510100, 510105, 510110, 510115, 510120 |
| 6 | Non-Hospital Revenue | Revenue (-1) | 510500, 510510, 510515, 510520, 510530, 510535, 510540, 510575, 510565, 510545, 510555, 510505, 510560, 510570, 510580 |
| 7 | Complex Building & BIS | Revenue (-1) | 510085, 510095, 510125, 510130 |
| 8 | Cost of Goods Sold | Expense (+1) | 600050, 600060, 600070, 600080, 600090, 600100, 600110, 600120, 600130, 600140, 600150, 600170, 600160, 600190, 600200, 600210, 600220, 600181, 600182, 600183, 600184, 600185, 600186 |
| 9 | Operating Cost | Expense (+1) | 700010, 700020, 700030, 700040, 700050, 700060, 700080, 700090, 700100, 700110, 700120, 700130, 700140, 700170, 700190, 700070, 700150, 700160, 700200, 700210, 700220, 702311, 701150, 701160, 701173, 701175, 702315, 703085, 704055 |
| 10 | Staff Cost (Based on Head Count) | Expense (+1) | 701010, 701030, 701040, 701050, 701060, 701070, 701080, 701090, 701100, 701110, 701120, 701130, 701140, 701170, 701171, 701172 |
| 11 | Bonus | Expense (+1) | 701020 |
| 12 | Administrative & Other Expenses | Expense (+1) | 702010, 702020, 702030, 702040, 702050, 702060, 702070, 702080, 702090, 702100, 702110, 702120, 702130, 702140, 702150, 702160, 702170, 702180, 702190, 702200, 702210, 702220, 702230, 702240, 702250, 702280, 702290, 702300, 702310 |
| 13 | Repair & Maintenance | Expense (+1) | 703010, 703020, 703030, 703040, 703050, 703070, 703080, 703060 |
| 14 | Sales & Marketing | Expense (+1) | 704020, 704030, 704040, 704050 |
| 14.1 | Commission Expense | Expense (+1) | 704010 |
| — | Taxes *(Notes only; see below)* | Expense (+1) | 707020, 707030, 700180 |
| 15 | Depreciation & Amortization | Expense (+1) | 705010, 705020, 705030, 705040, 705050, 705060, 705070, 705080, 705090, 705100, 705110, 705120, 705130, 705140, 705150, 705160, 705170, 705180, 705111 |
| — | Interest Income *(Notes only; part of Summary financial net)* | Revenue (-1) | 500750 |
| 16 | Finance Expenses *(Notes); Financial Expense & Income (Summary)* | Expense (+1) | 706010, 706020, 706030, 706040, 706050, 706060, 706070, 706080, 702260, 702270 |
| 17 | Income Tax | Expense (+1) | 707010 |

### Current THA account-name examples

The P&L Notes unfolding is the full live name list. Important recently clarified mappings are:

| Code | Live THA account name | Group |
|---:|---|---|
| 704010 | Commission Expenses | Commission Expense |
| 702260 | Foreign exchange losses | Finance Expenses |
| 702270 | Bank charges | Finance Expenses |
| 707010 | Income Tax Expenses | Income Tax |
| 707020 | Property Tax | Taxes |
| 707030 | Capital Gain Tax | Taxes |
| 700180 | Commercial Tax Expense | Taxes |

## 3. Management Profit and Loss Summary

### Lines and formulas

| Summary line | Formula |
|---|---|
| Total Revenue | `Inpatients + Outpatients + Other (EOPD, Day care)` |
| Net Revenues | `Total Revenue - Direct Cost` |
| Other Revenue | `Other Hospital Revenue + Non-Hospital Revenue + Complex Building & BIS` |
| Total Net Revenues | `Total Revenue + Other Revenue - Direct Cost` |
| Administrative & Other Expenses | `Administrative accounts + Taxes accounts` |
| Total Expenses | `Cost of Goods Sold + Operating Cost + Staff Cost + Bonus + Administrative & Other Expenses + Repair & Maintenance + Sales & Marketing + Commission Expense` |
| EBITDA | `Total Net Revenues - Total Expenses` |
| EBIT | `EBITDA - Depreciation & Amortization` |
| Financial Expense & Income | `Interest Income - Finance Expenses` |
| Earnings Before Tax | `EBIT + Financial Expense & Income` |
| Earnings After Tax | `Earnings Before Tax - Income Tax` |

### Period columns

| Column | Calculation |
|---|---|
| Actual (MTD) | Selected month's group balance |
| Actual (YTD) | Sum of each month from fiscal-year start through the selected month |
| Budget (MTD) | Selected budget's amount for the selected month and mapped accounts |
| Budget (YTD) | Selected budget's amount from fiscal-year start through the selected month |
| Variance (MTD/YTD) | `Actual - Budget` |
| Monthly Actual | Each actual month shown by the report filter |
| Monthly Budget | Budget months from fiscal-year start through the selected month only |

### Summary percentage base

`% = line amount / base amount × 100`.

| Lines | Percentage base |
|---|---|
| Inpatients, Outpatients, Other (EOPD, Day care), Total Revenue | Total Revenue |
| Direct Cost, Other Hospital Revenue, Non-Hospital Revenue, Complex Building & BIS, Net Revenues, Other Revenue | Net Revenues |
| All remaining lines and totals | Total Net Revenues |

For the Summary variance column, `Variance % = (Actual - Budget) / Budget × 100`. A percentage is blank when its denominator is zero.

## 4. Management Profit and Loss Notes

### Lines and formulas

The Notes report shows the same mapped groups and can unfold each group to its individual account codes and account names. Its total structure differs slightly from the Summary:

| Notes line | Formula |
|---|---|
| Total Revenue | `Inpatients + Outpatients + Other (EOPD, Day care)` |
| Net Revenues | `Total Revenue - Direct Cost` |
| Net Operating Revenue | `Total Revenue + Other Hospital Revenue + Non-Hospital Revenue + Complex Building & BIS - Direct Cost` |
| Total Expenses | `Cost of Goods Sold + Operating Cost + Staff Cost + Bonus + Administrative + Repair & Maintenance + Sales & Marketing + Commission Expense + Taxes` |
| EBITDA | `Net Operating Revenue - Total Expenses` |
| EBIT | `EBITDA - Depreciation & Amortization` |
| Earnings Before Tax | `EBIT + Interest Income - Finance Expenses` |
| Earnings After Tax | `Earnings Before Tax - Income Tax` |

### Notes percentages and comparison columns

| Item | Rule |
|---|---|
| Actual % on a group/account | `group or account balance / its percentage base × 100` |
| Outpatients and Other (EOPD, Day care) | Shared base: `Outpatients + Other (EOPD, Day care)` |
| Other Hospital Revenue, Non-Hospital Revenue, Complex Building & BIS | Shared base: the sum of those three groups |
| Staff Cost and Bonus | Shared base: `Staff Cost + Bonus` |
| All other groups/accounts | Their own group balance is the base; the group itself therefore displays 100% when non-zero |
| Period Total | Sum of the current period plus the selected previous comparison periods |
| Budget % | `Actual / Budget × 100` in the Notes report's native budget comparison |

## 5. Income-tax scope

The current report reads the posted balance of account **707010 — Income Tax Expenses**. It does **not** currently calculate or create a 22% tax journal entry. That automation requires a business decision on the posting trigger and journal before it can be safely added.

## 6. Maintenance rule

To add, move, or remove an account, update the account-code list for the relevant group in `models/profit_and_loss_report.py`. The Summary and Notes both use that same mapping, so the change affects both reports; then revalidate the affected totals and account unfolding in THA.
