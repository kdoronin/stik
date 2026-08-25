from strava_mcp.client import StravaClient
from strava_mcp.core import ConfigStore
from strava_mcp.service import StravaService

service = StravaService(StravaClient(store=ConfigStore()))
profile = service.athlete_profile()
activities = service.recent_activities(per_page=3)
print(f"athlete_id={profile.get('id')} name={profile.get('firstname')} {profile.get('lastname')}")
print(f"recent_count={len(activities)}")
for activity in activities:
    print(
        f"activity_id={activity.get('id')} type={activity.get('type')} "
        f"date={activity.get('start_date_local')} name={activity.get('name')!r}"
    )
