from __future__ import annotations

import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from config import config
from database.repo_cells import list_all_cells, list_cell_partners
from database.repo_directions import list_directions
from database.repo_misc import list_all_mock_results
from database.repo_tasks import list_all_tasks_for_partner
from database.repo_users import list_all_users
from utils.timez import now_tz

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def _style_header(ws, row_idx: int = 1) -> None:
    for cell in ws[row_idx]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _autosize(ws) -> None:
    for col_cells in ws.columns:
        length = max((len(str(c.value)) if c.value is not None else 0) for c in col_cells)
        col_letter = get_column_letter(col_cells[0].column)
        ws.column_dimensions[col_letter].width = min(max(length + 2, 10), 45)


async def build_monthly_report() -> str:
    os.makedirs(config.export_dir, exist_ok=True)
    wb = Workbook()

    ws_overall = wb.active
    ws_overall.title = "Umumiy KPI"
    await _fill_overall(ws_overall)

    ws_track = wb.create_sheet("Yo'nalishlar bo'yicha")
    await _fill_track_breakdown(ws_track)

    ws_cells = wb.create_sheet("Hujayralar bajarilishi")
    await _fill_cell_completion(ws_cells)

    ws_mock = wb.create_sheet("Mock natijalar")
    await _fill_mock_trajectories(ws_mock)

    ws_mock_summary = wb.create_sheet("Mock — yo'nalish bo'yicha")
    await _fill_mock_summary_by_direction(ws_mock_summary)

    filename = f"ufq_hisobot_{now_tz().strftime('%Y_%m_%d_%H%M')}.xlsx"
    path = os.path.join(config.export_dir, filename)
    wb.save(path)
    return path


async def _fill_overall(ws) -> None:
    users = await list_all_users()
    ws.append(["To'liq ism", "Username", "Faol vazifalar", "Bajarilgan", "Bajarilmagan", "Bajarish %"])
    _style_header(ws)
    for u in users:
        tasks = await list_all_tasks_for_partner(u["telegram_id"])
        total = len(tasks)
        done = sum(1 for t in tasks if t["my_status"] == "bajardi")
        failed = sum(1 for t in tasks if t["my_status"] == "bajarmadi")
        pct = round((done / total * 100), 1) if total else 0
        ws.append([u["full_name"], u["username"] or "—", total, done, failed, pct])
    _autosize(ws)


async def _fill_track_breakdown(ws) -> None:
    directions = await list_directions()
    ws.append(["Yo'nalish", "Holat", "Hujayralar soni"])
    _style_header(ws)
    cells = await list_all_cells()
    for d in directions:
        count = sum(1 for c in cells if c["direction_id"] == d["id"])
        ws.append([d["name"], "Faol" if d["is_active"] else "Faol emas", count])
    _autosize(ws)


async def _fill_cell_completion(ws) -> None:
    ws.append(["Yo'nalish", "Mentor", "Partner", "Faol vazifalar", "Bajarilgan", "Bajarish %"])
    _style_header(ws)
    cells = await list_all_cells()
    for c in cells:
        partners = await list_cell_partners(c["id"])
        for p in partners:
            tasks = await list_all_tasks_for_partner(p["telegram_id"])
            total = len(tasks)
            done = sum(1 for t in tasks if t["my_status"] == "bajardi")
            pct = round((done / total * 100), 1) if total else 0
            ws.append([c["direction_name"], c["mentor_name"], p["full_name"], total, done, pct])
    _autosize(ws)


async def _fill_mock_trajectories(ws) -> None:
    ws.append(["To'liq ism", "Yo'nalish", "Ball", "Sana"])
    _style_header(ws)
    results = await list_all_mock_results()
    for r in results:
        ws.append([r["full_name"], r["direction_name"], r["score"], r["date"]])
    _autosize(ws)


async def _fill_mock_summary_by_direction(ws) -> None:
    """Per-direction mock averages. Kept as its own sheet, grouped strictly by
    direction_id, so IELTS (0-9 scale) and SAT (400-1600 scale) scores are
    never averaged together into one meaningless number.
    """
    ws.append(["Yo'nalish", "Urinishlar soni", "O'rtacha ball", "Eng yuqori", "Eng past"])
    _style_header(ws)
    results = await list_all_mock_results()
    by_direction: dict[str, list[float]] = {}
    for r in results:
        by_direction.setdefault(r["direction_name"], []).append(r["score"])
    for direction_name, scores in sorted(by_direction.items()):
        avg = round(sum(scores) / len(scores), 2) if scores else 0.0
        ws.append([direction_name, len(scores), avg, max(scores) if scores else "—", min(scores) if scores else "—"])
    _autosize(ws)
