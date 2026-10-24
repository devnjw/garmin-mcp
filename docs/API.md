# API coverage

Checked against Garmin Personal API 1.0.0 Swagger on 2026-10-24: **26/26 documented GET operations** and every documented parameter have named MCP tools. Authentication is a separate POST handled internally.

Source: https://developer.garmin.com/gc-developer-program/personal/swagger-docs/

## Detailed tools

| MCP tool | GET path | Arguments |
| --- | --- | --- |
| `garmin_api_activity` | `/activity-service/activity/{activityId}` | `activity_id` |
| `garmin_api_activity_workouts` | `/activity-service/activity/{activityId}/workouts` | `activity_id` |
| `garmin_api_activity_search` | `/activitylist-service/activities/search/activities` | `start`, `limit`, `favorite`, `sort_order`, `exclude_children`, `sort_by`, `search`, `activity_type`, `activity_sub_type`, `event_type`, `min_distance`, `max_distance`, `min_duration`, `max_duration`, `min_elevation`, `max_elevation`, `start_date`, `end_date`, `upper_latitude`, `right_longitude`, `lower_latitude`, `left_longitude`, `lower_max_depth`, `upper_max_depth`, `deco_dive`, `min_elapsed_duration`, `max_elapsed_duration`, `min_bottom_time`, `max_bottom_time`, `min_avg_power`, `excluded_activity_sub_type`, `required_field` |
| `garmin_api_heart_rate_zones` | `/biometric-service/heartRateZones/v2` | `generate_defaults` |
| `garmin_api_download_activity` | `/download-service/files/activity/{activityId}` | `activity_id` |
| `garmin_api_fitness_age` | `/fitnessage-service/fitnessage/v2/{calendarDate}` | `calendar_date`, `full_history_scan` |
| `garmin_api_weight_goals` | `/goal-service/goal/user/effective/weightgoal/{startDate}/{endDate}` | `start_date`, `end_date` |
| `garmin_api_hrv_daily` | `/hrv-service/hrv/{calendarDate}` | `calendar_date` |
| `garmin_api_hrv_summaries` | `/hrv-service/hrv/daily/{fromDate}/{toDate}` | `from_date`, `to_date` |
| `garmin_api_food_logs` | `/nutrition-service/food/logs/{date}` | `include_goals`, `include_nutrition`, `include_media`, `meal_id`, `date` |
| `garmin_api_menstrual_summary` | `/periodichealth-service/menstrualcycle/summary/{calendarDate}` | `calendar_date` |
| `garmin_api_menstrual_day` | `/periodichealth-service/menstrualcycle/dayview/{calendarDate}` | `calendar_date`, `today_date`, `reduced_response`, `skipbm`, `include_analysis` |
| `garmin_api_sleep_daily` | `/sleep-service/sleep/dailySleep` | `date` |
| `garmin_api_sleep_summaries` | `/sleep-service/sleep/dailySleepSummariesByDate` | `start_date`, `end_date` |
| `garmin_api_profile` | `/userprofile-service/userprofile/settings` | None |
| `garmin_api_hydration` | `/usersummary-service/stats/hydration/daily/{startDate}/{endDate}` | `start_date`, `end_date` |
| `garmin_api_steps` | `/usersummary-service/stats/steps/daily/{startDate}/{endDate}` | `start_date`, `end_date` |
| `garmin_api_stress` | `/usersummary-service/stats/stress/daily/{startDate}/{endDate}` | `start_date`, `end_date` |
| `garmin_api_daily_summary` | `/usersummary-service/usersummary/daily` | `calendar_date` |
| `garmin_api_daily_summaries` | `/usersummary-service/v2/dailysummaries` | `start_date`, `end_date` |
| `garmin_api_weight_all` | `/weight-service/weight/all/{startDate}/{endDate}` | `start_date`, `end_date` |
| `garmin_api_weight_range` | `/weight-service/weight/range/{startDate}/{endDate}` | `start_date`, `end_date`, `include_all` |
| `garmin_api_body_battery` | `/wellness-service/wellness/bodyBattery/reports/daily` | `start_date`, `end_date`, `chunks` |
| `garmin_api_spo2` | `/wellness-service/wellness/daily/spo2acclimation/{calendarDate}` | `calendar_date` |
| `garmin_api_heart_rate` | `/wellness-service/wellness/dailyHeartRate` | `date` |
| `garmin_api_wellness_activities` | `/wellnessactivity-service/activity/summary/range/{fromDate}/{untilDate}` | `from_date`, `until_date` |

Argument names use snake_case in MCP; the client maps them to Garmin’s original query/path names. All parameters are present in MCP input schemas. Activity IDs are required positive integers. Dates default to the configured timezone’s current date; ranges default to the last seven inclusive days. Optional flags otherwise retain Garmin defaults, except `generate_defaults=false` and activity page size 20.

## Response and limits

- Raw JSON is returned unchanged under `data`, with status/source/query metadata. Response success does not assert complete measurements. Only null or an empty top-level list/object is classified as `no_data`; HTTP failures are errors.
- Raw range endpoints allow up to 31 days per call. Activity search permits an unrestricted date span with page sizes 1–100, `start` offset and `next_start` response metadata. A full page may require another query to establish the end.
- All 32 activity-search parameters are supported, including repeated array filters, favorite status, subtype/event filters, bounding boxes, dive filters and min/max metrics. Dates and bounds are validated before contacting Garmin.
- `garmin_api_download_activity` returns a local ZIP path, byte count and SHA-256 instead of binary data in the model context. It creates a new 0600 file in a 0700 downloads directory, never extracts ZIP contents, and refuses responses over 64 MiB.
- JSON responses are limited to 8 MiB. A size-limit error asks for a smaller query; responses are never silently truncated by this server. MCP clients may impose their own output limits.
- `garmin_api_heart_rate_zones(generate_defaults=true)` can generate defaults in Garmin. This option is false unless explicitly requested. This tool and download have `readOnlyHint=false`; the other 32 tools have `readOnlyHint=true`.
- Only documented endpoint paths are available. There is no arbitrary URL/path fetch tool, account-key tool, or Garmin upload/edit/delete tool.

## Summary tools retained

| Tool | Behavior |
| --- | --- |
| `garmin_status` | Environment credential configuration and optional authentication check; no profile values |
| `garmin_daily_summary` | One day of selected health/activity metrics |
| `garmin_sleep` | Sleep/nap duration, stages, score and overnight metrics; explicit missing dates |
| `garmin_hrv` | Nightly and weekly HRV summaries |
| `garmin_body_battery` | Charge/drain and observed minimum/maximum |
| `garmin_activities` | Normalized workout search with pagination |
| `garmin_activity` | Selected metrics for an activity |
| `garmin_day` | Combined day with section-level missing/error states |

Summary ranges allow 90 days and split API calls into 31-day windows. Units appear in normalized field names. Missing values and Garmin negative sentinels become null while real zeroes are preserved. Empty sleep placeholders are missing; nap-only dates come from explicit nap dates and never supply an overnight sleep date.

## Meaning of coverage

During live verification, the documented `weight/all` endpoint returned HTTP 400 for valid date intervals, including a direct call through the official client. The MCP tool retains that failure and suggests explicitly calling `garmin_api_weight_range` with the same dates and `include_all=true`. The alternative succeeded in verification and has a different response shape. Other accounts or future Garmin API versions may behave differently.

Endpoint and parameter support is contract-tested independently of real account data. Availability still depends on Garmin, device capabilities, account settings, recorded data and any feature entitlement. See [verification scope](VERIFICATION.md). The full Garmin app and business APIs are outside this Personal API snapshot.
