from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.asyncio


async def auth_headers(client, email="analytics@example.com", timezone="UTC"):
    registered = await client.post(
        "/auth/register",
        json={"email": email, "password": "secure-pass", "timezone": timezone},
    )
    assert registered.status_code == 201
    login = await client.post(
        "/auth/login",
        data={"username": email, "password": "secure-pass"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def create_habit(client, headers, payload):
    response = await client.post("/habits", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()


async def add_check_in(client, headers, habit_id, day, value=None):
    body = {"logged_at": f"{day}T12:00:00Z"}
    if value is not None:
        body["value"] = value
    return await client.post(
        f"/habits/{habit_id}/check-ins",
        headers=headers,
        json=body,
    )


async def test_daily_streak_heatmap_and_summary(client):
    headers = await auth_headers(client)
    habit = await create_habit(
        client,
        headers,
        {"name": "Daily", "habit_type": "boolean", "schedule_type": "daily"},
    )
    habit_id = habit["id"]

    for day in ("2026-11-18", "2026-11-19", "2026-11-20"):
        response = await add_check_in(client, headers, habit_id, day)
        assert response.status_code == 201

    streak = await client.get(
        f"/habits/{habit_id}/analytics/streak",
        headers=headers,
    )
    assert streak.status_code == 200
    assert streak.json()["unit"] == "days"
    assert streak.json()["current_streak"] == 3
    assert streak.json()["longest_streak"] >= 3

    heatmap = await client.get(
        f"/habits/{habit_id}/analytics/heatmap",
        params={"from": "2026-11-18", "to": "2026-11-20"},
        headers=headers,
    )
    assert heatmap.status_code == 200
    assert len(heatmap.json()) == 3
    assert all(item["is_completed"] for item in heatmap.json())
    assert all(item["intensity"] == 4 for item in heatmap.json())

    summary = await client.get(
        f"/habits/{habit_id}/analytics/summary",
        headers=headers,
    )
    assert summary.status_code == 200
    assert summary.json()["total_completed_days"] >= 3
    assert summary.json()["total_check_ins"] == 3


async def test_today_not_checked_keeps_daily_streak(client):
    headers = await auth_headers(client, "today@example.com")
    habit = await create_habit(
        client,
        headers,
        {"name": "Today", "habit_type": "boolean", "schedule_type": "daily"},
    )
    habit_id = habit["id"]
    today = datetime.now(UTC).date()
    yesterday = today.fromordinal(today.toordinal() - 1)
    response = await add_check_in(
        client,
        headers,
        habit_id,
        yesterday.isoformat(),
    )
    assert response.status_code == 201

    streak = await client.get(
        f"/habits/{habit_id}/analytics/streak",
        headers=headers,
    )
    assert streak.status_code == 200
    assert streak.json()["current_streak"] == 1


async def test_freeze_only_has_zero_streak_and_freeze_heatmap(client):
    headers = await auth_headers(client, "freeze@example.com")
    habit = await create_habit(
        client,
        headers,
        {"name": "Freeze", "habit_type": "boolean", "schedule_type": "daily"},
    )
    habit_id = habit["id"]
    today = datetime.now(UTC).date()
    freeze = await client.post(
        f"/habits/{habit_id}/freezes",
        headers=headers,
        json={"local_date": today.isoformat()},
    )
    assert freeze.status_code == 201

    streak = await client.get(
        f"/habits/{habit_id}/analytics/streak",
        headers=headers,
    )
    assert streak.status_code == 200
    assert streak.json()["current_streak"] == 0
    assert streak.json()["longest_streak"] == 0

    heatmap = await client.get(
        f"/habits/{habit_id}/analytics/heatmap",
        params={"from": today.isoformat(), "to": today.isoformat()},
        headers=headers,
    )
    assert heatmap.status_code == 200
    assert heatmap.json()[0]["is_frozen"] is True
    assert heatmap.json()[0]["intensity"] == 0


async def test_quantitative_heatmap_partial_and_completed(client):
    headers = await auth_headers(client, "quant@example.com")
    habit = await create_habit(
        client,
        headers,
        {
            "name": "Water",
            "habit_type": "quantitative",
            "schedule_type": "daily",
            "target_value": "100",
            "unit": "ml",
        },
    )
    habit_id = habit["id"]
    first = await add_check_in(client, headers, habit_id, "2026-11-20", "40")
    second = await add_check_in(client, headers, habit_id, "2026-11-20", "60")
    assert first.status_code == 201
    assert second.status_code == 201

    heatmap = await client.get(
        f"/habits/{habit_id}/analytics/heatmap",
        params={"from": "2026-11-20", "to": "2026-11-20"},
        headers=headers,
    )
    assert heatmap.status_code == 200
    item = heatmap.json()[0]
    assert item["is_completed"] is True
    assert item["intensity"] == 4
    assert float(item["value"]) == 100


async def test_weekdays_and_weekly_quota_streaks(client):
    headers = await auth_headers(client, "schedules@example.com")
    weekdays = await create_habit(
        client,
        headers,
        {
            "name": "Gym",
            "habit_type": "boolean",
            "schedule_type": "weekdays",
            "weekdays": [1, 3, 5],
        },
    )
    streak = await client.get(
        f"/habits/{weekdays['id']}/analytics/streak",
        headers=headers,
    )
    assert streak.status_code == 200
    assert streak.json()["unit"] == "days"

    quota = await create_habit(
        client,
        headers,
        {
            "name": "Reading",
            "habit_type": "boolean",
            "schedule_type": "weekly_quota",
            "weekly_target": 3,
        },
    )
    quota_streak = await client.get(
        f"/habits/{quota['id']}/analytics/streak",
        headers=headers,
    )
    assert quota_streak.status_code == 200
    assert quota_streak.json()["unit"] == "weeks"


async def test_heatmap_validation_archived_and_foreign(client):
    headers = await auth_headers(client, "validation@example.com")
    foreign_headers = await auth_headers(client, "foreign@example.com")
    habit = await create_habit(
        client,
        headers,
        {"name": "Archive", "habit_type": "boolean", "schedule_type": "daily"},
    )
    habit_id = habit["id"]

    reversed_range = await client.get(
        f"/habits/{habit_id}/analytics/heatmap",
        params={"from": "2026-12-02", "to": "2026-12-01"},
        headers=headers,
    )
    assert reversed_range.status_code == 422

    too_long = await client.get(
        f"/habits/{habit_id}/analytics/heatmap",
        params={"from": "2025-01-01", "to": "2026-12-31"},
        headers=headers,
    )
    assert too_long.status_code == 422

    archive = await client.post(
        f"/habits/{habit_id}/archive",
        headers=headers,
    )
    assert archive.status_code == 200
    analytics = await client.get(
        f"/habits/{habit_id}/analytics/summary",
        headers=headers,
    )
    assert analytics.status_code == 200

    foreign = await client.get(
        f"/habits/{habit_id}/analytics/streak",
        headers=foreign_headers,
    )
    assert foreign.status_code == 404


async def test_weekdays_backdated_new_york_and_schedule_summary(client):
    headers = await auth_headers(client, "ny-weekdays@example.com", "America/New_York")
    habit = await create_habit(
        client,
        headers,
        {
            "name": "Monday NY",
            "habit_type": "boolean",
            "schedule_type": "weekdays",
            "weekdays": [1],
        },
    )
    habit_id = habit["id"]

    backdated = await add_check_in(
        client,
        headers,
        habit_id,
        "2026-11-16",
    )
    assert backdated.status_code == 201

    utc_next_day = await add_check_in(
        client,
        headers,
        habit_id,
        "2026-11-20",
    )
    assert utc_next_day.status_code == 201

    streak = await client.get(
        f"/habits/{habit_id}/analytics/streak",
        headers=headers,
    )
    assert streak.status_code == 200

    on_monday = await add_check_in(
        client,
        headers,
        habit_id,
        "2026-11-23",
    )
    assert on_monday.status_code == 201

    non_scheduled = await create_habit(
        client,
        headers,
        {
            "name": "Scheduled summary",
            "habit_type": "boolean",
            "schedule_type": "weekdays",
            "weekdays": [1],
        },
    )
    non_scheduled_id = non_scheduled["id"]
    for day in ("2026-11-17", "2026-11-18", "2026-11-19"):
        response = await add_check_in(
            client,
            headers,
            non_scheduled_id,
            day,
        )
        assert response.status_code == 201

    summary = await client.get(
        f"/habits/{non_scheduled_id}/analytics/summary",
        headers=headers,
    )
    assert summary.status_code == 200
    assert 0.0 <= summary.json()["completion_rate_7d"] <= 1.0


async def test_daily_checkin_and_freeze_not_double_counted(client):
    headers = await auth_headers(client, "daily-freeze@example.com")
    habit = await create_habit(
        client,
        headers,
        {"name": "Daily freeze", "habit_type": "boolean", "schedule_type": "daily"},
    )
    habit_id = habit["id"]
    today = "2026-11-20"

    checked = await add_check_in(client, headers, habit_id, today)
    assert checked.status_code == 201
    frozen = await client.post(
        f"/habits/{habit_id}/freezes",
        headers=headers,
        json={"local_date": today},
    )
    assert frozen.status_code == 201

    streak = await client.get(
        f"/habits/{habit_id}/analytics/streak",
        headers=headers,
    )
    assert streak.status_code == 200
    assert streak.json()["current_streak"] == 1
    assert streak.json()["longest_streak"] == 1


async def test_weekly_quota_checkin_and_freeze_not_double_counted(client):
    headers = await auth_headers(client, "quota-freeze@example.com")
    habit = await create_habit(
        client,
        headers,
        {
            "name": "Quota freeze",
            "habit_type": "boolean",
            "schedule_type": "weekly_quota",
            "weekly_target": 1,
        },
    )
    habit_id = habit["id"]
    today = "2026-11-20"

    checked = await add_check_in(client, headers, habit_id, today)
    assert checked.status_code == 201
    frozen = await client.post(
        f"/habits/{habit_id}/freezes",
        headers=headers,
        json={"local_date": today},
    )
    assert frozen.status_code == 201

    streak = await client.get(
        f"/habits/{habit_id}/analytics/streak",
        headers=headers,
    )
    assert streak.status_code == 200
    assert streak.json()["unit"] == "weeks"
    assert streak.json()["current_streak"] == 1
    assert streak.json()["longest_streak"] == 1
