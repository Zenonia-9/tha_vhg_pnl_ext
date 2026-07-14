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

assert len(options["columns"]) == 8
assert sum(header.get("colspan", 1) for header in options["column_headers"][0]) == 8
assert [header["name"] for header in options["column_headers"][0]] == [
    "Jun - Jul Total", "Actual %", "Jul 2026", "Jun 2026",
]
assert [header["colspan"] for header in options["column_headers"][0]] == [1, 1, 3, 3]
assert all(len(line["columns"]) == 8 for line in lines)
assert options["columns"][4]["name"] == "%"
assert options["columns"][4]["figure_type"] == "percentage"

outpatient = next(line for line in lines if line["name"] == "Outpatient (Revenue)")
assert outpatient["columns"][0]["no_format"] == (
    outpatient["columns"][2]["no_format"] + outpatient["columns"][5]["no_format"]
)
assert outpatient["columns"][4]["name"].endswith("%")
assert outpatient["columns"][4]["name"] != outpatient["columns"][2]["name"]

unfolded_options = report.get_options({
    "date": options["date"],
    "comparison": {"filter": "previous_period", "number_period": 1},
    "budgets": [{"id": budget.id, "selected": True}],
})
unfolded_options["unfold_all"] = True
unfolded_lines = report._get_lines(unfolded_options)
bone_dxa = next(line for line in unfolded_lines if line["name"] == "500010 Bone Dxa Income")
expected_budget_percentage = bone_dxa["columns"][2]["no_format"] * 100.0 / bone_dxa["columns"][3]["no_format"]
assert abs(bone_dxa["columns"][4]["no_format"] - expected_budget_percentage) < 0.000001
assert bone_dxa["columns"][4]["name"].endswith("%")

xlsx = report.export_to_xlsx(options)
pdf = report.export_to_pdf(options)
assert len(xlsx["file_content"]) > 1000
assert len(pdf["file_content"]) > 1000

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
assert len(options_without_budget["columns"]) == 4
assert sum(
    header.get("colspan", 1)
    for header in options_without_budget["column_headers"][0]
) == 4
assert all(len(line["columns"]) == 4 for line in lines_without_budget)

print({
    "columns": len(options["columns"]),
    "header_colspan": sum(header.get("colspan", 1) for header in options["column_headers"][0]),
    "headers": [(header["name"], header["colspan"]) for header in options["column_headers"][0]],
    "outpatient_period_total": outpatient["columns"][0]["no_format"],
    "bone_dxa_budget_percentage": bone_dxa["columns"][4]["name"],
    "columns_without_budget": len(options_without_budget["columns"]),
    "xlsx_bytes": len(xlsx["file_content"]),
    "pdf_bytes": len(pdf["file_content"]),
})
