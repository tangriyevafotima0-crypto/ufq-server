"""
test_monitor.py — storage.py va monitor.py uchun sof-Python testlar.
Telethon shart emas (FakeClient ishlatiladi).
"""

import asyncio
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

from storage import BotState
from monitor import ChannelMonitor, format_opportunity
from parser import parse_post
from matcher import Profile, evaluate


class FakeMsg:
    def __init__(self, id, text, dt):
        self.id = id
        self.text = text
        self.message = text
        self.date = dt


class FakeEntity:
    def __init__(self, id, title):
        self.id = id
        self.title = title


class FakeClient:
    def __init__(self, chan_msgs):
        self.chan_msgs = chan_msgs  # {int_id: [FakeMsg,...] ascending}

    async def iter_messages(self, entity, limit=None, min_id=0, reverse=False, **kw):
        msgs = [m for m in self.chan_msgs[entity.id] if m.id > min_id]
        if not reverse:
            msgs = list(reversed(msgs))
        if limit:
            msgs = msgs[:limit]
        for m in msgs:
            yield m


GOOD_TEXT = (
    "IT sohasida yozgi dastur!\n"
    "Yosh: 15-18 yosh oralig'ida\n"
    "Bepul / to'liq grant\n"
    "Oxirgi muddat: 2099-yil 20-iyun\n"
    "Ariza: https://forms.gle/abc123\n"
)


def _tmp_state() -> BotState:
    return BotState(Path(tempfile.mktemp()))


def test_storage_channel_persistence():
    path = Path(tempfile.mktemp())
    s = BotState(path)
    s.add_channel(-1001111, "Test Kanal")
    s.set_last_seen(-1001111, 500)
    s.save()

    s2 = BotState(path)
    assert s2.watched == {"-1001111": "Test Kanal"}
    assert s2.get_last_seen(-1001111) == 500
    os.unlink(path)


def test_storage_group_flow():
    s = _tmp_state()
    s.add_pending_group(-100222, "Test Guruh")
    assert s.get_group(-100222)["status"] == "pending"
    assert s.pending_group_ids() == [-100222]
    assert s.confirmed_group_ids() == []

    assert s.confirm_group(-100222) is True
    assert s.confirmed_group_ids() == [-100222]
    assert s.pending_group_ids() == []

    assert s.confirm_group(-999) is False   # nonexistent
    assert s.remove_group(-100222) is True
    assert s.remove_group(-100222) is False  # already gone


def test_storage_dedup():
    s = _tmp_state()
    h = "abc123"
    assert not s.is_sent(h)
    s.mark_sent(h)
    assert s.is_sent(h)


def test_monitor_baseline_then_match():
    async def run():
        state = _tmp_state()
        state.add_channel(-1001111, "Fake Channel")
        state.update_setting("min_score", 1)

        msgs = [
            FakeMsg(1, "short", datetime(2025, 1, 1)),
            FakeMsg(2, GOOD_TEXT, datetime(2025, 1, 1)),
        ]
        client = FakeClient({12345: msgs})

        async def fake_resolve(c, t):
            return FakeEntity(12345, "Fake Channel")

        mon = ChannelMonitor(client, state, fake_resolve)

        # First poll: no baseline yet -> just sets last_seen, no matches emitted
        found = await mon.poll_once(lambda o, c: None)
        assert found == 0
        assert state.get_last_seen(-1001111) == 2

        # New matching message arrives
        msgs.append(FakeMsg(3, GOOD_TEXT, datetime(2025, 1, 2)))
        matched = []

        async def on_match(opp, channel_name):
            matched.append((opp.title, channel_name))

        found = await mon.poll_once(on_match)
        assert found == 1
        assert len(matched) == 1
        assert state.get_last_seen(-1001111) == 3

        # Re-poll: nothing new
        found = await mon.poll_once(on_match)
        assert found == 0

    asyncio.run(run())


def test_monitor_channel_crash_does_not_propagate():
    async def run():
        state = _tmp_state()
        state.add_channel(-100111, "Chan A")
        state.add_channel(-100999, "Chan B (broken)")
        state.update_setting("min_score", 1)

        class CrashyClient(FakeClient):
            async def iter_messages(self, entity, limit=None, min_id=0, reverse=False, **kw):
                if entity.id == 999:
                    raise RuntimeError("simulated crash")
                async for m in super().iter_messages(
                    entity, limit=limit, min_id=min_id, reverse=reverse, **kw
                ):
                    yield m

        client = CrashyClient({111: [], 999: []})

        async def fake_resolve(c, t):
            cid = int(t)
            return FakeEntity(111, "Chan A") if cid == -100111 else FakeEntity(999, "Chan B")

        mon = ChannelMonitor(client, state, fake_resolve)
        # Should not raise despite Chan B crashing internally.
        found = await mon.poll_once(lambda o, c: None)
        assert found == 0

    asyncio.run(run())


def test_format_opportunity_no_crash_on_sparse_fields():
    opp = parse_post(
        "IT dasturi, grant, ariza topshirish uchun kanalga yozing",
        date(2025, 1, 1), "Kanal2",
    )
    p = Profile(age=16, interests=["IT"])
    evaluate(opp, p, date(2025, 1, 1))
    text = format_opportunity(opp, "Kanal2")
    assert "Kanal2" in text
    assert "🎯" in text


if __name__ == "__main__":
    test_storage_channel_persistence()
    test_storage_group_flow()
    test_storage_dedup()
    test_monitor_baseline_then_match()
    test_monitor_channel_crash_does_not_propagate()
    test_format_opportunity_no_crash_on_sparse_fields()
    print("ALL TESTS PASSED")
