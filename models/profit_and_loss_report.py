# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import models
from odoo.tools import SQL


class VhgProfitAndLossReportHandler(models.AbstractModel):
    _name = "tha.vhg.pnl.report.handler"
    _inherit = "account.report.custom.handler"
    _description = "VHG Workbook Profit and Loss Report Handler"

    # Group order and account codes follow VTR PL Note (June 26), column F.
    _GROUPS = (
        ("outpatient", "Outpatient (Revenue)", -1, (
            "500020", "500030", "500060", "500125", "500130", "500085",
            "500145", "500070", "500190", "500010", "500015", "500025",
            "500065", "500035", "500040", "500075", "500080",
        )),
        ("eopd_day_care", "Other (EOPD, Day care)", -1, (
            "500050", "500055", "500146", "500045",
        )),
        ("inpatient", "Inpatient (Revenue)", -1, (
            "500095", "500100", "500150", "500115", "500135",
        )),
        ("additional_revenue", "Additional Revenue", -1, (
            "500090", "500105", "500110", "500120", "500140", "500155",
            "500160", "500165", "500170", "500175", "500180", "500185",
            "500186", "500187", "500400", "500405", "500410", "500415",
            "500420", "500425", "500600", "510020", "510025",
        )),
        ("direct_cost", "Direct Cost", 1, (
            "600010", "600020", "600030", "600035", "600040", "600045",
            "600180", "600181", "600182", "600183", "600184", "600185",
            "600186", "600225",
        )),
        ("other_hospital_revenue", "Other Hospital Revenue (Partnership Income) By F&A", -1, (
            "510030", "510015", "510000", "510010", "510035",
        )),
        ("non_hospital_revenue", "Non Hospital Revenue (Rental & Other) By F&A", -1, (
            "510500", "510510", "510515", "510520", "510530", "510535",
            "510540", "510575", "510565", "510545", "510555",
        )),
        ("rental_complex", "Rental Complex Building & BIS By F&A", -1, (
            "510085", "510095", "510125", "510130",
        )),
        ("other_income", "Other Income", -1, (
            "510100", "510105", "510110", "510115", "510120", "510505",
            "510550", "510560", "510570", "510580", "510585",
        )),
        ("cost_of_goods_sold", "Cost of Goods Sold", 1, (
            "600050", "600060", "600070", "600080", "600090", "600100",
            "600110", "600120", "600130", "600140", "600150", "600170",
            "600160", "600190", "600200", "600210", "600220",
        )),
        ("operating_cost", "Operating Cost", 1, (
            "700010", "700020", "700030", "700040", "700050", "700060",
            "700080", "700090", "700100", "700110", "700120", "700130",
            "700140", "700170", "700180", "700190", "700070", "700150",
            "700160", "700200", "700210", "700220", "700225", "702311",
        )),
        ("staff_cost", "Staff Cost (Based on Head Count)", 1, (
            "701010", "701030", "701040", "701050", "701060", "701070",
            "701080", "701090", "701100", "701110", "701120", "701130",
            "701140", "701150", "701160", "701170", "701171", "701172",
            "701173", "701175", "703060",
        )),
        ("bonus", "Bonus", 1, ("701020",)),
        ("administrative", "Administrative & Other Expenses", 1, (
            "702010", "702020", "702030", "702040", "702050", "702060",
            "702070", "702080", "702090", "702100", "702110", "702120",
            "702130", "702140", "702150", "702160", "702170", "702180",
            "702190", "702200", "702210", "702220", "702230", "702240",
            "702250", "702260", "702270", "702280", "702290", "702300",
            "702310", "702315", "702316", "707020", "707030",
        )),
        ("repair_maintenance", "Repair & Maintenance", 1, (
            "703010", "703020", "703030", "703040", "703050", "703070",
            "703080", "703085",
        )),
        ("sales_marketing", "Sales & Marketing", 1, (
            "704010", "704020", "704030", "704040", "704050", "704055",
        )),
        ("depreciation", "Depreciation & Amortization", 1, (
            "705010", "705020", "705030", "705040", "705050", "705060",
            "705070", "705080", "705090", "705100", "705110", "705120",
            "705130", "705140", "705150", "705160", "705170", "705180",
            "705111", "705185",
        )),
        ("interest_income", "Interest Income", -1, ("500750",)),
        ("finance_expenses", "Finance Expenses", 1, (
            "706010", "706020", "706030", "706040", "706050", "706060",
            "706070", "706080",
        )),
        ("income_tax", "Income Tax", 1, ("707010",)),
    )

    _OPERATING_EXPENSE_GROUPS = (
        "cost_of_goods_sold", "operating_cost", "staff_cost", "bonus",
        "administrative", "repair_maintenance", "sales_marketing",
    )

    _SHARED_PERCENTAGE_GROUPS = {
        "outpatient": ("outpatient", "eopd_day_care"),
        "eopd_day_care": ("outpatient", "eopd_day_care"),
        "other_hospital_revenue": (
            "other_hospital_revenue", "non_hospital_revenue", "rental_complex", "other_income",
        ),
        "non_hospital_revenue": (
            "other_hospital_revenue", "non_hospital_revenue", "rental_complex", "other_income",
        ),
        "rental_complex": (
            "other_hospital_revenue", "non_hospital_revenue", "rental_complex", "other_income",
        ),
        "other_income": (
            "other_hospital_revenue", "non_hospital_revenue", "rental_complex", "other_income",
        ),
        "staff_cost": ("staff_cost", "bonus"),
        "bonus": ("staff_cost", "bonus"),
    }

    def _custom_options_initializer(self, report, options, previous_options):
        current_column_group_key = next(
            (
                column_group_key
                for column_group_key, column_group in options["column_groups"].items()
                if column_group.get("forced_options", {}).get("date", {}).get("date_from") == options["date"]["date_from"]
                and column_group.get("forced_options", {}).get("date", {}).get("date_to") == options["date"]["date_to"]
            ),
            None,
        )
        if not current_column_group_key:
            return

        actual_percent_column_group_key = "vhg_actual_percent"
        options["vhg_actual_percent_balance_column_group_key"] = current_column_group_key
        options["vhg_actual_percent_column_group_key"] = actual_percent_column_group_key
        if any(column["expression_label"] == "actual_percent" for column in options["columns"]):
            return

        column_groups = {}
        for column_group_key, column_group in options["column_groups"].items():
            if column_group_key == current_column_group_key:
                column_groups[actual_percent_column_group_key] = {
                    "forced_options": {
                        "date": dict(options["date"]),
                        "vhg_actual_percent": True,
                    },
                    "forced_domain": [],
                }
            column_groups[column_group_key] = column_group
        options["column_groups"] = column_groups

        for index, column in enumerate(options["columns"]):
            if column["column_group_key"] == current_column_group_key and column["expression_label"] == "balance":
                options["columns"].insert(index, {
                    "name": "%",
                    "column_group_key": actual_percent_column_group_key,
                    "expression_label": "actual_percent",
                    "sortable": False,
                    "figure_type": "percentage",
                    "blank_if_zero": False,
                    "style": "text-align: center; white-space: nowrap;",
                })
                break

        for index, header in enumerate(options["column_headers"][0]):
            header_date = header.get("forced_options", {}).get("date", {})
            if header_date.get("date_from") == options["date"]["date_from"] and header_date.get("date_to") == options["date"]["date_to"]:
                options["column_headers"][0].insert(index, {"name": "Actual %"})
                break

    def _query_group_balances(self, report, options):
        code_to_group = {
            code: (key, sign)
            for key, _name, sign, codes in self._GROUPS
            for code in codes
        }
        group_balances = {
            key: defaultdict(float) for key, _name, _sign, _codes in self._GROUPS
        }
        account_balances = {key: {} for key in group_balances}

        pnl_domain = [("account_id.account_type", "in", (
            "income", "income_other", "expense", "expense_depreciation",
            "expense_direct_cost",
        ))]
        companies = self.env["res.company"]

        for column_group_key, column_options in report._split_options_per_column_group(options).items():
            if column_group_key == options.get("vhg_actual_percent_column_group_key"):
                continue
            query = report._get_report_query(column_options, "strict_range", domain=pnl_domain)
            self.env.cr.execute(SQL(
                """
                SELECT
                    account_move_line.account_id AS account_id,
                    account_move_line.company_id AS company_id,
                    COALESCE(SUM(%(balance_select)s), 0.0) AS balance
                FROM %(from_clause)s
                %(currency_table_join)s
                WHERE %(where_clause)s
                GROUP BY account_move_line.account_id, account_move_line.company_id
                """,
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                from_clause=query.from_clause,
                currency_table_join=report._currency_table_aml_join(column_options),
                where_clause=query.where_clause,
            ))

            for row in self.env.cr.dictfetchall():
                company = companies.browse(row["company_id"])
                account = self.env["account.account"].browse(row["account_id"]).with_company(company)
                code = (account.code or "").strip()
                mapping = code_to_group.get(code)
                if not mapping:
                    continue

                group_key, sign = mapping
                balance = row["balance"] * sign
                group_balances[group_key][column_group_key] += balance
                account_key = (account.id, code)
                detail = account_balances[group_key].setdefault(account_key, {
                    "account_id": account.id,
                    "code": code,
                    "name": account.name,
                    "balances": defaultdict(float),
                })
                detail["balances"][column_group_key] += balance

        return group_balances, account_balances

    @staticmethod
    def _combine(group_balances, additions=(), deductions=()):
        result = defaultdict(float)
        for key in additions:
            for column_group_key, value in group_balances[key].items():
                result[column_group_key] += value
        for key in deductions:
            for column_group_key, value in group_balances[key].items():
                result[column_group_key] -= value
        return result

    def _columns(self, report, options, balances, actual_percent=None):
        columns = []
        for column in options["columns"]:
            is_actual_percent = column["expression_label"] == "actual_percent"
            columns.append(report._build_column_dict(
                actual_percent if is_actual_percent else balances.get(column["column_group_key"], 0.0),
                column,
                options=options,
                digits=2 if is_actual_percent else 1,
            ))
        return columns

    def _actual_percent(self, options, group_key, balances, group_balances):
        current_column_group_key = options.get("vhg_actual_percent_balance_column_group_key")
        if not current_column_group_key:
            return None

        denominator_groups = self._SHARED_PERCENTAGE_GROUPS.get(group_key, (group_key,))
        denominator = sum(
            group_balances[denominator_group][current_column_group_key]
            for denominator_group in denominator_groups
        )
        if not denominator:
            return None

        return balances.get(current_column_group_key, 0.0) * 100.0 / denominator

    def _group_line(self, report, options, key, name, balances):
        line_id = report._get_generic_line_id(None, None, markup=f"vhg_pnl_{key}")
        unfolded = line_id in options["unfolded_lines"] or options.get("unfold_all")
        return {
            "id": line_id,
            "name": name,
            "level": 1,
            "class": "fw-bold",
            "columns": self._columns(report, options, balances),
            "unfoldable": True,
            "unfolded": bool(unfolded),
            "expand_function": "_report_expand_unfoldable_line_vhg_pnl_group",
        }

    def _account_line(self, report, options, parent_id, group_key, detail, group_balances):
        line_id = report._get_generic_line_id(
            "account.account",
            detail["account_id"],
            parent_line_id=parent_id,
            markup=f"{group_key}_{detail['code']}",
        )
        return {
            "id": line_id,
            "name": f"{detail['code']} {detail['name']}".strip(),
            "level": 2,
            "parent_id": parent_id,
            "columns": self._columns(
                report,
                options,
                detail["balances"],
                actual_percent=self._actual_percent(options, group_key, detail["balances"], group_balances),
            ),
            "caret_options": "account.account",
        }

    def _total_line(self, report, options, key, name, balances):
        return {
            "id": report._get_generic_line_id(None, None, markup=f"vhg_pnl_{key}"),
            "name": name,
            "level": 0,
            "class": "fw-bold",
            "columns": self._columns(report, options, balances),
            "unfoldable": False,
        }

    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        group_balances, account_balances = self._query_group_balances(report, options)
        return {
            "group_balances": group_balances,
            "account_balances": account_balances,
        }

    def _report_expand_unfoldable_line_vhg_pnl_group(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        report = self.env["account.report"].browse(options["report_id"])
        markup, model, _record_id = report._parse_line_id(line_dict_id)[-1]
        prefix = "vhg_pnl_"
        group_key = markup.removeprefix(prefix) if not model and isinstance(markup, str) else None
        valid_group_keys = {key for key, _name, _sign, _codes in self._GROUPS}
        if group_key not in valid_group_keys:
            return {"lines": [], "offset_increment": 0, "has_more": False}

        if unfold_all_batch_data:
            group_balances = unfold_all_batch_data["group_balances"]
            account_balances = unfold_all_batch_data["account_balances"]
        else:
            group_balances, account_balances = self._query_group_balances(report, options)

        details = sorted(
            account_balances[group_key].values(),
            key=lambda detail: (detail["code"], detail["name"]),
        )
        lines = [
            self._account_line(report, options, line_dict_id, group_key, detail, group_balances)
            for detail in details
        ]
        return {
            "lines": lines,
            "offset_increment": len(lines),
            "has_more": False,
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        group_balances, _account_balances = self._query_group_balances(report, options)
        group_meta = {key: (name, codes) for key, name, _sign, codes in self._GROUPS}
        lines = []

        def add_group(key):
            name, _codes = group_meta[key]
            parent = self._group_line(report, options, key, name, group_balances[key])
            lines.append((0, parent))

        for key in ("outpatient", "eopd_day_care", "inpatient", "additional_revenue"):
            add_group(key)

        total_revenue = self._combine(
            group_balances,
            additions=("outpatient", "eopd_day_care", "inpatient", "additional_revenue"),
        )
        lines.append((0, self._total_line(report, options, "total_revenue", "Total Revenue", total_revenue)))

        add_group("direct_cost")
        net_revenues = self._combine(
            group_balances,
            additions=("outpatient", "eopd_day_care", "inpatient", "additional_revenue"),
            deductions=("direct_cost",),
        )
        lines.append((0, self._total_line(report, options, "net_revenues", "Net Revenues", net_revenues)))

        for key in ("other_hospital_revenue", "non_hospital_revenue", "rental_complex", "other_income"):
            add_group(key)

        net_operating_revenue = self._combine(
            group_balances,
            additions=(
                "outpatient", "eopd_day_care", "inpatient", "additional_revenue",
                "other_hospital_revenue", "non_hospital_revenue", "rental_complex", "other_income",
            ),
            deductions=("direct_cost",),
        )
        lines.append((0, self._total_line(
            report, options, "net_operating_revenue", "Net Operating Revenue", net_operating_revenue,
        )))

        for key in self._OPERATING_EXPENSE_GROUPS:
            add_group(key)

        total_expenses = self._combine(group_balances, additions=self._OPERATING_EXPENSE_GROUPS)
        lines.append((0, self._total_line(report, options, "total_expenses", "Total Expenses", total_expenses)))

        ebitda = defaultdict(float, net_operating_revenue)
        for column_group_key, value in total_expenses.items():
            ebitda[column_group_key] -= value
        lines.append((0, self._total_line(report, options, "ebitda", "EBITDA", ebitda)))

        add_group("depreciation")
        ebit = defaultdict(float, ebitda)
        for column_group_key, value in group_balances["depreciation"].items():
            ebit[column_group_key] -= value
        lines.append((0, self._total_line(report, options, "ebit", "EBIT", ebit)))

        add_group("interest_income")
        add_group("finance_expenses")
        earnings_before_tax = defaultdict(float, ebit)
        for column_group_key, value in group_balances["interest_income"].items():
            earnings_before_tax[column_group_key] += value
        for column_group_key, value in group_balances["finance_expenses"].items():
            earnings_before_tax[column_group_key] -= value
        lines.append((0, self._total_line(
            report, options, "earnings_before_tax", "Earnings Before Tax", earnings_before_tax,
        )))

        add_group("income_tax")
        earnings_after_tax = defaultdict(float, earnings_before_tax)
        for column_group_key, value in group_balances["income_tax"].items():
            earnings_after_tax[column_group_key] -= value
        lines.append((0, self._total_line(
            report, options, "earnings_after_tax", "Earnings After Tax", earnings_after_tax,
        )))

        return lines
