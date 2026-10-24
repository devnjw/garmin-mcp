"""Explicit MCP signatures for the documented Personal API operations."""

from typing import Any

from mcp.types import ToolAnnotations


def register_api_tools(mcp, run):
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_activity(
        activity_id: int,
    ) -> dict[str, Any]:
        """Full activity details, including fields omitted from the summary tool. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("activity", activity_id=activity_id)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_activity_workouts(
        activity_id: int,
    ) -> dict[str, Any]:
        """Workouts associated with an activity. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("activity_workouts", activity_id=activity_id)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_activity_search(
        start: int | None = None,
        limit: int | None = None,
        favorite: int | None = None,
        sort_order: str | None = None,
        exclude_children: bool | None = None,
        sort_by: str | None = None,
        search: str | None = None,
        activity_type: str | None = None,
        activity_sub_type: str | None = None,
        event_type: str | None = None,
        min_distance: int | None = None,
        max_distance: int | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
        min_elevation: int | None = None,
        max_elevation: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        upper_latitude: float | None = None,
        right_longitude: float | None = None,
        lower_latitude: float | None = None,
        left_longitude: float | None = None,
        lower_max_depth: int | None = None,
        upper_max_depth: int | None = None,
        deco_dive: bool | None = None,
        min_elapsed_duration: int | None = None,
        max_elapsed_duration: int | None = None,
        min_bottom_time: int | None = None,
        max_bottom_time: int | None = None,
        min_avg_power: int | None = None,
        excluded_activity_sub_type: list[str] | None = None,
        required_field: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search activities with every documented filter. Distances and elevations are meters, durations are seconds, dive depth is centimeters, and power is watts. Array filters become repeated query parameters. Supply all four coordinates for a bounding box. Follow pagination with start and limit. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run(
            "activity_search",
            start=start,
            limit=limit,
            favorite=favorite,
            sort_order=sort_order,
            exclude_children=exclude_children,
            sort_by=sort_by,
            search=search,
            activity_type=activity_type,
            activity_sub_type=activity_sub_type,
            event_type=event_type,
            min_distance=min_distance,
            max_distance=max_distance,
            min_duration=min_duration,
            max_duration=max_duration,
            min_elevation=min_elevation,
            max_elevation=max_elevation,
            start_date=start_date,
            end_date=end_date,
            upper_latitude=upper_latitude,
            right_longitude=right_longitude,
            lower_latitude=lower_latitude,
            left_longitude=left_longitude,
            lower_max_depth=lower_max_depth,
            upper_max_depth=upper_max_depth,
            deco_dive=deco_dive,
            min_elapsed_duration=min_elapsed_duration,
            max_elapsed_duration=max_elapsed_duration,
            min_bottom_time=min_bottom_time,
            max_bottom_time=max_bottom_time,
            min_avg_power=min_avg_power,
            excluded_activity_sub_type=excluded_activity_sub_type,
            required_field=required_field,
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_heart_rate_zones(
        generate_defaults: bool | None = None,
    ) -> dict[str, Any]:
        """Heart-rate zone settings. generate_defaults defaults to false; setting it true may generate account zone settings when none exist. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("heart_rate_zones", generate_defaults=generate_defaults)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_download_activity(
        activity_id: int,
    ) -> dict[str, Any]:
        """Download the original activity ZIP to a private local directory. Returns file metadata; never extracts the archive. This tool writes a new file on this Mac. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("download_activity", activity_id=activity_id)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_fitness_age(
        calendar_date: str | None = None,
        full_history_scan: bool | None = None,
    ) -> dict[str, Any]:
        """Fitness-age data as of a date. full_history_scan controls the look-back search. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run(
            "fitness_age", calendar_date=calendar_date, full_history_scan=full_history_scan
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_weight_goals(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Effective weight goals for a date interval. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("weight_goals", start_date=start_date, end_date=end_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_hrv_daily(
        calendar_date: str | None = None,
    ) -> dict[str, Any]:
        """Full daily HRV summary and readings. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("hrv_daily", calendar_date=calendar_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_hrv_summaries(
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """HRV summaries across a date interval. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("hrv_summaries", from_date=from_date, to_date=to_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_food_logs(
        include_goals: bool | None = None,
        include_nutrition: bool | None = None,
        include_media: bool | None = None,
        meal_id: int | None = None,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Food logs with optional goals, nutrition, media and meal filters. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run(
            "food_logs",
            include_goals=include_goals,
            include_nutrition=include_nutrition,
            include_media=include_media,
            meal_id=meal_id,
            date=date,
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_menstrual_summary(
        calendar_date: str | None = None,
    ) -> dict[str, Any]:
        """Menstrual-cycle summary for a date. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("menstrual_summary", calendar_date=calendar_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_menstrual_day(
        calendar_date: str | None = None,
        today_date: str | None = None,
        reduced_response: bool | None = None,
        skipbm: bool | None = None,
        include_analysis: bool | None = None,
    ) -> dict[str, Any]:
        """Menstrual-cycle day view, including optional analysis and prediction reference date. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run(
            "menstrual_day",
            calendar_date=calendar_date,
            today_date=today_date,
            reduced_response=reduced_response,
            skipbm=skipbm,
            include_analysis=include_analysis,
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_sleep_daily(
        date: str | None = None,
    ) -> dict[str, Any]:
        """Full sleep response for a date, with fields preserved. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("sleep_daily", date=date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_sleep_summaries(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Sleep summaries across a date interval, including empty placeholders from Garmin. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("sleep_summaries", start_date=start_date, end_date=end_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_profile() -> dict[str, Any]:
        """Full profile settings. May include account identifiers and personal information. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("profile")

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_hydration(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Daily hydration statistics. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("hydration", start_date=start_date, end_date=end_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_steps(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Daily step statistics. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("steps", start_date=start_date, end_date=end_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_stress(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Daily stress statistics. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("stress", start_date=start_date, end_date=end_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_daily_summary(
        calendar_date: str | None = None,
    ) -> dict[str, Any]:
        """Full daily user summary, preserving all Garmin fields. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("daily_summary", calendar_date=calendar_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_daily_summaries(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """User summary range response, including the original data envelope. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("daily_summaries", start_date=start_date, end_date=end_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_weight_all(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """All weight measurements from the weight/all endpoint. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("weight_all", start_date=start_date, end_date=end_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_weight_range(
        start_date: str | None = None,
        end_date: str | None = None,
        include_all: bool | None = None,
    ) -> dict[str, Any]:
        """Weight range response; include_all controls all versus latest daily entries. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run(
            "weight_range", start_date=start_date, end_date=end_date, include_all=include_all
        )

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_body_battery(
        start_date: str | None = None,
        end_date: str | None = None,
        chunks: int | None = None,
    ) -> dict[str, Any]:
        """Body Battery readings and optional interval grouping using chunks. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("body_battery", start_date=start_date, end_date=end_date, chunks=chunks)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_spo2(
        calendar_date: str | None = None,
    ) -> dict[str, Any]:
        """Daily oxygen saturation and acclimation data. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("spo2", calendar_date=calendar_date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_heart_rate(
        date: str | None = None,
    ) -> dict[str, Any]:
        """Daily heart-rate readings and summary. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("heart_rate", date=date)

    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            openWorldHint=True,
        )
    )
    async def garmin_api_wellness_activities(
        from_date: str | None = None,
        until_date: str | None = None,
    ) -> dict[str, Any]:
        """Wellness activity summaries across a date interval. Raw JSON fields are not normalized. Date ranges default to 7 days and allow at most 31 days (activity search uses pagination)."""
        return await run("wellness_activities", from_date=from_date, until_date=until_date)
