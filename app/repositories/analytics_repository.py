from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

STREAK_DAILY_SQL = text(
    """
    WITH habit AS (
        SELECT h.id, h.habit_type, h.target_value
        FROM habits h
        WHERE h.id = :habit_id
          AND h.user_id = :user_id
    ),
    completed_dates AS (
        SELECT ci.local_date,
               TRUE AS is_completed
        FROM check_ins ci
        CROSS JOIN habit h
        WHERE ci.habit_id = h.id
          AND ci.local_date <= CAST(:today AS date)
        GROUP BY ci.local_date, h.habit_type, h.target_value
        HAVING SUM(ci.value) >= CASE
            WHEN h.habit_type = 'boolean' THEN 1
            ELSE h.target_value
        END
    ),
    frozen_dates AS (
        SELECT f.local_date
        FROM habit_freezes f
        WHERE f.habit_id = :habit_id
          AND f.local_date <= CAST(:today AS date)
    ),
    effective_dates AS (
        SELECT COALESCE(c.local_date, f.local_date) AS local_date,
               COALESCE(c.is_completed, FALSE) AS is_completed
        FROM completed_dates c
        FULL OUTER JOIN frozen_dates f ON f.local_date = c.local_date
    ),
    numbered AS (
        SELECT local_date,
               is_completed,
               ROW_NUMBER() OVER (ORDER BY local_date) AS rn
        FROM effective_dates
    ),
    islands AS (
        SELECT COUNT(*) FILTER (WHERE is_completed) AS streak_len,
               MAX(local_date) AS island_end
        FROM numbered
        GROUP BY local_date - rn::int
    )
    SELECT
        COALESCE((
            SELECT streak_len
            FROM islands
            WHERE island_end >= CAST(:today AS date) - 1
            ORDER BY island_end DESC
            LIMIT 1
        ), 0)::int AS current_streak,
        COALESCE(MAX(streak_len), 0)::int AS longest_streak
    FROM islands
    """
)


STREAK_WEEKDAYS_SQL = text(
    """
    WITH habit AS (
        SELECT h.id, h.habit_type, h.target_value
        FROM habits h
        WHERE h.id = :habit_id
          AND h.user_id = :user_id
    ),
    bounds AS (
        SELECT LEAST(
            COALESCE(
                (SELECT MIN(ci.local_date)
                 FROM check_ins ci
                 WHERE ci.habit_id = :habit_id
                   AND ci.local_date <= CAST(:today AS date)),
                CAST(:today AS date)
            ),
            COALESCE(
                (SELECT MIN(f.local_date)
                 FROM habit_freezes f
                 WHERE f.habit_id = :habit_id
                   AND f.local_date <= CAST(:today AS date)),
                CAST(:today AS date)
            ),
            CAST(:today AS date)
        ) AS start_date
    ),
    scheduled AS (
        SELECT d::date AS local_date,
               ROW_NUMBER() OVER (ORDER BY d) AS sched_rn
        FROM generate_series(
            (SELECT start_date FROM bounds),
            CAST(:today AS date),
            INTERVAL '1 day'
        ) d
        CROSS JOIN habit h
        WHERE EXTRACT(ISODOW FROM d)::int IN (
            SELECT hw.weekday
            FROM habit_weekdays hw
            WHERE hw.habit_id = h.id
        )
    ),
    completed_dates AS (
        SELECT ci.local_date,
               TRUE AS is_completed
        FROM check_ins ci
        CROSS JOIN habit h
        WHERE ci.habit_id = h.id
          AND ci.local_date <= CAST(:today AS date)
        GROUP BY ci.local_date, h.habit_type, h.target_value
        HAVING SUM(ci.value) >= CASE
            WHEN h.habit_type = 'boolean' THEN 1
            ELSE h.target_value
        END
    ),
    status AS (
        SELECT s.local_date,
               s.sched_rn,
               c.is_completed IS TRUE AS is_completed,
               EXISTS (
                   SELECT 1
                   FROM habit_freezes f
                   WHERE f.habit_id = :habit_id
                     AND f.local_date = s.local_date
                     AND f.local_date <= CAST(:today AS date)
               ) AS is_frozen
        FROM scheduled s
        LEFT JOIN completed_dates c ON c.local_date = s.local_date
    ),
    effective AS (
        SELECT local_date, sched_rn, is_completed
        FROM status
        WHERE is_completed OR is_frozen
    ),
    numbered AS (
        SELECT *,
               ROW_NUMBER() OVER (ORDER BY sched_rn) AS rn
        FROM effective
    ),
    islands AS (
        SELECT COUNT(*) FILTER (WHERE is_completed) AS streak_len,
               MAX(sched_rn) AS island_end_rn
        FROM numbered
        GROUP BY sched_rn - rn
    ),
    totals AS (
        SELECT COUNT(*) AS max_total_sched_rn
        FROM scheduled
    ),
    latest_island AS (
        SELECT streak_len, island_end_rn
        FROM islands
        ORDER BY island_end_rn DESC
        LIMIT 1
    ),
    today_status AS (
        SELECT EXISTS (
                   SELECT 1 FROM scheduled
                   WHERE local_date = CAST(:today AS date)
               ) AS today_scheduled,
               EXISTS (
                   SELECT 1 FROM effective
                   WHERE local_date = CAST(:today AS date)
               ) AS today_effective
    ),
    active_island AS (
        SELECT li.streak_len
        FROM latest_island li
        CROSS JOIN totals t
        CROSS JOIN today_status ts
        WHERE li.island_end_rn = t.max_total_sched_rn
           OR (ts.today_scheduled
               AND NOT ts.today_effective
               AND li.island_end_rn = t.max_total_sched_rn - 1)
    )
    SELECT
        COALESCE((SELECT streak_len FROM active_island), 0)::int AS current_streak,
        COALESCE((
            SELECT MAX(streak_len)::int
            FROM islands
        ), 0) AS longest_streak
    FROM totals
    """
)


