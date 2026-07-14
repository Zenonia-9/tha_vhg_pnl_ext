# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime

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
            "500065", "500035", "500040", "500075", "500080", "500090",
            "500105", "500110", "500120", "500140", "500155", "500186",
            "500160", "500165", "500170", "500175", "500180", "500187",
        )),
        ("eopd_day_care", "Other (EOPD, Day care)", -1, (
            "500050", "500055", "500146", "500045",
        )),
        ("inpatient", "Inpatient (Revenue)", -1, (
            "500095", "500100", "500150", "500115", "500135",
        )),
        ("direct_cost", "Direct Cost (Doctor Fee + Refer + Reading)", 1, (
            "600010", "600020", "600030", "600035", "600040", "600045", "600180",
        )),
        ("other_hospital_revenue", "Other Hospital Revenue (Partnership Income) By F&A", -1, (
            "510030", "510015", "510000", "510010", "510035",
            "510020", "510025", "500185", "500400", "500405", "500410",
            "500415", "500420", "500425", "500600", "510100", "510105",
            "510110", "510115", "510120",
        )),
        # 510585 Need to Remove
        ("non_hospital_revenue", "Non Hospital Revenue (Rental & Other) By F&A", -1, (
            "510500", "510510", "510515", "510520", "510530", "510535",
            "510540", "510575", "510565", "510545", "510555", "510505",
            "510560", "510570", "510580",
        )),
        ("rental_complex", "Rental Complex Building & BIS By F&A", -1, (
            "510085", "510095", "510125", "510130",
        )),
        ("cost_of_goods_sold", "Cost of Goods Sold", 1, (
            "600050", "600060", "600070", "600080", "600090", "600100",
            "600110", "600120", "600130", "600140", "600150", "600170",
            "600160", "600190", "600200", "600210", "600220", "600181", "600182",
            "600183", "600184", "600185", "600186",
        )),
        # 702316 Need to Remove
        ("operating_cost", "Operating Cost", 1, (
            "700010", "700020", "700030", "700040", "700050", "700060",
            "700080", "700090", "700100", "700110", "700120", "700130",
            "700140", "700170", "700190", "700070", "700150",
            "700160", "700200", "700210", "700220", "702311", "701150",
            "701160", "701173", "701175", "702315", "703085", "704055",
        )),
        # 703060 Move to Repair & Maintenance
        ("staff_cost", "Staff Cost (Based on Head Count)", 1, (
            "701010", "701030", "701040", "701050", "701060", "701070",
            "701080", "701090", "701100", "701110", "701120", "701130",
            "701140", "701170", "701171", "701172",
        )),
        ("bonus", "Bonus", 1, ("701020",)),
        ("administrative", "Administrative & Other Expenses", 1, (
            "702010", "702020", "702030", "702040", "702050", "702060",
            "702070", "702080", "702090", "702100", "702110", "702120",
            "702130", "702140", "702150", "702160", "702170", "702180",
            "702190", "702200", "702210", "702220", "702230", "702240",
            "702250", "702260", "702270", "702280", "702290", "702300",
            "702310",
        )),
        # 703060 Get from Staff Cost
        ("repair_maintenance", "Repair & Maintenance", 1, (
            "703010", "703020", "703030", "703040", "703050", "703070",
            "703080", "703060",
        )),
        ("sales_marketing", "Sales & Marketing", 1, (
            "704010", "704020", "704030", "704040", "704050",
        )),
        ("taxes", "Taxes", 1, ("707020", "707030", "700180")),
        ("depreciation", "Depreciation & Amortization", 1, (
            "705010", "705020", "705030", "705040", "705050", "705060",
            "705070", "705080", "705090", "705100", "705110", "705120",
            "705130", "705140", "705150", "705160", "705170", "705180", "705111",
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
        "administrative", "repair_maintenance", "sales_marketing", "taxes",
    )

    _SHARED_PERCENTAGE_GROUPS = {
        "outpatient": ("outpatient", "eopd_day_care"),
        "eopd_day_care": ("outpatient", "eopd_day_care"),
        "other_hospital_revenue": (
            "other_hospital_revenue", "non_hospital_revenue", "rental_complex",
        ),
        "non_hospital_revenue": (
            "other_hospital_revenue", "non_hospital_revenue", "rental_complex",
        ),
        "rental_complex": (
            "other_hospital_revenue", "non_hospital_revenue", "rental_complex",
        ),
        "staff_cost": ("staff_cost", "bonus"),
        "bonus": ("staff_cost", "bonus"),
    }

    def _custom_options_initializer(self, report, options, previous_options):
        horizontal_header_names = {}
        for header_level in options.get("column_headers", []):
            for header in header_level:
                horizontal_element = header.get("horizontal_groupby_element")
                if horizontal_element:
                    horizontal_header_names[tuple(sorted(horizontal_element.items()))] = header["name"]

        synthetic_column_group_keys = {
            column_group_key
            for column_group_key, column_group in options["column_groups"].items()
            if column_group.get("forced_options", {}).get("vhg_period_total")
            or column_group.get("forced_options", {}).get("vhg_actual_percent")
        }
        options["columns"] = [
            column
            for column in options["columns"]
            if column["expression_label"] not in ("period_total", "actual_percent")
            and column["column_group_key"] not in synthetic_column_group_keys
        ]
        options["column_groups"] = {
            column_group_key: column_group
            for column_group_key, column_group in options["column_groups"].items()
            if column_group_key not in synthetic_column_group_keys
        }
        multi_comparison = options.get("multi_comparison")
        if isinstance(multi_comparison, dict):
            previous_period_count = (
                int(multi_comparison.get("previous_period_number", 0) or 0)
                if multi_comparison.get("previous_period")
                else 0
            )
        else:
            comparison = options.get("comparison", {})
            previous_period_count = (
                int(comparison.get("number_period", 0) or 0)
                if comparison.get("filter") == "previous_period"
                else 0
            )
        has_previous_period_comparison = previous_period_count > 0
        options["vhg_period_total_enabled"] = has_previous_period_comparison
        period_total_column_group_key = "vhg_period_total"
        period_total_header = ""
        if has_previous_period_comparison:
            period_date_keys = {
                (options["date"]["date_from"], options["date"]["date_to"]),
            }
            previous_period = options["date"]
            for _index in range(previous_period_count):
                previous_period = report._get_shifted_dates_period(options, previous_period, -1)
                period_date_keys.add((previous_period["date_from"], previous_period["date_to"]))

            balance_column_group_keys = [
                column["column_group_key"]
                for column in options["columns"]
                if column["expression_label"] == "balance"
                and not options["column_groups"][column["column_group_key"]]["forced_options"].get("compute_budget")
                and not options["column_groups"][column["column_group_key"]]["forced_options"].get("budget_percentage")
                and (
                    options["column_groups"][column["column_group_key"]]["forced_options"]["date"]["date_from"],
                    options["column_groups"][column["column_group_key"]]["forced_options"]["date"]["date_to"],
                ) in period_date_keys
            ]
            period_dates = [
                options["column_groups"][column_group_key]["forced_options"]["date"]
                for column_group_key in balance_column_group_keys
            ]
            period_total_header = self._period_total_header(period_dates)
            options["vhg_period_total_balance_column_group_keys"] = balance_column_group_keys
            options["vhg_period_total_column_group_key"] = period_total_column_group_key

        native_columns = list(options["columns"])
        native_column_groups = options["column_groups"]
        column_groups = {}
        columns = []
        actual_percent_column_groups = {}
        if has_previous_period_comparison:
            column_groups[period_total_column_group_key] = {
                "forced_options": {"vhg_period_total": True},
                "forced_domain": [],
            }
            columns.append({
                "name": "Balance",
                "column_group_key": period_total_column_group_key,
                "expression_label": "period_total",
                "sortable": False,
                "figure_type": "monetary",
                "blank_if_zero": False,
            })

        for column in native_columns:
            column_group_key = column["column_group_key"]
            column_group = native_column_groups[column_group_key]
            forced_options = column_group["forced_options"]
            is_actual_balance = (
                column["expression_label"] == "balance"
                and not forced_options.get("compute_budget")
                and not forced_options.get("budget_percentage")
            )
            if is_actual_balance:
                actual_percent_column_group_key = f"vhg_actual_percent_{len(actual_percent_column_groups)}"
                actual_percent_column_groups[actual_percent_column_group_key] = column_group_key
                percent_column_group = {
                    "forced_options": {
                        "date": dict(forced_options.get("date", {})),
                        "vhg_actual_percent": column_group_key,
                    },
                    "forced_domain": [],
                }
                if column_group.get("horizontal_groupby_element"):
                    percent_column_group["horizontal_groupby_element"] = column_group["horizontal_groupby_element"]
                column_groups[actual_percent_column_group_key] = percent_column_group
                columns.append({
                    "name": "%",
                    "column_group_key": actual_percent_column_group_key,
                    "expression_label": "actual_percent",
                    "sortable": False,
                    "figure_type": "percentage",
                    "blank_if_zero": False,
                    "style": "text-align: center; white-space: nowrap;",
                })
            column_groups[column_group_key] = column_group
            columns.append(column)
        options["column_groups"] = column_groups
        options["columns"] = columns
        options["vhg_actual_percent_column_groups"] = actual_percent_column_groups

        budget_base_column_groups = {}
        budget_column_groups = {}
        budget_percentage_column_groups = {}
        for column_group_key, column_group in options["column_groups"].items():
            forced_options = column_group["forced_options"]
            column_date = forced_options.get("date", {})
            date_key = (column_date.get("date_from"), column_date.get("date_to"))
            if forced_options.get("budget_base"):
                budget_base_column_groups[date_key] = column_group_key
            elif budget_id := forced_options.get("compute_budget"):
                budget_column_groups[(date_key, budget_id)] = column_group_key
            elif budget_id := forced_options.get("budget_percentage"):
                budget_percentage_column_groups[column_group_key] = (
                    budget_base_column_groups.get(date_key),
                    budget_column_groups.get((date_key, budget_id)),
                )
        options["vhg_budget_percentage_column_groups"] = budget_percentage_column_groups

        budget_names = {
            budget["id"]: budget["name"]
            for budget in options.get("budgets", [])
            if budget.get("selected")
        }
        for column in options["columns"]:
            column_group_key = column["column_group_key"]
            if column_group_key == period_total_column_group_key:
                continue
            forced_options = options["column_groups"][column_group_key]["forced_options"]
            if budget_id := forced_options.get("compute_budget"):
                column["name"] = budget_names.get(budget_id, "Budget")
            elif forced_options.get("budget_percentage"):
                column.update({
                    "name": "%",
                    "figure_type": "percentage",
                    "blank_if_zero": False,
                })

        top_headers = []
        if has_previous_period_comparison:
            top_headers.append({"name": period_total_header, "colspan": 1})
        for column in options["columns"]:
            if column["column_group_key"] == period_total_column_group_key:
                continue
            forced_options = options["column_groups"][column["column_group_key"]]["forced_options"]
            column_date = forced_options.get("date", {})
            date_key = (column_date.get("date_from"), column_date.get("date_to"))
            if top_headers and top_headers[-1].get("date_key") == date_key:
                top_headers[-1]["colspan"] += 1
            else:
                top_headers.append({
                    "date_key": date_key,
                    "name": column_date.get("string", ""),
                    "colspan": 1,
                })

        selected_horizontal_group_id = options.get("selected_horizontal_group_id")
        header_rows = [[
            {
                "name": header["name"],
                "colspan": header["colspan"],
                "rowspan": 2 if selected_horizontal_group_id and not header.get("date_key") else 1,
            }
            for header in top_headers
        ]]
        if selected_horizontal_group_id:
            horizontal_headers = []
            for column in options["columns"]:
                if column["column_group_key"] == period_total_column_group_key:
                    continue
                source_column_group_key = actual_percent_column_groups.get(
                    column["column_group_key"], column["column_group_key"]
                )
                column_group = options["column_groups"][source_column_group_key]
                forced_options = column_group["forced_options"]
                horizontal_key = tuple(column_group.get("horizontal_groupby_element", ()))
                if horizontal_key:
                    label = horizontal_header_names.get(horizontal_key, "Actual")
                elif forced_options.get("compute_budget") or forced_options.get("budget_percentage"):
                    label = "Budget"
                else:
                    label = "Actual"
                date_options = forced_options.get("date", {})
                group_key = (date_options.get("date_from"), date_options.get("date_to"), label)
                if horizontal_headers and horizontal_headers[-1]["group_key"] == group_key:
                    horizontal_headers[-1]["colspan"] += 1
                else:
                    horizontal_headers.append({
                        "group_key": group_key,
                        "name": label,
                        "colspan": 1,
                    })
            header_rows.append([
                {"name": header["name"], "colspan": header["colspan"], "rowspan": 1}
                for header in horizontal_headers
            ])

        options["vhg_notes_header_rows"] = header_rows
        options["column_headers"] = [[
            {"name": header["name"], "colspan": header["colspan"]}
            for header in top_headers
        ]]
        options["show_horizontal_group_total"] = False
        options["custom_display_config"].update({
            "templates": {
                "AccountReportHeader": "tha_vhg_pnl_ext.NotesReportHeader",
            },
            "pdf_export": {
                "pdf_export_main_table_header": "tha_vhg_pnl_ext.notes_pdf_header",
            },
        })

    @staticmethod
    def _period_total_header(period_dates):
        dates = [
            (
                datetime.strptime(period["date_from"], "%Y-%m-%d").date(),
                datetime.strptime(period["date_to"], "%Y-%m-%d").date(),
            )
            for period in period_dates
        ]
        start_date = min(date_from for date_from, _date_to in dates)
        end_date = max(date_to for _date_from, date_to in dates)
        if start_date == end_date:
            return f"{end_date:%b %Y} Total"
        if start_date.year == end_date.year:
            return f"{start_date:%b} - {end_date:%b} Total"
        return f"{start_date:%b %Y} - {end_date:%b %Y}"

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
            if (
                column_group_key == options.get("vhg_period_total_column_group_key")
                or column_group_key in options.get("vhg_actual_percent_column_groups", {})
            ):
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

    def _columns(self, report, options, balances, group_key=None, group_balances=None):
        columns = []
        budget_percentage_column_groups = options.get("vhg_budget_percentage_column_groups", {})
        actual_percent_column_groups = options.get("vhg_actual_percent_column_groups", {})
        for column in options["columns"]:
            is_period_total = column["expression_label"] == "period_total"
            is_actual_percent = column["expression_label"] == "actual_percent"
            budget_percentage_group_keys = budget_percentage_column_groups.get(column["column_group_key"])
            value = balances.get(column["column_group_key"], 0.0)
            if is_period_total:
                value = sum(
                    balances.get(column_group_key, 0.0)
                    for column_group_key in options.get("vhg_period_total_balance_column_group_keys", ())
                )
            elif is_actual_percent:
                source_column_group_key = actual_percent_column_groups.get(column["column_group_key"])
                value = (
                    self._actual_percent(
                        group_key,
                        balances,
                        group_balances,
                        source_column_group_key,
                    )
                    if group_key and group_balances and source_column_group_key
                    else None
                )
            elif budget_percentage_group_keys:
                actual_column_group_key, budget_column_group_key = budget_percentage_group_keys
                budget_base_column = next(
                    other_column
                    for other_column in options["columns"]
                    if other_column["column_group_key"] == actual_column_group_key
                )
                comparison = report._compute_column_percent_comparison_data(
                    options,
                    balances.get(actual_column_group_key, 0.0),
                    balances.get(budget_column_group_key, 0.0),
                    green_on_positive=budget_base_column.get("green_on_positive", False),
                )
                columns.append(report._build_column_dict(
                    comparison["name"],
                    {
                        **column,
                        "figure_type": "string",
                        "comparison_mode": comparison["mode"],
                    },
                    options=options,
                ))
                continue
            columns.append(report._build_column_dict(
                value,
                column,
                options=options,
                digits=2 if is_period_total or is_actual_percent else 1,
            ))
        return columns

    def _actual_percent(self, group_key, balances, group_balances, column_group_key):
        denominator_groups = self._SHARED_PERCENTAGE_GROUPS.get(group_key, (group_key,))
        denominator = sum(
            group_balances[denominator_group][column_group_key]
            for denominator_group in denominator_groups
        )
        if not denominator:
            return None

        return balances.get(column_group_key, 0.0) * 100.0 / denominator

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
                group_key=group_key,
                group_balances=group_balances,
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

        for key in ("outpatient", "eopd_day_care", "inpatient"):
            add_group(key)

        total_revenue = self._combine(
            group_balances,
            additions=("outpatient", "eopd_day_care", "inpatient"),
        )
        lines.append((0, self._total_line(report, options, "total_revenue", "Total Revenue", total_revenue)))

        add_group("direct_cost")
        net_revenues = self._combine(
            group_balances,
            additions=("outpatient", "eopd_day_care", "inpatient"),
            deductions=("direct_cost",),
        )
        lines.append((0, self._total_line(report, options, "net_revenues", "Net Revenues", net_revenues)))

        for key in ("other_hospital_revenue", "non_hospital_revenue", "rental_complex"):
            add_group(key)

        net_operating_revenue = self._combine(
            group_balances,
            additions=(
                "outpatient", "eopd_day_care", "inpatient",
                "other_hospital_revenue", "non_hospital_revenue", "rental_complex",
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
