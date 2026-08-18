company = env["res.company"].browse(5)
report = env.ref("tha_vhg_pnl_ext.report_vhg_profit_and_loss").with_company(company).with_context(
    allowed_company_ids=[company.id]
)
budget = env["account.report.budget"].sudo().with_company(company).search([
    ("name", "=", "VHG Summary Demo Budget JUL 26"),
], limit=1)
assert budget

options = report.get_options({
    "date": {
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
        "filter": "custom",
        "mode": "range",
    },
    "comparison": {"filter": "previous_period", "number_period": 1},
    "budgets": [{"id": budget.id, "selected": True}],
})
lines = report._get_lines(options)

# The VHG_* lines are a public cross_report contract.  They deliberately stay
# out of the rendered Notes report, whose dynamic rows remain the display
# source of truth.
reference_lines = report.line_ids.filtered(lambda line: (line.code or "").startswith("VHG_"))
assert len(reference_lines) == 28
balance_sheet_report = env.ref("tha_vhg_bs_ext.report_vhg_balance_sheet_notes", raise_if_not_found=False)
if balance_sheet_report:
    cross_report_method = balance_sheet_report._get_custom_report_function(
        "_report_custom_engine_vhg_pnl_reference", "custom_engine"
    )
    assert cross_report_method
assert sum(line["name"] == "Total Revenue" for line in lines) == 1

line_names = [line["name"] for line in lines]
group_names = [
    line["name"] for line in lines
    if line.get("level") == 1 and line.get("unfoldable")
]
assert group_names[:3] == [
    "Inpatient (Revenue)", "Outpatient (Revenue)", "Other (EOPD, Day care)",
]
assert "Direct Cost" in group_names
assert all("By F&A" not in name for name in group_names)
assert group_names.index("Sales & Marketing") < group_names.index("Commission Expense")
assert group_names.index("Commission Expense") < group_names.index("Taxes")

assert len(options["columns"]) == 12
assert sum(header.get("colspan", 1) for header in options["column_headers"][0]) == 12
assert [header["name"] for header in options["column_headers"][0]] == [
    "Jun - Jul Total", "Jul 2026", "Jun 2026",
]
assert [header["colspan"] for header in options["column_headers"][0]] == [4, 4, 4]
assert all(len(line["columns"]) == 12 for line in lines)
assert options["columns"][0]["name"] == "%"
assert options["columns"][0]["figure_type"] == "percentage"
assert options["columns"][1]["name"] == "Actual"
assert options["columns"][2]["name"] == "Budget"
assert options["columns"][3]["name"] == "%"
assert options["columns"][5]["name"] == "Actual"
assert options["columns"][6]["name"] == "Budget"
assert options["columns"][7]["name"] == "%"
assert len(options["vhg_notes_header_rows"]) == 2
assert [header["name"] for header in options["vhg_notes_header_rows"][1]] == [
    "", "Amount", "", "Amount", "", "Amount",
]
assert sum(header["colspan"] for header in options["vhg_notes_header_rows"][1]) == 12

outpatient = next(line for line in lines if line["name"] == "Outpatient (Revenue)")
assert outpatient["columns"][1]["no_format"] == (
    outpatient["columns"][5]["no_format"] + outpatient["columns"][9]["no_format"]
)
assert outpatient["columns"][7]["name"].endswith("%")
assert outpatient["columns"][7]["name"] != outpatient["columns"][5]["name"]

total_revenue = next(line for line in lines if line["name"] == "Total Revenue")
actual_balance_column_group = options["columns"][5]["column_group_key"]
reference_totals = report._compute_expression_totals_for_each_column_group(
    reference_lines.expression_ids,
    options,
    col_groups_restrict=[actual_balance_column_group],
)
reference_total_revenue = reference_lines.filtered(
    lambda line: line.code == "VHG_TOTAL_REVENUE"
).expression_ids
assert reference_totals[actual_balance_column_group][reference_total_revenue]["value"] == (
    total_revenue["columns"][5]["no_format"]
)