STREAK_WEEKLY_QUOTA_SQL = text(
    """
    WITH habit AS (
        SELECT h.id, h.habit_type, h.target_value, h.weekly_target
        FROM habits h
        WHERE h.id = :habit_id
          AND h.user_id = :user_id
    ),
    completed_dates AS (
        SELECT ci.local_date,
               TRUE AS is_completed
        FROM check_ins ci
        CROSS JOIN habit h
        WHERE ci.habit_id = h.id
          AND ci.local_date <= CAST(:today AS date)
        GROUP BY ci.local_date, h.habit_type, h.target_value
        HAVING SUM(ci.value) >= CASE
            WHEN h.habit_type = 'boolean' THEN 1
            ELSE h.target_value
        END
    ),
    frozen_dates AS (
        SELECT f.local_date
        FROM habit_freezes f
        WHERE f.habit_id = :habit_id
          AND f.local_date <= CAST(:today AS date)
    ),
    effective_dates AS (
        SELECT COALESCE(c.local_date, f.local_date) AS local_date,
               COALESCE(c.is_completed, FALSE) AS is_completed
        FROM completed_dates c
        FULL OUTER JOIN frozen_dates f ON f.local_date = c.local_date
    ),
    week_status AS (
        SELECT date_trunc('week', ed.local_date)::date AS week_start,
               COUNT(*) FILTER (WHERE ed.is_completed) AS completed_days,
               COUNT(*) AS effective_days
        FROM effective_dates ed
        GROUP BY date_trunc('week', ed.local_date)::date
    ),
    effective_weeks AS (
        SELECT ws.week_start,
               ws.completed_days >= h.weekly_target AS week_completed,
               ws.completed_days < h.weekly_target
                   AND ws.effective_days >= h.weekly_target AS week_frozen
        FROM week_status ws
        CROSS JOIN habit h
        WHERE ws.effective_days >= h.weekly_target
    ),
    numbered AS (
        SELECT *,
               ROW_NUMBER() OVER (ORDER BY week_start) AS rn
        FROM effective_weeks
    ),
    islands AS (
        SELECT COUNT(*) FILTER (WHERE week_completed) AS streak_len,
               MAX(week_start) AS island_end
        FROM numbered
        GROUP BY week_start - rn::int * 7
    )
    SELECT
        COALESCE((
            SELECT streak_len
            FROM islands
            WHERE island_end >= date_trunc('week', CAST(:today AS date))::date - 7
            ORDER BY island_end DESC
            LIMIT 1
        ), 0)::int AS current_streak,
        COALESCE(MAX(streak_len), 0)::int AS longest_streak
    FROM islands
    """
)


