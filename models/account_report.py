# -*- coding: utf-8 -*-

from odoo import models


class AccountReport(models.Model):
    _inherit = "account.report"

    def _init_options_horizontal_groups(self, options, previous_options):
        super()._init_options_horizontal_groups(options, previous_options)
        notes_report = self.env.ref(
            "tha_vhg_pnl_ext.report_vhg_profit_and_loss", raise_if_not_found=False
        )
        source_report = self.env.ref("account_reports.profit_and_loss", raise_if_not_found=False)
        if self != notes_report or not source_report:
            return

        horizontal_groups = source_report.horizontal_group_ids
        options["available_horizontal_groups"] = [
            {"id": horizontal_group.id, "name": horizontal_group.name}
            for horizontal_group in horizontal_groups
        ]
        previous_selected = previous_options.get("selected_horizontal_group_id")
        options["selected_horizontal_group_id"] = (
            previous_selected if previous_selected in horizontal_groups.ids else None
        )

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        summary_report = self.env.ref(
            "tha_vhg_pnl_ext.report_vhg_profit_and_loss_summary", raise_if_not_found=False
        )
        if self != summary_report:
            return super()._inject_report_into_xlsx_sheet(options, workbook, sheet)

        print_options = self.get_options({**options, "export_mode": "file"})
        lines = self._get_lines(print_options)
        header = workbook.add_format({
            "bold": True, "border": 1, "align": "center", "valign": "vcenter",
            "bg_color": "#FFF2CC",
        })
        text = workbook.add_format({"border": 1})
        total_text = workbook.add_format({"border": 1, "bold": True})
        number = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        total_number = workbook.add_format({"border": 1, "bold": True, "num_format": "#,##0.00"})
        percentage = workbook.add_format({"border": 1, "num_format": "0.00%"})
        total_percentage = workbook.add_format({"border": 1, "bold": True, "num_format": "0.00%"})

        columns = print_options["columns"]
        month_count = len(columns) - 13
        sheet.merge_range(0, 0, 0, 5, print_options["vhg_summary_mtd_label"], header)
        sheet.merge_range(0, 6, 1, 6, "No.", header)
        sheet.merge_range(0, 7, 1, 7, "Particular", header)
        sheet.merge_range(0, 8, 0, 9, print_options["vhg_summary_ytd_actual_label"], header)
        if month_count:
            sheet.merge_range(0, 10, 0, 9 + month_count, "Monthly Actual", header)
        ytd_budget_start = 10 + month_count
        sheet.merge_range(
            0,
            ytd_budget_start,
            0,
            ytd_budget_start + 3,
            print_options["vhg_summary_ytd_budget_label"],
            header,
        )
        subheaders = columns[:6] + columns[7:]
        subheader_positions = list(range(6)) + list(range(8, 8 + len(columns) - 7))
        for x, column in zip(subheader_positions, subheaders):
            sheet.write(1, x, column["name"], header)
        labels = columns[:7] + [{"name": "Particular"}] + columns[7:]
        sheet.set_column(0, len(labels) - 1, 14)
        sheet.set_column(7, 7, 34)

        for y, line in enumerate(lines, start=2):
            is_total = line.get("level") == 0
            values = line["columns"][:7] + [{"no_format": line["name"], "figure_type": "string"}] + line["columns"][7:]
            for x, cell in enumerate(values):
                value = cell.get("no_format")
                figure_type = cell.get("figure_type")
                if figure_type == "percentage" and value is not None:
                    value /= 100.0
                    cell_format = total_percentage if is_total else percentage
                elif isinstance(value, (int, float)):
                    cell_format = total_number if is_total else number
                else:
                    cell_format = total_text if is_total else text
                sheet.write(y, x, value if value is not None else "", cell_format)