unfolded_options = report.get_options({
    "date": options["date"],
    "comparison": {"filter": "previous_period", "number_period": 1},
    "budgets": [{"id": budget.id, "selected": True}],
})
unfolded_options["unfold_all"] = True
unfolded_lines = report._get_lines(unfolded_options)
bone_dxa = next(line for line in unfolded_lines if line["name"] == "500010 Bone Dxa Income")
commission = next(line for line in unfolded_lines if line["name"] == "704010 Commission Expenses")
bank_charges = next(line for line in unfolded_lines if line["name"] == "702270 Bank charges")
fx_losses = next(line for line in unfolded_lines if line["name"] == "702260 Foreign exchange losses")
operating_cost_account = next(line for line in unfolded_lines if line["name"].startswith("700225 "))
commission_parent = next(line for line in unfolded_lines if line["id"] == commission["parent_id"])
bank_parent = next(line for line in unfolded_lines if line["id"] == bank_charges["parent_id"])
fx_parent = next(line for line in unfolded_lines if line["id"] == fx_losses["parent_id"])
operating_cost_account_parent = next(
    line for line in unfolded_lines if line["id"] == operating_cost_account["parent_id"]
)
assert commission_parent["name"] == "Commission Expense"
assert bank_parent["name"] == "Finance Expenses"
assert fx_parent["name"] == "Operating Cost"
assert operating_cost_account_parent["name"] == "Operating Cost"
expected_budget_percentage = report._compute_column_percent_comparison_data(
    unfolded_options,
    bone_dxa["columns"][5]["no_format"],
    bone_dxa["columns"][6]["no_format"],
    green_on_positive=env["tha.vhg.pnl.report.handler"]._green_on_positive_for_budget("outpatient"),
)
assert bone_dxa["columns"][7]["name"] == expected_budget_percentage["name"]
assert bone_dxa["columns"][7]["comparison_mode"] == expected_budget_percentage["mode"]
assert bone_dxa["columns"][7]["figure_type"] == "string"
assert bone_dxa["columns"][5]["green_on_positive"] is True
assert bone_dxa["columns"][7]["comparison_mode"] == env["tha.vhg.pnl.report.handler"]._budget_comparison_mode(
    bone_dxa["columns"][5]["no_format"], bone_dxa["columns"][6]["no_format"], True,
    bone_dxa["columns"][7]["comparison_mode"],
)

commission_budget_percentage = commission["columns"][7]
assert commission["columns"][5]["green_on_positive"] is False
assert commission_budget_percentage["comparison_mode"] == env["tha.vhg.pnl.report.handler"]._budget_comparison_mode(
    commission["columns"][5]["no_format"], commission["columns"][6]["no_format"], False,
    commission_budget_percentage["comparison_mode"],
)
assert bone_dxa["columns"][0]["name"].endswith("%")
assert bone_dxa["columns"][4]["name"].endswith("%")
assert bone_dxa["columns"][8]["name"].endswith("%")

million_options = report.get_options({
    "date": options["date"],
    "comparison": {"filter": "previous_period", "number_period": 1},
    "budgets": [{"id": budget.id, "selected": True}],
    "rounding_unit": "millions",
})
million_lines = report._get_lines(million_options)
million_outpatient = next(line for line in million_lines if line["name"] == "Outpatient (Revenue)")
assert million_outpatient["columns"][4]["name"] == outpatient["columns"][4]["name"]
assert million_outpatient["columns"][7]["name"] == outpatient["columns"][7]["name"]

taxes = next(line for line in lines if line["name"] == "Taxes")
total_expenses = next(line for line in lines if line["name"] == "Total Expenses")
assert lines.index(taxes) < lines.index(total_expenses)

