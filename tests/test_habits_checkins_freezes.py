import pytest

pytestmark = pytest.mark.asyncio


async def register(client, email="owner@example.com", timezone="UTC"):
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": "secure-pass", "timezone": timezone},
    )
    assert response.status_code == 201
    login = await client.post(
        "/auth/login",
        data={"username": email, "password": "secure-pass"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def create_habit(client, headers, payload):
    return await client.post("/habits", headers=headers, json=payload)


async def test_crud_habit_types_and_schedules(client):
    headers = await register(client)
    cases = [
        {
            "name": "Daily water",
            "habit_type": "quantitative",
            "schedule_type": "daily",
            "target_value": "2000",
            "unit": "ml",
        },
        {
            "name": "Gym",
            "habit_type": "boolean",
            "schedule_type": "weekdays",
            "weekdays": [1, 3, 5],
        },
        {
            "name": "Reading",
            "habit_type": "boolean",
            "schedule_type": "weekly_quota",
            "weekly_target": 3,
        },
    ]
    ids = []
    for payload in cases:
        response = await create_habit(client, headers, payload)
        assert response.status_code == 201
        ids.append(response.json()["id"])

    listed = await client.get("/habits", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    patch = await client.patch(
        f"/habits/{ids[1]}",
        headers=headers,
        json={"schedule_type": "daily", "weekdays": None},
    )
    assert patch.status_code == 200
    assert patch.json()["weekdays"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": "Bad boolean",
            "habit_type": "boolean",
            "schedule_type": "daily",
            "target_value": "1",
        },
        {
            "name": "Bad quantitative",
            "habit_type": "quantitative",
            "schedule_type": "daily",
            "target_value": "0",
            "unit": "ml",
        },
        {
            "name": "Bad weekdays",
            "habit_type": "boolean",
            "schedule_type": "weekdays",
            "weekdays": [1, 1],
        },
        {
            "name": "Bad quota",
            "habit_type": "boolean",
            "schedule_type": "weekly_quota",
            "weekly_target": 8,
        },
    ],
)
async def test_invalid_habit_combinations(client, payload):
    headers = await register(client)
    response = await create_habit(client, headers, payload)
    assert response.status_code == 422


async def test_user_isolation_archive_and_restore(client):
    owner_headers = await register(client, "owner@example.com")
    other_headers = await register(client, "other@example.com")
    response = await create_habit(
        client,
        owner_headers,
        {"name": "Private", "habit_type": "boolean", "schedule_type": "daily"},
    )
    habit_id = response.json()["id"]

    foreign = await client.get(f"/habits/{habit_id}", headers=other_headers)
    assert foreign.status_code == 404

    archive = await client.post(f"/habits/{habit_id}/archive", headers=owner_headers)
    assert archive.status_code == 200
    duplicate_archive = await client.post(
        f"/habits/{habit_id}/archive",
        headers=owner_headers,
    )
    assert duplicate_archive.status_code == 409

    frozen = await client.post(
        f"/habits/{habit_id}/freezes",
        headers=owner_headers,
        json={"local_date": "2026-05-10"},
    )
    assert frozen.status_code == 409
    check_in = await client.post(
        f"/habits/{habit_id}/check-ins",
        headers=owner_headers,
        json={"value": 1},
    )
    assert check_in.status_code == 409

    restored = await client.post(f"/habits/{habit_id}/restore", headers=owner_headers)
    assert restored.status_code == 200
    duplicate_restore = await client.post(
        f"/habits/{habit_id}/restore",
        headers=owner_headers,
    )
    assert duplicate_restore.status_code == 409


async def test_timezone_local_date_survives_timezone_change(client):
    headers = await register(client, timezone="Europe/Moscow")
    created = await create_habit(
        client,
        headers,
        {
            "name": "UTC edge",
            "habit_type": "quantitative",
            "schedule_type": "daily",
            "target_value": "100",
            "unit": "ml",
        },
    )
    habit_id = created.json()["id"]
    check_in = await client.post(
        f"/habits/{habit_id}/check-ins",
        headers=headers,
        json={"value": "100", "logged_at": "2026-05-10T22:30:00Z"},
    )
    assert check_in.status_code == 201
    assert check_in.json()["local_date"] == "2026-05-11"

    changed = await client.patch(
        "/users/me",
        headers=headers,
        json={"timezone": "America/New_York"},
    )
    assert changed.status_code == 200
    fetched = await client.get(
        f"/habits/{habit_id}/check-ins/{check_in.json()['id']}",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["local_date"] == "2026-05-11"


async def test_boolean_duplicate_and_quantitative_multiple(client):
    headers = await register(client)
    boolean = await create_habit(
        client,
        headers,
        {"name": "Boolean", "habit_type": "boolean", "schedule_type": "daily"},
    )
    boolean_id = boolean.json()["id"]
    first = await client.post(
        f"/habits/{boolean_id}/check-ins",
        headers=headers,
        json={"value": 1, "logged_at": "2026-05-10T12:00:00Z"},
    )
    duplicate = await client.post(
        f"/habits/{boolean_id}/check-ins",
        headers=headers,
        json={"value": 1, "logged_at": "2026-05-10T13:00:00Z"},
    )
    assert first.status_code == 201
    assert duplicate.status_code == 409

    quantitative = await create_habit(
        client,
        headers,
        {
            "name": "Water",
            "habit_type": "quantitative",
            "schedule_type": "daily",
            "target_value": "200",
            "unit": "ml",
        },
    )
    quantitative_id = quantitative.json()["id"]
    one = await client.post(
        f"/habits/{quantitative_id}/check-ins",
        headers=headers,
        json={"value": "100", "logged_at": "2026-05-10T12:00:00Z"},
    )
    two = await client.post(
        f"/habits/{quantitative_id}/check-ins",
        headers=headers,
        json={"value": "100", "logged_at": "2026-05-10T13:00:00Z"},
    )
    assert one.status_code == 201
    assert two.status_code == 201


async def test_cursor_pagination_filters_and_invalid_cursor(client):
    headers = await register(client)
    habit = await create_habit(
        client,
        headers,
        {
            "name": "Cursor",
            "habit_type": "quantitative",
            "schedule_type": "daily",
            "target_value": "10",
            "unit": "items",
        },
    )
    habit_id = habit.json()["id"]
    for day in range(1, 6):
        response = await client.post(
            f"/habits/{habit_id}/check-ins",
            headers=headers,
            json={
                "value": "1",
                "logged_at": f"2026-05-{day:02d}T12:00:00Z",
            },
        )
        assert response.status_code == 201

    seen = []
    cursor = None
    while True:
        url = f"/habits/{habit_id}/check-ins?limit=2"
        if cursor:
            url += f"&cursor={cursor}"
        page = await client.get(url, headers=headers)
        assert page.status_code == 200
        body = page.json()
        seen.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == len(set(seen)) == 5

    filtered = await client.get(
        f"/habits/{habit_id}/check-ins?from=2026-05-02&to=2026-05-04",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["items"]) == 3

    invalid = await client.get(
        f"/habits/{habit_id}/check-ins?cursor=not-valid",
        headers=headers,
    )
    assert invalid.status_code == 422


async def test_freeze_create_duplicate_and_delete(client):
    headers = await register(client)
    habit = await create_habit(
        client,
        headers,
        {"name": "Frozen", "habit_type": "boolean", "schedule_type": "daily"},
    )
    habit_id = habit.json()["id"]
    created = await client.post(
        f"/habits/{habit_id}/freezes",
        headers=headers,
        json={"local_date": "2026-05-10"},
    )
    assert created.status_code == 201
    duplicate = await client.post(
        f"/habits/{habit_id}/freezes",
        headers=headers,
        json={"local_date": "2026-05-10"},
    )
    assert duplicate.status_code == 409
    deleted = await client.delete(
        f"/habits/{habit_id}/freezes/2026-05-10",
        headers=headers,
    )
    assert deleted.status_code == 204