HEATMAP_SQL = text(
    """
    WITH habit AS (
        SELECT h.id, h.habit_type, h.target_value
        FROM habits h
        WHERE h.id = :habit_id
          AND h.user_id = :user_id
    ),
    calendar AS (
        SELECT d::date AS local_date
        FROM generate_series(
            CAST(:date_from AS date),
            CAST(:date_to AS date),
            INTERVAL '1 day'
        ) d
    ),
    daily_values AS (
        SELECT ci.local_date, SUM(ci.value) AS day_value
        FROM check_ins ci
        CROSS JOIN habit h
        WHERE ci.habit_id = h.id
          AND ci.local_date BETWEEN
              CAST(:date_from AS date) AND CAST(:date_to AS date)
        GROUP BY ci.local_date, h.habit_type, h.target_value
    )
    SELECT c.local_date AS date,
           COALESCE(v.day_value, 0)::numeric(12, 2) AS value,
           CASE
               WHEN h.habit_type = 'boolean' THEN 1
               ELSE h.target_value
           END::numeric(12, 2) AS target_value,
           CASE
               WHEN h.habit_type = 'boolean'
               THEN COALESCE(v.day_value, 0) >= 1
               ELSE COALESCE(v.day_value, 0) >= h.target_value
           END AS is_completed,
           EXISTS (
               SELECT 1
               FROM habit_freezes f
               WHERE f.habit_id = h.id
                 AND f.local_date = c.local_date
           ) AS is_frozen,
           CASE
               WHEN h.habit_type = 'boolean'
                    AND COALESCE(v.day_value, 0) >= 1 THEN 4
               WHEN h.habit_type = 'boolean' THEN 0
               WHEN COALESCE(v.day_value, 0) >= h.target_value THEN 4
               WHEN COALESCE(v.day_value, 0) = 0 THEN 0
               WHEN COALESCE(v.day_value, 0) / h.target_value < 0.34 THEN 1
               WHEN COALESCE(v.day_value, 0) / h.target_value < 0.67 THEN 2
               ELSE 3
           END AS intensity
    FROM calendar c
    CROSS JOIN habit h
    LEFT JOIN daily_values v ON v.local_date = c.local_date
    ORDER BY c.local_date
    """
)