horizontal_group_id = options["available_horizontal_groups"][0]["id"]
horizontal_options = report.get_options({
    "date": options["date"],
    "selected_horizontal_group_id": horizontal_group_id,
})
horizontal_lines = report._get_lines(horizontal_options)
assert horizontal_options["selected_horizontal_group_id"] == horizontal_group_id
assert len(horizontal_options["vhg_notes_header_rows"]) == 2
assert sum(
    header["colspan"] for header in horizontal_options["vhg_notes_header_rows"][0]
) == len(horizontal_options["columns"])
assert all(
    len(line["columns"]) == len(horizontal_options["columns"])
    for line in horizontal_lines
)

xlsx = report.export_to_xlsx(options)
pdf = report.export_to_pdf(options)
assert len(xlsx["file_content"]) > 1000
assert len(pdf["file_content"]) > 1000

native_xlsx_options = report.get_options({
    "date": options["date"],
    "comparison": {"filter": "previous_period", "number_period": 1},
    "budgets": [{"id": budget.id, "selected": True}],
    "export_mode": "file",
    "unfold_all": True,
    "vhg_notes_native_xlsx": True,
})
native_xlsx_options["unfold_all"] = True
native_xlsx_options["vhg_notes_native_xlsx"] = True
native_xlsx_lines = report._get_lines(native_xlsx_options)
inpatient_header = next(
    line for line in native_xlsx_lines if line["name"] == "Inpatient (Revenue)"
)
native_bone_dxa = next(
    line for line in native_xlsx_lines if line["name"] == "500010 Bone Dxa Income"
)
assert all(not column["name"] for column in inpatient_header["columns"])
assert native_bone_dxa["columns"][0]["name"].endswith("%")
assert native_bone_dxa["columns"][4]["name"].endswith("%")

options_without_budget = report.get_options({
    "date": {
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
        "filter": "custom",
        "mode": "range",
    },
    "comparison": {"filter": "previous_period", "number_period": 1},
    "budgets": [],
})
lines_without_budget = report._get_lines(options_without_budget)
assert len(options_without_budget["columns"]) == 6
assert sum(
    header.get("colspan", 1)
    for header in options_without_budget["column_headers"][0]
) == 6
assert all(len(line["columns"]) == 6 for line in lines_without_budget)
assert all(column["name"] != "Balance" for column in options_without_budget["columns"])

handler = env["tha.vhg.pnl.report.handler"]
percentage_test_balances = {
    "inpatient": {"current": 120.0},
    "outpatient": {"current": 80.0},
    "eopd_day_care": {"current": 20.0},
    "other_hospital_revenue": {"current": 30.0},
    "non_hospital_revenue": {"current": 10.0},
    "rental_complex": {"current": 40.0},
    "direct_cost": {"current": 50.0},
}
ebitda_balances = {"current": 100.0}
# EBITDA % uses Total Net Revenues: (120 + 80 + 20 + 30 + 10 + 40 - 50).
assert handler._actual_percent(
    "ebitda", ebitda_balances, percentage_test_balances, "current"
) == 40.0
assert handler._period_total_percent(
    "ebitda",
    ebitda_balances,
    percentage_test_balances,
    {"vhg_period_total_balance_column_group_keys": ("current",)},
) == 40.0
assert handler._budget_comparison_mode(0.0, 100.0, True, "green") == "red"
assert handler._budget_comparison_mode(0.0, 100.0, False, "red") == "green"
assert handler._budget_comparison_name({"name": "n/a", "mode": "muted"}) == ""

print({
    "columns": len(options["columns"]),
    "header_colspan": sum(header.get("colspan", 1) for header in options["column_headers"][0]),
    "headers": [(header["name"], header["colspan"]) for header in options["column_headers"][0]],
    "outpatient_period_total": outpatient["columns"][1]["no_format"],
    "bone_dxa_budget_percentage": bone_dxa["columns"][5]["name"],
    "columns_without_budget": len(options_without_budget["columns"]),
    "xlsx_bytes": len(xlsx["file_content"]),
    "pdf_bytes": len(pdf["file_content"]),
})
