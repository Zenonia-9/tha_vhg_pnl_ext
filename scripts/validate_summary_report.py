company = env["res.company"].search([
    ("name", "ilike", "THUKHA SAYTANAR CO. Ltd"),
], limit=1)
report = env.ref("tha_vhg_pnl_ext.report_vhg_profit_and_loss_summary").with_company(company).with_context(
    allowed_company_ids=[company.id]
)
budget = env["account.report.budget"].sudo().with_company(company).search([
    ("name", "=", "VHG Summary Demo Budget JUL 26"),
], limit=1)
assert budget, "Demo budget is missing"
fy_budget = env["account.report.budget"].sudo().with_company(company).search([
    ("name", "=", "VHG Summary Demo Budget FY2026-27"),
], limit=1)
assert fy_budget and len(fy_budget.item_ids) == 2832

base_previous = {
    "date": {
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
        "filter": "custom",
        "mode": "range",
    },
}
no_budget_options = report.get_options(base_previous)
no_budget_lines = report._get_lines(no_budget_options)
assert "vhg_hide_zero_months" not in no_budget_options
assert [column["name"] for column in no_budget_options["columns"][:9]] == [
    "Actual", "%", "Budget", "%", "Variance", "%", "No.", "Actual", "%",
]
assert len(no_budget_lines) == 26, len(no_budget_lines)
assert all(not line.get("unfoldable") for line in no_budget_lines)
assert all(not line.get("expand_function") for line in no_budget_lines)
number_cells = [line["columns"][6]["no_format"] for line in no_budget_lines]
assert [number for number in number_cells if number] == [str(number) for number in range(1, 18)]
assert not no_budget_options["filters"]["show_period_comparison"]
assert not no_budget_options["filters"]["show_all"]
assert no_budget_options["vhg_summary_ytd_month_keys"] == [
    "actual_2026_04", "actual_2026_05", "actual_2026_06", "actual_2026_07",
]
assert no_budget_options["vhg_summary_month_keys"] == [
    f"actual_{year}_{month:02d}"
    for year, month in [(2026, month) for month in range(4, 13)] + [(2027, month) for month in range(1, 4)]
]
budget_labels = {"mtd_budget", "mtd_budget_percent", "mtd_variance", "mtd_variance_percent", "fy_budget", "fy_budget_percent", "fy_variance", "fy_variance_percent"}
for line in no_budget_lines:
    for column, cell in zip(no_budget_options["columns"], line["columns"]):
        if column["expression_label"] in budget_labels:
            assert cell["no_format"] is None

budget_previous = dict(base_previous)
budget_previous["budgets"] = [{"id": budget.id, "selected": True}]
budget_options = report.get_options(budget_previous)
budget_lines = report._get_lines(budget_options)
assert len(budget_lines) == 26
assert len(budget.item_ids) == 236
assert any(
    cell.get("no_format")
    for line in budget_lines
    for column, cell in zip(budget_options["columns"], line["columns"])
    if column["expression_label"] == "mtd_budget"
)

hidden_options = report.get_options({
    **budget_previous,
    "vhg_show_monthly_columns": False,
})
assert not any(column["expression_label"].startswith("month_") for column in hidden_options["columns"])

xlsx = report.export_to_xlsx(budget_options)
assert len(xlsx["file_content"]) > 1000
from io import BytesIO
from zipfile import ZipFile
with ZipFile(BytesIO(xlsx["file_content"])) as workbook:
    worksheet_xml = workbook.read("xl/worksheets/sheet1.xml")
    for merged_range in (b'A1:F1', b'G1:G2', b'H1:H2', b'I1:J1', b'K1:V1', b'W1:Z1'):
        assert merged_range in worksheet_xml, merged_range
pdf = report.export_to_pdf(budget_options)
assert len(pdf["file_content"]) > 1000

print({
    "report_id": report.id,
    "line_count": len(budget_lines),
    "columns_with_months": len(budget_options["columns"]) + 1,
    "columns_without_months": len(hidden_options["columns"]) + 1,
    "xlsx_bytes": len(xlsx["file_content"]),
    "pdf_bytes": len(pdf["file_content"]),
    "first_line": budget_lines[0]["name"],
    "last_line": budget_lines[-1]["name"],
})