SUMMARY_SQL = text(
    """
    WITH habit AS (
        SELECT h.id, h.habit_type, h.schedule_type, h.target_value, h.weekly_target
        FROM habits h
        WHERE h.id = :habit_id
          AND h.user_id = :user_id
    ),
    completed_dates AS (
        SELECT ci.local_date,
               TRUE AS is_completed
        FROM check_ins ci
        CROSS JOIN habit h
        WHERE ci.habit_id = h.id
          AND ci.local_date <= CAST(:today AS date)
        GROUP BY ci.local_date, h.habit_type, h.target_value
        HAVING SUM(ci.value) >= CASE
            WHEN h.habit_type = 'boolean' THEN 1
            ELSE h.target_value
        END
    ),
    scheduled_7 AS (
        SELECT d::date AS local_date
        FROM generate_series(
            CAST(:today AS date) - 6,
            CAST(:today AS date),
            INTERVAL '1 day'
        ) d
    ),
    scheduled_30 AS (
        SELECT d::date AS local_date
        FROM generate_series(
            CAST(:today AS date) - 29,
            CAST(:today AS date),
            INTERVAL '1 day'
        ) d
    ),
    summary AS (
        SELECT
            (SELECT COUNT(*) FROM completed_dates) AS total_completed_days,
            (SELECT COUNT(*)
             FROM check_ins ci
             WHERE ci.habit_id = :habit_id
               AND ci.local_date <= CAST(:today AS date)) AS total_check_ins,
            (SELECT COUNT(*)
             FROM completed_dates cd
             WHERE cd.local_date >= CAST(:today AS date) - 6) AS completed_7,
            (SELECT COUNT(*)
             FROM completed_dates cd
             WHERE cd.local_date >= CAST(:today AS date) - 29) AS completed_30
        FROM habit
    )
    SELECT s.total_completed_days::int,
           s.total_check_ins::int,
           COALESCE(CASE h.schedule_type
               WHEN 'daily' THEN ROUND(s.completed_7::numeric / 7.0, 4)
               WHEN 'weekdays' THEN ROUND(
                   (
                       SELECT COUNT(*)
                       FROM completed_dates cd
                       JOIN scheduled_7 q ON q.local_date = cd.local_date
                       WHERE EXTRACT(ISODOW FROM cd.local_date)::int IN (
                           SELECT weekday
                           FROM habit_weekdays
                           WHERE habit_id = h.id
                       )
                   )::numeric /
                   NULLIF((
                       SELECT COUNT(*)
                       FROM scheduled_7 q
                       WHERE EXTRACT(ISODOW FROM q.local_date)::int IN (
                           SELECT weekday
                           FROM habit_weekdays
                           WHERE habit_id = h.id
                       )
                   ), 0),
                   4
               )
               WHEN 'weekly_quota' THEN
                   LEAST(1.0, ROUND(s.completed_7::numeric / (h.weekly_target * 1.0), 4))
           END, 0.0) AS completion_rate_7d,
           COALESCE(CASE h.schedule_type
               WHEN 'daily' THEN ROUND(s.completed_30::numeric / 30.0, 4)
               WHEN 'weekdays' THEN ROUND(
                   (
                       SELECT COUNT(*)
                       FROM completed_dates cd
                       JOIN scheduled_30 q ON q.local_date = cd.local_date
                       WHERE EXTRACT(ISODOW FROM cd.local_date)::int IN (
                           SELECT weekday
                           FROM habit_weekdays
                           WHERE habit_id = h.id
                       )
                   )::numeric /
                   NULLIF((
                       SELECT COUNT(*)
                       FROM scheduled_30 q
                       WHERE EXTRACT(ISODOW FROM q.local_date)::int IN (
                           SELECT weekday
                           FROM habit_weekdays
                           WHERE habit_id = h.id
                       )
                   ), 0),
                   4
               )
               WHEN 'weekly_quota' THEN
                   LEAST(
                       1.0,
                       ROUND(s.completed_30::numeric / (h.weekly_target * (30.0 / 7.0)), 4)
                   )
           END, 0.0) AS completion_rate_30d
    FROM summary s
    CROSS JOIN habit h
    """
)


OWNERSHIP_SQL = text(
    """
    SELECT h.id, h.habit_type, h.schedule_type, h.target_value,
           h.weekly_target
    FROM habits h
    WHERE h.id = :habit_id
      AND h.user_id = :user_id
    """
)


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_owned_habit(self, habit_id: UUID, user_id: UUID):
        result = await self.session.execute(
            OWNERSHIP_SQL,
            {"habit_id": habit_id, "user_id": user_id},
        )
        return result.mappings().first()

    async def get_streak(
        self,
        habit_id: UUID,
        user_id: UUID,
        today: date,
        schedule_type: str,
    ) -> dict:
        sql = {
            "daily": STREAK_DAILY_SQL,
            "weekdays": STREAK_WEEKDAYS_SQL,
            "weekly_quota": STREAK_WEEKLY_QUOTA_SQL,
        }[schedule_type]
        result = await self.session.execute(
            sql,
            {"habit_id": habit_id, "user_id": user_id, "today": today},
        )
        row = result.mappings().first()
        return dict(row or {"current_streak": 0, "longest_streak": 0})

    async def get_heatmap(
        self,
        habit_id: UUID,
        user_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[dict]:
        result = await self.session.execute(
            HEATMAP_SQL,
            {
                "habit_id": habit_id,
                "user_id": user_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_summary(
        self,
        habit_id: UUID,
        user_id: UUID,
        today: date,
    ) -> dict:
        result = await self.session.execute(
            SUMMARY_SQL,
            {"habit_id": habit_id, "user_id": user_id, "today": today},
        )
        row = result.mappings().first()
        return dict(
            row
            or {
                "total_completed_days": 0,
                "total_check_ins": 0,
                "completion_rate_7d": 0.0,
                "completion_rate_30d": 0.0,
            }
        )
