"""Run with odoo shell: verify zero sections and subtotals in generated XLSX."""

from copy import deepcopy
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile


def workbook_texts(content):
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(BytesIO(content)) as workbook:
        strings = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
        shared_strings = [
            "".join(node.itertext()) for node in strings.findall("s:si", namespace)
        ]
        sheet = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        return {
            shared_strings[int(cell.find("s:v", namespace).text)]
            for cell in sheet.findall(".//s:c[@t='s']", namespace)
        }


report = env.ref("tha_vhg_pnl_ext.report_vhg_profit_and_loss")
number_types = {"integer", "float", "monetary", "percentage"}

# This period has no accounting activity: every section header should hide,
# along with their section subtotals. Main report totals must remain.
previous_options = {
    "date": {
        "date_from": "1900-01-01",
        "date_to": "1900-01-31",
        "filter": "custom",
        "mode": "range",
    },
    "unfold_all": True,
    "hide_0_lines": False,
}
for comparison in ({"filter": "no_comparison"}, {"filter": "previous_period", "number_period": 1}):
    options = report.get_options({**previous_options, "comparison": comparison, "export_mode": "file"})
    lines = report._get_lines(options)
    headers = [line for line in lines if line.get("unfoldable") and line.get("level") == 1]
    totals = [line for line in lines if line.get("level") == 0]
    subtotals = [line for line in lines if "|total~~" in line["id"]]
    assert headers and totals, "Expected section headers and total rows"
    assert all(
        column.get("is_zero", True)
        for line in lines for column in line["columns"]
        if column.get("figure_type") in number_types
    ), "Choose an empty period for this regression check"

    shown = workbook_texts(report.export_to_xlsx(deepcopy(options))["file_content"])
    hidden = workbook_texts(report.export_to_xlsx({**deepcopy(options), "hide_0_lines": True})["file_content"])
    for header in headers:
        assert header["name"] in shown, f"Missing header with the filter disabled: {header['name']}"
        assert header["name"] not in hidden, f"Zero section header still exported: {header['name']}"
    for total in totals:
        assert total["name"] in hidden, f"Total row should remain: {total['name']}"
    for subtotal in subtotals:
        assert subtotal["name"] in shown, f"Missing subtotal with the filter disabled: {subtotal['name']}"
        assert subtotal["name"] not in hidden, f"Hidden section subtotal still exported: {subtotal['name']}"
    print("XLSX_ZERO_SECTIONS_OK", comparison["filter"], len(headers), "headers and", len(subtotals), "subtotals hidden;", len(totals), "report totals retained", flush=True)

# A section whose details offset to zero still needs its header when a child
# is nonzero. A zero detail must hide even when the surrounding rows are bold.
parent_id = report._get_generic_line_id(None, None, markup="tha_zero_section")
nonzero_parent_id = report._get_generic_line_id(None, None, markup="tha_offset_section")
zero_column = {"figure_type": "monetary", "no_format": 0.0, "is_zero": True}
nonzero_column = {"figure_type": "monetary", "no_format": 10.0, "is_zero": False}
fixture_lines = [
    {"id": parent_id, "class": "fw-bold", "level": 1, "columns": [zero_column]},
    {"id": parent_id + "|detail~~", "parent_id": parent_id, "level": 2, "columns": [zero_column]},
    {"id": parent_id + "|total~~", "parent_id": parent_id, "class": "fw-bold", "level": 1, "columns": [zero_column]},
    {"id": nonzero_parent_id, "class": "fw-bold", "level": 1, "columns": [zero_column]},
    {"id": nonzero_parent_id + "|detail~~", "parent_id": nonzero_parent_id, "level": 2, "columns": [nonzero_column]},
    {"id": nonzero_parent_id + "|total~~", "parent_id": nonzero_parent_id, "class": "fw-bold", "level": 1, "columns": [zero_column]},
    {"id": "tha_report_total", "class": "fw-bold", "level": 0, "columns": [zero_column]},
]
for target in (report, env.ref("tha_vhg_pnl_ext.report_vhg_profit_and_loss_summary")):
    assert [line["id"] for line in target._filter_out_0_lines(fixture_lines)] == [
        nonzero_parent_id, nonzero_parent_id + "|detail~~", nonzero_parent_id + "|total~~", "tha_report_total",
    ]
print("ZERO_DETAIL_AND_VISIBLE_CHILD_OK", flush=True)

# Recheck the mixed August report shown by the user, when this company exists.
company = env["res.company"].search([("name", "ilike", "THUKHA SAYTANAR")], limit=1)
if company:
    mixed_report = report.with_company(company).with_context(allowed_company_ids=company.ids)
    options = mixed_report.get_options({
        **previous_options,
        "date": {**previous_options["date"], "date_from": "2026-08-01", "date_to": "2026-08-31"},
        "export_mode": "file",
    })
    lines = mixed_report._get_lines(options)
    mixed_export = mixed_report.export_to_xlsx({**deepcopy(options), "hide_0_lines": True})
    hidden = workbook_texts(mixed_export["file_content"])
    hidden_count = visible_count = 0
    for header in (line for line in lines if line.get("unfoldable") and line.get("level") == 1):
        section = [header] + [line for line in lines if line.get("parent_id") == header["id"]]
        empty = all(
            column.get("is_zero", True)
            for line in section for column in line["columns"]
            if column.get("figure_type") in number_types
        )
        subtotal = next(line for line in section if "|total~~" in line["id"])
        for line in (header, subtotal):
            assert (line["name"] not in hidden) if empty else (line["name"] in hidden), line["name"]
        hidden_count += empty
        visible_count += not empty
    assert hidden_count and visible_count, "Expected both empty and active sections in August"
    print("AUGUST_XLSX_OK", hidden_count, "empty sections hidden;", visible_count, "active sections retained", flush=True)

env.cr.rollback()
