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
    _DEMO_BUDGET_PREFIX = "VHG Summary Demo Budget "
    _REVENUE_GROUPS = ("inpatient", "outpatient", "eopd_day_care")
    _OTHER_REVENUE_GROUPS = (
        "other_hospital_revenue", "non_hospital_revenue", "rental_complex",
    )
    _SUMMARY_OPERATING_EXPENSE_GROUPS = (
        "cost_of_goods_sold", "operating_cost", "staff_cost", "bonus",
        "administrative", "repair_maintenance", "sales_marketing", "commission_expense",
    )

    def _custom_options_initializer(self, report, options, previous_options):
        horizontal_mode = bool(options.get("selected_horizontal_group_id"))
        horizontal_entities = self._horizontal_entities(options) if horizontal_mode else []
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

        show_months = previous_options.get("vhg_show_monthly_columns", False)
        hide_zero_months = previous_options.get("vhg_hide_zero_monthly_columns", True)
        previous_month_start = month_start - relativedelta(months=1)
        previous_month_end = month_start - relativedelta(days=1)
        options.update({
            "vhg_show_monthly_columns": bool(show_months),
            "vhg_hide_zero_monthly_columns": bool(hide_zero_months),
            "vhg_summary_month_keys": [],
            "vhg_summary_budget_month_keys": [],
            "vhg_summary_fiscal_month_keys": [],
            "vhg_summary_selected_month_key": f"actual_{month_start:%Y_%m}",
            "vhg_summary_ytd_month_keys": [
                f"actual_{start:%Y_%m}" for start, _end in months if start <= month_start
            ],
            "vhg_summary_budget_id": selected_budget_ids[0] if selected_budget_ids else None,
            "vhg_summary_query_groups": {},
            "vhg_summary_horizontal_mode": horizontal_mode,
            "vhg_summary_horizontal_entities": horizontal_entities,
            "vhg_summary_fiscal_label": f"FY {fiscal_start:%b %Y} - {fiscal_end:%b %Y}",
            "vhg_summary_mtd_label": f"Month to Date - {month_start:%b %Y}",
            "vhg_summary_ytd_actual_label": f"Year to Date Actual - {fiscal_start:%b} to {month_start:%b %Y}",
            "vhg_summary_ytd_budget_label": f"Year to Date Budget - {fiscal_start:%b} to {month_start:%b %Y}",
        })

        if horizontal_mode:
            period_label = f"{fiscal_start:%b-%y} to {month_start:%b-%y}"
            for entity in horizontal_entities:
                options["vhg_summary_query_groups"][entity["query_key"]] = self._query_group(
                    fiscal_start, month_end, forced_domain=entity["forced_domain"]
                )
            visible_months = []
            if show_months:
                for start, end in months:
                    key = f"actual_{start:%Y_%m}"
                    options["vhg_summary_fiscal_month_keys"].append(key)
                    options["vhg_summary_query_groups"][key] = self._query_group(start, end)
                visible_months = months
                if hide_zero_months:
                    group_balances = self._query_summary_balances(report, options)
                    visible_months = [
                        (start, end) for start, end in visible_months
                        if self._month_has_actual(group_balances, start)
                    ]
                options["vhg_summary_month_keys"] = [
                    f"actual_{start:%Y_%m}" for start, _end in visible_months
                ]
            if selected_budget_ids:
                options["vhg_summary_query_groups"]["budget_ytd"] = self._query_group(
                    fiscal_start, month_end, selected_budget_ids[0]
                )
            options["vhg_summary_horizontal_period_label"] = period_label
            options["vhg_summary_horizontal_headers"] = [
                {"name": entity["name"], "colspan": 2}
                for entity in horizontal_entities
            ] + [
                {"name": f"Conso ({period_label})", "colspan": 2},
            ]
            if visible_months:
                options["vhg_summary_horizontal_headers"].append({
                    "name": f"Monthly Conso (FY {fiscal_start:%Y}-{fiscal_end:%y})",
                    "colspan": len(visible_months),
                })
            options["vhg_summary_horizontal_headers"].extend([
                {"name": "Budget", "colspan": 2},
                {"name": "Variance", "colspan": 2},
            ])
            options["column_groups"] = {"summary": {"forced_options": {}, "forced_domain": []}}
            options["columns"] = self._horizontal_display_columns(
                horizontal_entities, period_label, visible_months
            )
            options["column_headers"] = [[{"name": column["name"]} for column in options["columns"]]]
        else:
            for start, end in months:
                key = f"actual_{start:%Y_%m}"
                options["vhg_summary_fiscal_month_keys"].append(key)
                options["vhg_summary_query_groups"][key] = self._query_group(start, end)
            previous_month_key = f"actual_{previous_month_start:%Y_%m}"
            if previous_month_key not in options["vhg_summary_query_groups"]:
                options["vhg_summary_query_groups"][previous_month_key] = self._query_group(
                    previous_month_start, previous_month_end
                )
            if selected_budget_ids:
                budget_id = selected_budget_ids[0]
                options["vhg_summary_query_groups"]["budget_mtd"] = self._query_group(
                    month_start, month_end, budget_id
                )
                options["vhg_summary_query_groups"]["budget_ytd"] = self._query_group(
                    fiscal_start, month_end, budget_id
                )

            if show_months or hide_zero_months:
                group_balances = self._query_summary_balances(report, options)
            if show_months:
                visible_months = months
            else:
                visible_months = [
                    (previous_month_start, previous_month_end),
                    (month_start, month_end),
                ]
            if hide_zero_months:
                visible_months = [
                    (start, end) for start, end in visible_months
                    if self._month_has_actual(group_balances, start)
                ]
            options["vhg_summary_month_keys"] = [
                f"actual_{start:%Y_%m}" for start, _end in visible_months
            ]
            # Budget months follow the selected fiscal period, independently of
            # whether the matching Actual month is zero.
            budget_months = []
            if show_months:
                budget_months = [
                    (start, end) for start, end in months if start <= month_start
                ]
                options["vhg_summary_budget_month_keys"] = [
                    f"budget_{start:%Y_%m}" for start, _end in budget_months
                ]
                if selected_budget_ids:
                    budget_id = selected_budget_ids[0]
                    for start, end in budget_months:
                        key = f"budget_{start:%Y_%m}"
                        options["vhg_summary_query_groups"][key] = self._query_group(
                            start, end, budget_id
                        )

            options["column_groups"] = {"summary": {"forced_options": {}, "forced_domain": []}}
            options["columns"] = self._display_columns(
                visible_months, month_start, budget_months=budget_months
            )
            options["column_headers"] = [[{"name": column["name"]} for column in options["columns"]]]

        options["unfolded_lines"] = []
        options["unfold_all"] = False
        options["show_horizontal_group_total"] = False
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

    def _horizontal_entities(self, options):
        entities = []
        seen = set()
        horizontal_group = self.env["account.report.horizontal.group"].browse(
            options["selected_horizontal_group_id"]
        )
        field_order = horizontal_group.rule_ids.mapped("field_name")
        for column in options.get("columns", []):
            column_group = options.get("column_groups", {}).get(column["column_group_key"], {})
            element = tuple(column_group.get("horizontal_groupby_element", ()))
            if not element or element in seen:
                continue
            seen.add(element)
            element_values = dict(element)
            names = []
            for field_name in field_order:
                record_id = element_values.get(field_name)
                field = self.env["account.move.line"]._fields[field_name]
                record = self.env[field.comodel_name].browse(record_id)
                names.append(record.display_name)
            entities.append({
                "name": " / ".join(names),
                "query_key": f"horizontal_{len(entities)}",
                "forced_domain": list(column_group.get("forced_domain", [])),
            })
        return entities

    @staticmethod
    def _month_has_actual(group_balances, month_start):
        month_key = f"actual_{month_start:%Y_%m}"
        return any(
            balances.get(month_key)
            for balances in group_balances.values()
        )

    @staticmethod
    def _query_group(date_from, date_to, budget_id=None, forced_domain=None):
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
        return {"forced_options": forced_options, "forced_domain": forced_domain or []}

    @staticmethod
    def _column(name, label, figure_type="monetary"):
        return {
            "name": name,
            "column_group_key": "summary",
            "expression_label": label,
            "figure_type": figure_type,
            "sortable": False,
        }

    def _display_columns(self, months, selected_month, budget_months=None):
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
        if budget_months:
            columns.extend(
                self._column(start.strftime("%b %Y"), f"budget_month_{start:%Y_%m}")
                for start, _end in budget_months
            )
        columns.extend([
            self._column("Budget", "ytd_budget"),
            self._column("%", "ytd_budget_percent", "percentage"),
            self._column("Variance", "ytd_variance"),
            self._column("%", "ytd_variance_percent", "percentage"),
        ])
        return columns

    @staticmethod
    def _format_display_column(report, options, percentage_options, column, value, column_dict):
        figure_type = column["figure_type"]
        if figure_type == "percentage":
            formatted_value = report.format_value(
                percentage_options,
                value,
                "percentage",
                format_params=column_dict["format_params"],
            )
        elif figure_type == "monetary":
            rounding_factor = {
                "decimals": 1.0,
                "units": 1.0,
                "thousands": 1_000.0,
                "lakhs": 100_000.0,
                "millions": 1_000_000.0,
            }.get(options.get("rounding_unit"), 1.0)
            formatted_value = report.format_value(
                {**options, "rounding_unit": "decimals"},
                value / rounding_factor if value is not None else None,
                "float",
                format_params={"digits": 2},
            )
        else:
            return column_dict

        column_dict["name"] = formatted_value
        if options.get("export_mode") != "file":
            column_dict.update({
                "figure_type": "string",
                "no_format": formatted_value if value is not None else None,
            })
        return column_dict

    def _horizontal_display_columns(self, entities, period_label, months):
        columns = [self._column("No.", "sequence", "string")]
        for index, _entity in enumerate(entities):
            columns.extend([
                self._column(period_label, f"horizontal_{index}_actual"),
                self._column("%", f"horizontal_{index}_percent", "percentage"),
            ])
        columns.extend([
            self._column("Total", "consolidated_actual"),
            self._column("%", "consolidated_percent", "percentage"),
        ])
        columns.extend(
            self._column(start.strftime("%b %Y"), f"month_{start:%Y_%m}")
            for start, _end in months
        )
        columns.extend([
            self._column(period_label, "ytd_budget"),
            self._column("%", "ytd_budget_percent", "percentage"),
            self._column("Amount", "ytd_variance"),
            self._column("%", "ytd_variance_percent", "percentage"),
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
        report._init_options_currency_table(query_options, {})
        report._init_currency_table(query_options)
        return super()._query_group_balances(report, query_options)[0]

    def _summary_values(self, group_balances):
        values = {key: defaultdict(float, balances) for key, balances in group_balances.items()}
        values["administrative"] = self._add(values["administrative"], values["taxes"])
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
        values["total_expenses"] = self._combine(
            values, additions=self._SUMMARY_OPERATING_EXPENSE_GROUPS
        )
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
        if options.get("vhg_summary_horizontal_mode"):
            return self._horizontal_line_columns(report, options, row_key, values, sequence)

        selected_key = options["vhg_summary_selected_month_key"]
        ytd_keys = options["vhg_summary_ytd_month_keys"]
        denominator_key = self._percentage_denominator(row_key)
        mtd_actual = values[row_key][selected_key]
        ytd_actual = sum(values[row_key][key] for key in ytd_keys)
        mtd_actual_denominator = values[denominator_key][selected_key]
        ytd_actual_denominator = sum(values[denominator_key][key] for key in ytd_keys)
        has_budget = bool(options.get("vhg_summary_budget_id"))
        mtd_budget = values[row_key]["budget_mtd"] if has_budget else None
        ytd_budget = values[row_key]["budget_ytd"] if has_budget else None
        mtd_budget_denominator = values[denominator_key]["budget_mtd"] if has_budget else None
        ytd_budget_denominator = values[denominator_key]["budget_ytd"] if has_budget else None
        mtd_variance = mtd_actual - mtd_budget if has_budget else None
        ytd_variance = ytd_actual - ytd_budget if has_budget else None

        data = {
            "mtd_actual": mtd_actual,
            "mtd_actual_percent": self._ratio(mtd_actual, mtd_actual_denominator),
            "mtd_budget": mtd_budget,
            "mtd_budget_percent": self._ratio(mtd_budget, mtd_budget_denominator) if has_budget else None,
            "mtd_variance": mtd_variance,
            "mtd_variance_percent": self._ratio(mtd_variance, mtd_budget) if has_budget else None,
            "sequence": sequence,
            "ytd_actual": ytd_actual,
            "ytd_actual_percent": self._ratio(ytd_actual, ytd_actual_denominator),
            "ytd_budget": ytd_budget,
            "ytd_budget_percent": self._ratio(ytd_budget, ytd_budget_denominator) if has_budget else None,
            "ytd_variance": ytd_variance,
            "ytd_variance_percent": self._ratio(ytd_variance, ytd_budget) if has_budget else None,
        }
        for month_key in options["vhg_summary_month_keys"]:
            data[f"month_{month_key.removeprefix('actual_')}"] = values[row_key][month_key]
        for budget_month_key in options["vhg_summary_budget_month_keys"]:
            data[f"budget_month_{budget_month_key.removeprefix('budget_')}"] = (
                values[row_key][budget_month_key] if has_budget else None
            )

        columns = []
        percentage_options = {**options, "rounding_unit": "decimals"}
        for column in options["columns"]:
            value = data.get(column["expression_label"])
            column_dict = report._build_column_dict(
                value,
                column,
                options=(
                    percentage_options
                    if column["figure_type"] == "percentage"
                    else options
                ),
                digits=2 if column["figure_type"] == "percentage" else 1,
            )
            column_dict = self._format_display_column(
                report, options, percentage_options, column, value, column_dict
            )
            columns.append(column_dict)
        return columns

    def _horizontal_line_columns(self, report, options, row_key, values, sequence):
        denominator_key = self._percentage_denominator(row_key)
        data = {"sequence": sequence}
        consolidated_actual = 0.0
        consolidated_denominator = 0.0
        for index, entity in enumerate(options["vhg_summary_horizontal_entities"]):
            query_key = entity["query_key"]
            actual = values[row_key][query_key]
            denominator = values[denominator_key][query_key]
            data[f"horizontal_{index}_actual"] = actual
            data[f"horizontal_{index}_percent"] = self._ratio(actual, denominator)
            consolidated_actual += actual
            consolidated_denominator += denominator

        has_budget = bool(options.get("vhg_summary_budget_id"))
        budget = values[row_key]["budget_ytd"] if has_budget else None
        budget_denominator = values[denominator_key]["budget_ytd"] if has_budget else None
        variance = consolidated_actual - budget if has_budget else None
        data.update({
            "consolidated_actual": consolidated_actual,
            "consolidated_percent": self._ratio(
                consolidated_actual, consolidated_denominator
            ),
            "ytd_budget": budget,
            "ytd_budget_percent": self._ratio(budget, budget_denominator) if has_budget else None,
            "ytd_variance": variance,
            "ytd_variance_percent": self._ratio(variance, budget) if has_budget else None,
        })
        for month_key in options["vhg_summary_month_keys"]:
            data[f"month_{month_key.removeprefix('actual_')}"] = values[row_key][month_key]
        percentage_options = {**options, "rounding_unit": "decimals"}
        columns = []
        for column in options["columns"]:
            value = data.get(column["expression_label"])
            column_dict = report._build_column_dict(
                value,
                column,
                options=(
                    percentage_options
                    if column["figure_type"] == "percentage"
                    else options
                ),
                digits=2 if column["figure_type"] == "percentage" else 1,
            )
            column_dict = self._format_display_column(
                report, options, percentage_options, column, value, column_dict
            )
            columns.append(column_dict)
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
            *((key, group_names[key]) for key in self._SUMMARY_OPERATING_EXPENSE_GROUPS),
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
        group_keys = {
            *self._REVENUE_GROUPS,
            "direct_cost",
            *self._OTHER_REVENUE_GROUPS,
            *self._SUMMARY_OPERATING_EXPENSE_GROUPS,
            "depreciation",
            "financial_net",
            "income_tax",
        }
        group_number = 0
        lines = []
        for key, name in rows:
            sequence = ""
            if key == "commission_expense":
                sequence = "14.1"
            elif key in group_keys:
                group_number += 1
                sequence = str(group_number)
            lines.append((0, {
                "id": report._get_generic_line_id(None, None, markup=f"vhg_pnl_summary_{key}"),
                "name": name,
                "level": 0 if key in total_keys else 1,
                "class": "fw-bold" if key in total_keys else "",
                "columns": self._line_columns(
                    report, options, key, values, sequence
                ),
                "unfoldable": False,
                "unfolded": False,
            }))
        return lines

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

        months = [date(2026, 4, 1) + relativedelta(months=index) for index in range(12)]
        monthly_names = [
            f"{self._DEMO_BUDGET_PREFIX}{month:%b}".replace(
                f"{month:%b}", month.strftime("%b").upper()
            ) + f" {month:%y}"
            for month in months
        ]
        annual_matches = self.env["account.report.budget"].search([
            ("name", "=", self._DEMO_BUDGET_NAME),
            ("company_id", "=", company.id),
        ], order="id")
        annual_budget = annual_matches[:1]
        duplicate_budgets = annual_matches[1:]
        if not annual_budget:
            annual_budget = self.env["account.report.budget"].create({
                "name": self._DEMO_BUDGET_NAME,
                "company_id": company.id,
            })
        removed = len(duplicate_budgets.item_ids)
        duplicate_budgets.unlink()

        budgets = {}
        duplicate_budgets = self.env["account.report.budget"]
        for name in monthly_names:
            matches = self.env["account.report.budget"].search([
                ("name", "=", name),
                ("company_id", "=", company.id),
            ], order="id")
            budget = matches[:1]
            duplicate_budgets |= matches[1:]
            if not budget:
                budget = self.env["account.report.budget"].create({
                    "name": name,
                    "company_id": company.id,
                })
            budgets[name] = budget
        removed += len(duplicate_budgets.item_ids)
        duplicate_budgets.unlink()
        budgets[self._DEMO_BUDGET_NAME] = annual_budget

        created = updated = 0
        items_per_budget = {}
        budget_targets = [(annual_budget, list(enumerate(months, start=1)))]
        budget_targets.extend(
            (budgets[monthly_names[month_index - 1]], [(month_index, month)])
            for month_index, month in enumerate(months, start=1)
        )
        for budget, target_months in budget_targets:
            existing = {
                (item.account_id.id, item.date): item
                for item in budget.item_ids
            }
            expected_keys = set()
            for month_index, month in target_months:
                for code in codes:
                    account = account_by_code[code]
                    group_index, account_index, sign = code_meta[code]
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
            extras = budget.item_ids.filtered(
                lambda item: (item.account_id.id, item.date) not in expected_keys
            )
            removed += len(extras)
            extras.unlink()
            items_per_budget[budget.name] = len(expected_keys)
        return {
            "budget_ids": [budgets[name].id for name in monthly_names] + [annual_budget.id],
            "budget_names": monthly_names + [self._DEMO_BUDGET_NAME],
            "created": created,
            "updated": updated,
            "removed": removed,
            "items_per_budget": items_per_budget,
        }
