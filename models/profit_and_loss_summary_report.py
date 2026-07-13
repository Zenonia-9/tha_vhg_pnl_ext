# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class VhgProfitAndLossSummaryReportHandler(models.AbstractModel):
    _name = "tha.vhg.pnl.summary.report.handler"
    _inherit = "tha.vhg.pnl.report.handler"
    _description = "VHG Management Profit and Loss Summary Handler"

    _DEMO_BUDGET_NAME = "VHG Summary Demo Budget FY2026-27"
    _SEQUENCES = {
        "inpatient": "1",
        "outpatient": "2",
        "eopd_day_care": "3",
        "direct_cost": "4",
        "cost_of_goods_sold": "5",
        "operating_cost": "6",
        "staff_cost": "7",
        "bonus": "7.1",
        "administrative": "8",
        "repair_maintenance": "9",
        "sales_marketing": "10",
        "other_hospital_revenue": "11",
        "non_hospital_revenue": "12",
        "depreciation": "13",
        "financial_net": "14",
        "rental_complex": "15",
        "income_tax": "16",
    }
    _REVENUE_GROUPS = ("inpatient", "outpatient", "eopd_day_care")
    _OTHER_REVENUE_GROUPS = (
        "other_hospital_revenue", "non_hospital_revenue", "rental_complex",
    )

    def _custom_options_initializer(self, report, options, previous_options):
        selected_date = fields.Date.to_date(options["date"]["date_to"])
        month_start = selected_date.replace(day=1)
        month_end = month_start + relativedelta(months=1, days=-1)
        company = self.env["res.company"].browse(report.get_report_company_ids(options)[:1]) or self.env.company
        fiscal_dates = company.compute_fiscalyear_dates(selected_date)
        fiscal_start = fiscal_dates["date_from"].replace(day=1)
        fiscal_end = fiscal_dates["date_to"]
        months = []
        cursor = fiscal_start
        while cursor <= fiscal_end:
            months.append((cursor, cursor + relativedelta(months=1, days=-1)))
            cursor += relativedelta(months=1)

        selected_budget_ids = [
            budget["id"] for budget in options.get("budgets", []) if budget.get("selected")
        ][:1]
        for budget in options.get("budgets", []):
            budget["selected"] = budget["id"] in selected_budget_ids

        show_months = previous_options.get("vhg_show_monthly_columns", True)
        options.update({
            "vhg_show_monthly_columns": bool(show_months),
            "vhg_summary_month_keys": [],
            "vhg_summary_selected_month_key": f"actual_{month_start:%Y_%m}",
            "vhg_summary_ytd_month_keys": [
                f"actual_{start:%Y_%m}" for start, _end in months if start <= month_start
            ],
            "vhg_summary_budget_id": selected_budget_ids[0] if selected_budget_ids else None,
            "vhg_summary_query_groups": {},
            "vhg_summary_fiscal_label": f"FY {fiscal_start:%b %Y} - {fiscal_end:%b %Y}",
        })

        for start, end in months:
            key = f"actual_{start:%Y_%m}"
            options["vhg_summary_month_keys"].append(key)
            options["vhg_summary_query_groups"][key] = self._query_group(start, end)
        if selected_budget_ids:
            budget_id = selected_budget_ids[0]
            options["vhg_summary_query_groups"]["budget_mtd"] = self._query_group(
                month_start, month_end, budget_id
            )
            options["vhg_summary_query_groups"]["budget_fy"] = self._query_group(
                fiscal_start, fiscal_end, budget_id
            )

        options["column_groups"] = {"summary": {"forced_options": {}, "forced_domain": []}}
        options["columns"] = self._display_columns(months if show_months else [])
        options["column_headers"] = [[{"name": column["name"]} for column in options["columns"]]]
        options["unfolded_lines"] = []
        options["unfold_all"] = False
        options["custom_display_config"].update({
            "templates": {
                "AccountReportFilters": "tha_vhg_pnl_ext.SummaryReportFilters",
                "AccountReportHeader": "tha_vhg_pnl_ext.SummaryReportHeader",
                "AccountReportLine": "tha_vhg_pnl_ext.SummaryReportLine",
            },
            "components": {"AccountReportFilters": "VhgPnlSummaryFilters"},
            "pdf_export": {
                "pdf_export_main_table_header": "tha_vhg_pnl_ext.summary_pdf_header",
                "pdf_export_main_table_body": "tha_vhg_pnl_ext.summary_pdf_body",
            },
            "css_custom_class": "o_vhg_pnl_summary",
        })

    @staticmethod
    def _query_group(date_from, date_to, budget_id=None):
        forced_options = {
            "date": {
                "date_from": fields.Date.to_string(date_from),
                "date_to": fields.Date.to_string(date_to),
                "mode": "range",
                "period_type": "month",
                "currency_table_period_key": f"{date_from}_{date_to}",
                "string": f"{date_from:%b %Y}",
            },
        }
        if budget_id:
            forced_options["compute_budget"] = budget_id
        return {"forced_options": forced_options, "forced_domain": []}

    @staticmethod
    def _column(name, label, figure_type="monetary"):
        return {
            "name": name,
            "column_group_key": "summary",
            "expression_label": label,
            "figure_type": figure_type,
            "sortable": False,
        }

    def _display_columns(self, months):
        columns = [
            self._column("Actual", "mtd_actual"),
            self._column("%", "mtd_actual_percent", "percentage"),
            self._column("Budget", "mtd_budget"),
            self._column("%", "mtd_budget_percent", "percentage"),
            self._column("Variance", "mtd_variance"),
            self._column("%", "mtd_variance_percent", "percentage"),
            self._column("No.", "sequence", "string"),
            self._column("Actual", "ytd_actual"),
            self._column("%", "ytd_actual_percent", "percentage"),
        ]
        columns.extend(
            self._column(start.strftime("%b %Y"), f"month_{start:%Y_%m}")
            for start, _end in months
        )
        columns.extend([
            self._column("Budget", "fy_budget"),
            self._column("%", "fy_budget_percent", "percentage"),
            self._column("Variance", "fy_variance"),
            self._column("%", "fy_variance_percent", "percentage"),
        ])
        return columns

    def _query_summary_balances(self, report, options):
        query_options = dict(options)
        query_options["column_groups"] = options["vhg_summary_query_groups"]
        query_options["columns"] = [
            {
                "name": "Balance",
                "expression_label": "balance",
                "column_group_key": key,
            }
            for key in query_options["column_groups"]
        ]
        return super()._query_group_balances(report, query_options)[0]

    def _summary_values(self, group_balances):
        values = {key: defaultdict(float, balances) for key, balances in group_balances.items()}
        values["total_revenue"] = self._combine(values, additions=self._REVENUE_GROUPS)
        values["net_revenues"] = self._combine(
            values, additions=self._REVENUE_GROUPS, deductions=("direct_cost",)
        )
        values["other_revenue"] = self._combine(values, additions=self._OTHER_REVENUE_GROUPS)
        values["total_net_revenues"] = self._combine(
            values,
            additions=(*self._REVENUE_GROUPS, *self._OTHER_REVENUE_GROUPS),
            deductions=("direct_cost",),
        )
        values["total_expenses"] = self._combine(values, additions=self._OPERATING_EXPENSE_GROUPS)
        values["ebitda"] = self._subtract(values["total_net_revenues"], values["total_expenses"])
        values["ebit"] = self._subtract(values["ebitda"], values["depreciation"])
        values["financial_net"] = self._subtract(
            values["interest_income"], values["finance_expenses"]
        )
        values["earnings_before_tax"] = self._add(values["ebit"], values["financial_net"])
        values["earnings_after_tax"] = self._subtract(
            values["earnings_before_tax"], values["income_tax"]
        )
        return values

    @staticmethod
    def _add(left, right):
        result = defaultdict(float, left)
        for key, value in right.items():
            result[key] += value
        return result

    @staticmethod
    def _subtract(left, right):
        result = defaultdict(float, left)
        for key, value in right.items():
            result[key] -= value
        return result

    def _percentage_denominator(self, row_key):
        if row_key in self._REVENUE_GROUPS or row_key == "total_revenue":
            return "total_revenue"
        if row_key == "direct_cost" or row_key in self._OTHER_REVENUE_GROUPS or row_key in (
            "net_revenues", "other_revenue",
        ):
            return "net_revenues"
        return "total_net_revenues"

    @staticmethod
    def _ratio(value, denominator):
        return value * 100.0 / denominator if denominator else None

    def _line_columns(self, report, options, row_key, values, sequence):
        selected_key = options["vhg_summary_selected_month_key"]
        ytd_keys = options["vhg_summary_ytd_month_keys"]
        denominator_key = self._percentage_denominator(row_key)
        mtd_actual = values[row_key][selected_key]
        ytd_actual = sum(values[row_key][key] for key in ytd_keys)
        mtd_actual_denominator = values[denominator_key][selected_key]
        ytd_actual_denominator = sum(values[denominator_key][key] for key in ytd_keys)
        has_budget = bool(options.get("vhg_summary_budget_id"))
        mtd_budget = values[row_key]["budget_mtd"] if has_budget else None
        fy_budget = values[row_key]["budget_fy"] if has_budget else None
        mtd_budget_denominator = values[denominator_key]["budget_mtd"] if has_budget else None
        fy_budget_denominator = values[denominator_key]["budget_fy"] if has_budget else None
        ytd_variance = mtd_actual - mtd_budget if has_budget else None
        fy_variance = ytd_actual - fy_budget if has_budget else None

        data = {
            "mtd_actual": mtd_actual,
            "mtd_actual_percent": self._ratio(mtd_actual, mtd_actual_denominator),
            "mtd_budget": mtd_budget,
            "mtd_budget_percent": self._ratio(mtd_budget, mtd_budget_denominator) if has_budget else None,
            "mtd_variance": ytd_variance,
            "mtd_variance_percent": self._ratio(ytd_variance, mtd_budget) if has_budget else None,
            "sequence": sequence,
            "ytd_actual": ytd_actual,
            "ytd_actual_percent": self._ratio(ytd_actual, ytd_actual_denominator),
            "fy_budget": fy_budget,
            "fy_budget_percent": self._ratio(fy_budget, fy_budget_denominator) if has_budget else None,
            "fy_variance": fy_variance,
            "fy_variance_percent": self._ratio(fy_variance, fy_budget) if has_budget else None,
        }
        for month_key in options["vhg_summary_month_keys"]:
            data[f"month_{month_key.removeprefix('actual_')}"] = values[row_key][month_key]

        columns = []
        for column in options["columns"]:
            value = data.get(column["expression_label"])
            columns.append(report._build_column_dict(
                value,
                column,
                options=options,
                digits=2 if column["figure_type"] == "percentage" else 1,
            ))
        return columns

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        group_balances = self._query_summary_balances(report, options)
        values = self._summary_values(group_balances)

        group_names = {key: name for key, name, _sign, _codes in self._GROUPS}
        group_names.update({
            "inpatient": "Inpatients",
            "outpatient": "Outpatients",
            "eopd_day_care": "Other (EOPD, Day care)",
            "direct_cost": "Direct Cost",
            "other_hospital_revenue": "Other Hospital Revenue",
            "non_hospital_revenue": "Non-Hospital Revenue",
            "rental_complex": "Complex Building & BIS",
            "cost_of_goods_sold": "Cost of Goods Sold",
            "financial_net": "Financial Expense & Income",
        })
        rows = (
            ("inpatient", group_names["inpatient"]),
            ("outpatient", group_names["outpatient"]),
            ("eopd_day_care", group_names["eopd_day_care"]),
            ("total_revenue", "Total Revenue"),
            ("direct_cost", group_names["direct_cost"]),
            ("net_revenues", "Net Revenues"),
            ("other_hospital_revenue", group_names["other_hospital_revenue"]),
            ("non_hospital_revenue", group_names["non_hospital_revenue"]),
            ("rental_complex", group_names["rental_complex"]),
            ("other_revenue", "Other Revenue"),
            ("total_net_revenues", "Total Net Revenues"),
            *((key, group_names[key]) for key in self._OPERATING_EXPENSE_GROUPS),
            ("total_expenses", "Total Expenses"),
            ("ebitda", "EBITDA"),
            ("depreciation", group_names["depreciation"]),
            ("ebit", "EBIT"),
            ("financial_net", group_names["financial_net"]),
            ("earnings_before_tax", "Earnings Before Tax"),
            ("income_tax", group_names["income_tax"]),
            ("earnings_after_tax", "Earnings After Tax"),
        )
        total_keys = {
            "total_revenue", "net_revenues", "other_revenue", "total_net_revenues",
            "total_expenses", "ebitda", "ebit", "earnings_before_tax", "earnings_after_tax",
        }
        return [
            (0, {
                "id": report._get_generic_line_id(None, None, markup=f"vhg_pnl_summary_{key}"),
                "name": name,
                "level": 0 if key in total_keys else 1,
                "class": "fw-bold" if key in total_keys else "",
                "columns": self._line_columns(
                    report, options, key, values, self._SEQUENCES.get(key, "")
                ),
                "unfoldable": False,
                "unfolded": False,
            })
            for key, name in rows
        ]

    def seed_demo_budget(self):
        company = self.env["res.company"].search([
            ("name", "ilike", "THUKHA SAYTANAR CO. Ltd")
        ], limit=1)
        if not company:
            raise UserError(_("Victoria Hospital company was not found."))

        codes = []
        code_meta = {}
        for group_index, (_key, _name, sign, group_codes) in enumerate(self._GROUPS, start=1):
            for account_index, code in enumerate(group_codes, start=1):
                if code not in code_meta:
                    codes.append(code)
                    code_meta[code] = (group_index, account_index, sign)
        accounts = self.env["account.account"].with_company(company).search([
            ("code", "in", codes),
            ("company_ids", "in", company.id),
        ])
        account_by_code = {account.code.strip(): account for account in accounts}
        missing = sorted(set(codes) - set(account_by_code))
        if missing:
            raise UserError(_("Mapped COA codes missing from THA: %s", ", ".join(missing)))

        budget = self.env["account.report.budget"].search([
            ("name", "=", self._DEMO_BUDGET_NAME),
            ("company_id", "=", company.id),
        ], limit=1)
        if not budget:
            budget = self.env["account.report.budget"].create({
                "name": self._DEMO_BUDGET_NAME,
                "company_id": company.id,
            })

        months = [date(2026, 4, 1) + relativedelta(months=index) for index in range(12)]
        existing = {
            (item.account_id.id, item.date): item
            for item in budget.item_ids
        }
        expected_keys = set()
        created = updated = 0
        for code in codes:
            account = account_by_code[code]
            group_index, account_index, sign = code_meta[code]
            for month_index, month in enumerate(months, start=1):
                key = (account.id, month)
                expected_keys.add(key)
                display_amount = 100000 + group_index * 10000 + account_index * 100 + month_index * 1000
                amount = display_amount * sign
                item = existing.get(key)
                if item:
                    if item.amount != amount:
                        item.amount = amount
                        updated += 1
                else:
                    self.env["account.report.budget.item"].create({
                        "budget_id": budget.id,
                        "account_id": account.id,
                        "date": month,
                        "amount": amount,
                    })
                    created += 1
        extras = budget.item_ids.filtered(lambda item: (item.account_id.id, item.date) not in expected_keys)
        removed = len(extras)
        extras.unlink()
        return {
            "budget_id": budget.id,
            "created": created,
            "updated": updated,
            "removed": removed,
            "items": len(expected_keys),
        }
