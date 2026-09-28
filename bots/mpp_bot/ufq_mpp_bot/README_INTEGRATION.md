# UFQ MPP Bot v2 patch — integration guide

## File placement
Copy each file to the matching path in your existing `ufq_mpp_bot/` project,
overwriting nothing except files with the exact same name that this patch
itself created earlier (repo_v2.py / repo_quotas.py, if you're re-applying
an update).

    patch_and_update.py          -> ufq_mpp_bot/patch_and_update.py
    database/repo_v2.py          -> ufq_mpp_bot/database/repo_v2.py
    database/repo_quotas.py      -> ufq_mpp_bot/database/repo_quotas.py
    handlers/v2_panels.py        -> ufq_mpp_bot/handlers/v2_panels.py
    keyboards/dynamic_menu.py    -> ufq_mpp_bot/keyboards/dynamic_menu.py

## 1. Run the migration once
    cd ufq_mpp_bot
    python3 patch_and_update.py          # uses config.py's DB_PATH
    # or: python3 patch_and_update.py path/to/your.db

It backs up your DB file first (timestamped .backup_* copy), then adds the
new tables/columns/triggers. Safe to re-run — every step is guarded and
skips anything already applied.

## 2. Register the new router in bot.py
Add `v2_panels` to the handlers import:

    from handlers import (
        admin_directions,
        admin_manage,
        admin_mentor,
        common,
        mentor_mock,
        mentor_partners,
        mentor_tasks,
        partner_status,
        v2_panels,
    )

And include its router, after the existing ones:

    dp.include_router(partner_status.router)
    dp.include_router(v2_panels.router)

## 3. Restart the bot
    python3 bot.py

Try `/v2menu` (or `/start`, which still shows the v1 menus) to see the new
role-based main menu with 🌐 Guruhlar va Reyting / 📚 O'qish paneli /
🎓 Mentor paneli / 👑 Admin paneli.

## What this patch does NOT touch
tasks, submissions, mock_results, cell_members, the existing 3-partner-per
-cell trigger, and every v1 handler file continue to work exactly as
before. v2 is additive: new tables, new triggers (per-user cross-cell
quota: max 2 cells as partner, 1 as mentor), new panels.

## Known incompleteness (see chat for full detail)
- Admin v2 buttons for cell opening / cell management / monthly Excel
  currently point the admin back to the existing v1 buttons rather than
  reimplementing those flows natively — those v1 flows already work.
- Two separate mock-entry paths now exist: v1's "🎯 Mock kiritish"
  (writes to mock_results) and v2's "🎯 Mock boshqaruvi" (writes to
  mock_exams/mock_scores). They are independent tables and do not sync.
- Verified by execution: DB migration idempotency, trigger behavior (old
  and new), FK integrity, all new repo SQL paths, aiogram's real
  @router.error() signature. NOT verified: full aiogram runtime (no
  network access to install aiogram in the sandbox this was built in) —
  test against a real bot token before production use.
