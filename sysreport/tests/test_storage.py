from __future__ import annotations

from sysreport.storage import format_drive, list_drives


def test_list_drives_reports_free_percent(fake_disk):
    drives = list_drives()
    assert len(drives) == 1
    assert drives[0].mountpoint == "C:\\"
    assert drives[0].free == 20_000_000_000
    assert drives[0].free_percent == 20.0


def test_list_drives_skips_entries_without_fstype(monkeypatch):
    from collections import namedtuple

    Part = namedtuple("Part", ["device", "mountpoint", "fstype", "opts"])
    monkeypatch.setattr("psutil.disk_partitions", lambda all=False: [Part("D:\\", "D:\\", "", "cdrom")])

    assert list_drives() == []


def test_format_drive_includes_human_size_and_percent(fake_disk):
    drives = list_drives()
    text = format_drive(drives[0])
    assert "C:\\" in text
    assert "20%" in text
