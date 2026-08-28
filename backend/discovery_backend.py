import json
import os
import threading
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env()


DISCOVERY_DB_PATH = Path(os.getenv("KICK_DISCOVERY_DB_PATH", "./data/discovery.json"))
DISCOVERY_TIMEOUT_S = float(os.getenv("KICK_DISCOVERY_PROVIDER_TIMEOUT_S", "4.0"))
DISCOVERY_LOCK = threading.Lock()

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_db() -> dict[str, Any]:
    DISCOVERY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DISCOVERY_DB_PATH.exists():
        try:
            return json.loads(DISCOVERY_DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    seed = {
        "posts": [
            {
                "id": "seed-pass-support-foot",
                "user_name": "沙坪坝 7 号",
                "region": "重庆 · 沙坪坝",
                "badge": "传球 · 支撑脚",
                "title": "支撑脚老是偏外，怎么练？",
                "body": "上传了两段短传，系统提示支撑脚方向和出球线路不一致。",
                "ai_reply": "Kick AI：先做 8 米墙传，支撑脚脚尖固定朝目标，每组 20 次。",
                "likes": 12,
                "comment_count": 3,
                "created_at": _now_iso(),
            },
            {
                "id": "seed-shot-power-chain",
                "user_name": "左脚想开窍",
                "region": "重庆",
                "badge": "射门 · 发力链",
                "title": "射门发力总是散",
                "body": "触球前身体后仰，球容易飘高，想找同城队友一起练。",
                "ai_reply": "Kick AI：优先看支撑脚落点和髋部带动，不要只加大摆腿。",
                "likes": 8,
                "comment_count": 1,
                "created_at": _now_iso(),
            },
        ],
        "comments": {},
        "venue_corrections": [],
        "coaches": [
            {
                "id": "coach-technique-online",
                "name": "技术动作私教",
                "region": "全国线上",
                "specialty": "传球 / 射门纠错",
                "price_text": "¥99 起",
                "description": "看你的分析报告，给 1 次线上动作点评和 1 组针对训练。",
                "rating": 4.8,
                "verified": True,
            },
            {
                "id": "coach-chongqing-local",
                "name": "重庆同城场地陪练",
                "region": "重庆",
                "specialty": "支撑脚、触球面、发力链",
                "price_text": "¥199 起",
                "description": "适合需要线下纠正支撑脚、触球面和射门发力链的用户。",
                "rating": 4.7,
                "verified": False,
            },
        ],
        "bookings": [],
    }
    DISCOVERY_DB_PATH.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
    return seed


def _read_db() -> dict[str, Any]:
    with DISCOVERY_LOCK:
        return _ensure_db()


def _write_db(data: dict[str, Any]) -> None:
    with DISCOVERY_LOCK:
        DISCOVERY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        DISCOVERY_DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class CommunityPostCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(
        default="kickai-demo-user",
        max_length=80,
        validation_alias=AliasChoices("user_id", "userId", "author_user_id", "authorUserId"),
    )
    user_name: str = Field(
        default="匿名球友",
        max_length=40,
        validation_alias=AliasChoices("user_name", "userName", "author_name", "authorName"),
    )
    region: str = Field(default="未知地区", max_length=40)
    badge: str = Field(default="训练讨论", max_length=40)
    title: str = Field(..., min_length=1, max_length=80)
    body: str = Field(..., min_length=1, max_length=600, validation_alias=AliasChoices("body", "content"))
    visibility: Literal["public", "mutual_follow", "private"] = "public"
    analysis_result_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("analysis_result_id", "analysisResultId"),
    )


class CommunityPostUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str = Field(
        default="kickai-demo-user",
        max_length=80,
        validation_alias=AliasChoices("user_id", "userId", "author_user_id", "authorUserId"),
    )
    title: str | None = Field(default=None, min_length=1, max_length=80)
    body: str | None = Field(
        default=None,
        min_length=1,
        max_length=600,
        validation_alias=AliasChoices("body", "content"),
    )
    badge: str | None = Field(default=None, max_length=40)
    visibility: Literal["public", "mutual_follow", "private"] | None = None


class CommunityCommentCreate(BaseModel):
    user_name: str = Field(default="匿名球友", max_length=40)
    body: str = Field(..., min_length=1, max_length=400)


class VenueCorrectionCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    venue_id: str | None = Field(default=None, validation_alias=AliasChoices("venue_id", "venueId"))
    name: str = Field(..., min_length=1, max_length=120)
    region: str = Field(default="未知地区", max_length=80)
    address: str | None = Field(default=None, max_length=240)
    price_text: str | None = Field(default=None, max_length=80, validation_alias=AliasChoices("price_text", "priceText"))
    turf_type: str | None = Field(default=None, max_length=80, validation_alias=AliasChoices("turf_type", "turfType"))
    lighting: str | None = Field(default=None, max_length=80)
    open_time: str | None = Field(default=None, max_length=120, validation_alias=AliasChoices("open_time", "openTime"))
    note: str | None = Field(default=None, max_length=400)
    reporter_name: str = Field(default="匿名球友", max_length=40, validation_alias=AliasChoices("reporter_name", "reporterName"))


class CoachBookingCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    coach_id: str = Field(validation_alias=AliasChoices("coach_id", "coachId"))
    user_name: str = Field(default="匿名用户", max_length=40, validation_alias=AliasChoices("user_name", "userName"))
    contact: str = Field(..., min_length=1, max_length=80)
    region: str = Field(default="未填写", max_length=80)
    goal: str = Field(..., min_length=1, max_length=400)
    preferred_time: str | None = Field(default=None, max_length=120, validation_alias=AliasChoices("preferred_time", "preferredTime"))
    analysis_result_id: str | None = Field(default=None, validation_alias=AliasChoices("analysis_result_id", "analysisResultId"))


class CoachConversationCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    coach_id: str = Field(validation_alias=AliasChoices("coach_id", "coachId"))
    user_id: str = Field(
        default="kickai-demo-user",
        max_length=80,
        validation_alias=AliasChoices("user_id", "userId"),
    )
    user_name: str = Field(
        default="KickAI 用户",
        max_length=40,
        validation_alias=AliasChoices("user_name", "userName"),
    )
    region: str = Field(default="未填写", max_length=80)
    initial_message: str | None = Field(
        default=None,
        max_length=600,
        validation_alias=AliasChoices("initial_message", "initialMessage"),
    )
    analysis_result_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("analysis_result_id", "analysisResultId"),
    )


class CoachMessageCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sender_id: str = Field(
        default="kickai-demo-user",
        max_length=80,
        validation_alias=AliasChoices("sender_id", "senderId"),
    )
    sender_name: str = Field(
        default="KickAI 用户",
        max_length=40,
        validation_alias=AliasChoices("sender_name", "senderName"),
    )
    body: str = Field(..., min_length=1, max_length=800, validation_alias=AliasChoices("body", "content", "message"))


def _provider_keys() -> dict[str, bool]:
    osm_enabled = os.getenv("KICK_ENABLE_OSM_FALLBACK", "1").strip().lower() not in {"0", "false", "no"}
    return {
        "amap": bool(os.getenv("KICK_AMAP_KEY")),
        "baidu": bool(os.getenv("KICK_BAIDU_MAP_AK")),
        "tencent": bool(os.getenv("KICK_TENCENT_MAP_KEY")),
        "osm": osm_enabled,
    }


def _http_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "KickAI/1.0"})
    with urllib.request.urlopen(request, timeout=DISCOVERY_TIMEOUT_S) as response:
        body = response.read()
    return json.loads(body.decode("utf-8"))


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _split_lng_lat(location: str | None) -> tuple[float | None, float | None]:
    if not location or "," not in location:
        return None, None
    lng_text, lat_text = location.split(",", 1)
    return _safe_float(lng_text), _safe_float(lat_text)


def _normalise_venue(
    *,
    source: str,
    provider_id: str,
    name: str,
    address: str | None,
    lng: float | None,
    lat: float | None,
    phone: str | None = None,
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"{source}:{provider_id or uuid.uuid4().hex[:10]}",
        "name": name,
        "address": address or "地址待补充",
        "longitude": lng,
        "latitude": lat,
        "phone": phone,
        "source": source,
        "source_label": {
            "amap": "高德地图",
            "baidu": "百度地图",
            "tencent": "腾讯地图",
            "osm": "OpenStreetMap",
            "user_correction": "用户纠错",
            "venue_owner": "球场认证",
        }.get(source, source),
        "reliability_label": "地图来源" if source in {"amap", "baidu", "tencent", "osm"} else "用户校验",
        "last_verified_at": None,
        "raw": raw or {},
    }


def _search_amap(
    city: str,
    district: str | None,
    keyword: str,
    latitude: float | None,
    longitude: float | None,
    radius: int,
) -> list[dict[str, Any]]:
    key = os.getenv("KICK_AMAP_KEY")
    if not key:
        return []
    params = {
        "key": key,
        "keywords": keyword,
        "offset": "20",
        "page": "1",
        "extensions": "base",
    }
    if latitude is not None and longitude is not None:
        endpoint = "https://restapi.amap.com/v3/place/around"
        params.update({"location": f"{longitude},{latitude}", "radius": str(radius)})
    else:
        endpoint = "https://restapi.amap.com/v3/place/text"
        if city:
            params.update({"city": city, "citylimit": "true"})
    payload = _http_json(endpoint + "?" + urllib.parse.urlencode(params))
    if str(payload.get("status") or "") != "1":
        info = payload.get("info") or "amap_request_failed"
        infocode = payload.get("infocode") or "unknown"
        raise RuntimeError(f"{info} ({infocode})")
    venues = []
    pois = payload.get("pois") or []
    if district and latitude is None and longitude is None:
        pois = [
            poi
            for poi in pois
            if district in str(poi.get("adname") or "")
            or district in str(poi.get("address") or "")
            or district in str(poi.get("name") or "")
        ]
    for poi in pois:
        lng, lat = _split_lng_lat(poi.get("location"))
        venues.append(
            _normalise_venue(
                source="amap",
                provider_id=str(poi.get("id") or ""),
                name=str(poi.get("name") or "未命名球场"),
                address=str(poi.get("address") or ""),
                lng=lng,
                lat=lat,
                phone=str(poi.get("tel") or "") or None,
                raw={"type": poi.get("type"), "distance": poi.get("distance")},
            )
        )
    return venues


def _search_baidu(city: str, keyword: str) -> list[dict[str, Any]]:
    key = os.getenv("KICK_BAIDU_MAP_AK")
    if not key:
        return []
    params = {
        "ak": key,
        "query": keyword,
        "region": city,
        "output": "json",
        "page_size": "20",
    }
    payload = _http_json("https://api.map.baidu.com/place/v3/region?" + urllib.parse.urlencode(params))
    venues = []
    for poi in payload.get("results") or []:
        location = poi.get("location") or {}
        venues.append(
            _normalise_venue(
                source="baidu",
                provider_id=str(poi.get("uid") or ""),
                name=str(poi.get("name") or "未命名球场"),
                address=str(poi.get("address") or ""),
                lng=_safe_float(location.get("lng")),
                lat=_safe_float(location.get("lat")),
                phone=str(poi.get("telephone") or "") or None,
                raw={"province": poi.get("province"), "city": poi.get("city"), "area": poi.get("area")},
            )
        )
    return venues


def _search_tencent(city: str, keyword: str) -> list[dict[str, Any]]:
    key = os.getenv("KICK_TENCENT_MAP_KEY")
    if not key:
        return []
    boundary = f"region({city},0)"
    params = {
        "key": key,
        "keyword": keyword,
        "boundary": boundary,
        "page_size": "20",
        "page_index": "1",
    }
    payload = _http_json("https://apis.map.qq.com/ws/place/v1/search?" + urllib.parse.urlencode(params))
    venues = []
    for poi in payload.get("data") or []:
        location = poi.get("location") or {}
        venues.append(
            _normalise_venue(
                source="tencent",
                provider_id=str(poi.get("id") or ""),
                name=str(poi.get("title") or "未命名球场"),
                address=str(poi.get("address") or ""),
                lng=_safe_float(location.get("lng")),
                lat=_safe_float(location.get("lat")),
                phone=str(poi.get("tel") or "") or None,
                raw={"category": poi.get("category"), "ad_info": poi.get("ad_info")},
            )
        )
    return venues


def _search_osm_text(city: str, keyword: str) -> list[dict[str, Any]]:
    query = " ".join(part for part in [city, keyword] if part)
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": "20",
        "countrycodes": "cn",
        "accept-language": "zh-CN",
    }
    payload = _http_json("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params))
    venues = []
    for poi in payload if isinstance(payload, list) else []:
        display_name = str(poi.get("display_name") or "")
        name = str(poi.get("name") or "").strip() or display_name.split(",", 1)[0].strip() or "OpenStreetMap 球场"
        venues.append(
            _normalise_venue(
                source="osm",
                provider_id=str(poi.get("osm_id") or poi.get("place_id") or ""),
                name=name,
                address=display_name,
                lng=_safe_float(poi.get("lon")),
                lat=_safe_float(poi.get("lat")),
                raw={"class": poi.get("class"), "type": poi.get("type"), "importance": poi.get("importance")},
            )
        )
    return venues


def _search_osm_around(latitude: float, longitude: float, radius: int) -> list[dict[str, Any]]:
    safe_radius = max(500, min(radius, 20000))
    query = f"""
    [out:json][timeout:8];
    (
      node(around:{safe_radius},{latitude},{longitude})["leisure"="pitch"]["sport"~"soccer|football",i];
      way(around:{safe_radius},{latitude},{longitude})["leisure"="pitch"]["sport"~"soccer|football",i];
      relation(around:{safe_radius},{latitude},{longitude})["leisure"="pitch"]["sport"~"soccer|football",i];
      node(around:{safe_radius},{latitude},{longitude})["name"~"足球|football|soccer",i];
      way(around:{safe_radius},{latitude},{longitude})["name"~"足球|football|soccer",i];
      relation(around:{safe_radius},{latitude},{longitude})["name"~"足球|football|soccer",i];
    );
    out center tags 30;
    """
    payload = _http_json("https://overpass-api.de/api/interpreter?" + urllib.parse.urlencode({"data": query}))
    venues = []
    for element in payload.get("elements") or []:
        tags = element.get("tags") or {}
        center = element.get("center") or {}
        lat = _safe_float(element.get("lat")) or _safe_float(center.get("lat"))
        lng = _safe_float(element.get("lon")) or _safe_float(center.get("lon"))
        name = str(tags.get("name") or tags.get("name:zh") or tags.get("name:en") or "OpenStreetMap 足球场")
        address = ", ".join(
            str(value)
            for value in [
                tags.get("addr:province"),
                tags.get("addr:city"),
                tags.get("addr:district"),
                tags.get("addr:street"),
            ]
            if value
        )
        venues.append(
            _normalise_venue(
                source="osm",
                provider_id=f"{element.get('type')}:{element.get('id')}",
                name=name,
                address=address or "OpenStreetMap 开放数据，地址待校验",
                lng=lng,
                lat=lat,
                raw={"osm_type": element.get("type"), "tags": tags},
            )
        )
    return venues


def _dedupe_venues(venues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weights = {"venue_owner": 6, "user_correction": 5, "amap": 4, "tencent": 3, "baidu": 2, "osm": 1}
    by_key: dict[str, dict[str, Any]] = {}
    for venue in venues:
        key = f"{venue.get('name', '').strip()}::{venue.get('address', '').strip()}"
        existing = by_key.get(key)
        if existing is None or weights.get(str(venue.get("source")), 0) > weights.get(str(existing.get("source")), 0):
            by_key[key] = venue
    return sorted(by_key.values(), key=lambda item: (str(item.get("source") or ""), str(item.get("name") or "")))


def _normalise_post(post: dict[str, Any]) -> dict[str, Any]:
    user_name = str(post.get("user_name") or "匿名球友").strip() or "匿名球友"
    post.setdefault("user_id", f"user-{uuid.uuid5(uuid.NAMESPACE_URL, user_name).hex[:12]}")
    post.setdefault("visibility", "public")
    post.setdefault("updated_at", None)
    return post


def _visible_to_viewer(post: dict[str, Any], viewer_user_id: str | None) -> bool:
    post = _normalise_post(post)
    visibility = str(post.get("visibility") or "public")
    author_id = str(post.get("user_id") or "")
    viewer_id = str(viewer_user_id or "")
    if visibility == "private":
        return bool(viewer_id and viewer_id == author_id)
    if visibility == "mutual_follow":
        if viewer_id and viewer_id == author_id:
            return True
        mutual_followers = {str(item) for item in post.get("mutual_followers") or []}
        return bool(viewer_id and viewer_id in mutual_followers)
    return True


def _normalise_conversation(conversation: dict[str, Any]) -> dict[str, Any]:
    conversation.setdefault("messages", [])
    conversation.setdefault("status", "open")
    conversation.setdefault("updated_at", conversation.get("created_at") or _now_iso())
    return conversation


@router.get("/config")
def discovery_config():
    keys = _provider_keys()
    return {
        "status": "ok",
        "venue_provider_keys": keys,
        "venue_search_ready": any(keys.values()),
        "poi_provider_env_keys": {
            "amap": "KICK_AMAP_KEY",
            "baidu": "KICK_BAIDU_MAP_AK",
            "tencent": "KICK_TENCENT_MAP_KEY",
            "osm": "KICK_ENABLE_OSM_FALLBACK",
        },
        "storage_path": str(DISCOVERY_DB_PATH),
        "features": {
            "community_posts": True,
            "venue_poi_search": any(keys.values()),
            "venue_user_correction": True,
            "coach_booking": True,
            "coach_chat": True,
        },
    }


@router.get("/community/posts")
def list_posts(
    region: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    viewer_user_id: str | None = "kickai-demo-user",
):
    db = _read_db()
    posts = [_normalise_post(dict(post)) for post in list(db.get("posts") or [])]
    posts = [post for post in posts if _visible_to_viewer(post, viewer_user_id)]
    if region:
        posts = [post for post in posts if region in str(post.get("region") or "")]
    posts.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {"status": "ok", "items": posts[:limit]}


@router.post("/community/posts")
def create_post(req: CommunityPostCreate):
    db = _read_db()
    post = {
        "id": f"post-{uuid.uuid4().hex[:12]}",
        "user_id": req.user_id.strip() or "kickai-demo-user",
        "user_name": req.user_name.strip() or "匿名球友",
        "region": req.region.strip() or "未知地区",
        "badge": req.badge.strip() or "训练讨论",
        "title": req.title.strip(),
        "body": req.body.strip(),
        "visibility": req.visibility,
        "analysis_result_id": req.analysis_result_id,
        "ai_reply": "Kick AI：已收到这条训练讨论。后续会结合你的分析报告生成更具体的训练建议。",
        "likes": 0,
        "comment_count": 0,
        "created_at": _now_iso(),
        "updated_at": None,
    }
    db.setdefault("posts", []).insert(0, post)
    _write_db(db)
    return {"status": "ok", "item": post}


@router.get("/community/posts/{post_id}")
def get_post(post_id: str, viewer_user_id: str | None = "kickai-demo-user"):
    db = _read_db()
    post = next((item for item in db.get("posts") or [] if item.get("id") == post_id), None)
    if post is None:
        return {"status": "error", "error_code": "post_not_found", "message": "帖子不存在"}
    post = _normalise_post(dict(post))
    if not _visible_to_viewer(post, viewer_user_id):
        return {"status": "error", "error_code": "post_not_visible", "message": "当前可见范围不允许查看"}
    return {"status": "ok", "item": post}


@router.put("/community/posts/{post_id}")
def update_post(post_id: str, req: CommunityPostUpdate):
    db = _read_db()
    for post in db.get("posts") or []:
        if post.get("id") != post_id:
            continue
        _normalise_post(post)
        if str(post.get("user_id") or "") != (req.user_id.strip() or "kickai-demo-user"):
            return {"status": "error", "error_code": "permission_denied", "message": "只能编辑自己发布的帖子"}
        if req.title is not None:
            post["title"] = req.title.strip()
        if req.body is not None:
            post["body"] = req.body.strip()
        if req.badge is not None:
            post["badge"] = req.badge.strip() or "训练讨论"
        if req.visibility is not None:
            post["visibility"] = req.visibility
        post["updated_at"] = _now_iso()
        _write_db(db)
        return {"status": "ok", "item": post}
    return {"status": "error", "error_code": "post_not_found", "message": "帖子不存在"}


@router.get("/community/users/{user_id}/posts")
def list_user_posts(
    user_id: str,
    viewer_user_id: str | None = "kickai-demo-user",
    limit: int = Query(default=50, ge=1, le=100),
):
    db = _read_db()
    posts = [
        _normalise_post(dict(post))
        for post in db.get("posts") or []
        if str(post.get("user_id") or "") == user_id
    ]
    posts = [post for post in posts if _visible_to_viewer(post, viewer_user_id)]
    posts.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {"status": "ok", "items": posts[:limit]}


@router.post("/community/posts/{post_id}/like")
def like_post(post_id: str):
    db = _read_db()
    for post in db.get("posts") or []:
        if post.get("id") == post_id:
            _normalise_post(post)
            post["likes"] = int(post.get("likes") or 0) + 1
            _write_db(db)
            return {"status": "ok", "item": post}
    return {"status": "error", "error_code": "post_not_found", "message": "帖子不存在"}


@router.get("/community/posts/{post_id}/comments")
def list_comments(post_id: str):
    db = _read_db()
    return {"status": "ok", "items": list((db.get("comments") or {}).get(post_id) or [])}


@router.post("/community/posts/{post_id}/comments")
def create_comment(post_id: str, req: CommunityCommentCreate):
    db = _read_db()
    post = next((item for item in db.get("posts") or [] if item.get("id") == post_id), None)
    if post is None:
        return {"status": "error", "error_code": "post_not_found", "message": "帖子不存在"}
    comment = {
        "id": f"comment-{uuid.uuid4().hex[:12]}",
        "post_id": post_id,
        "user_name": req.user_name.strip() or "匿名球友",
        "body": req.body.strip(),
        "created_at": _now_iso(),
    }
    comments = db.setdefault("comments", {}).setdefault(post_id, [])
    comments.append(comment)
    post["comment_count"] = int(post.get("comment_count") or 0) + 1
    _write_db(db)
    return {"status": "ok", "item": comment}


@router.get("/venues/search")
def search_venues(
    city: str = "",
    district: str | None = None,
    keyword: str = "足球场",
    latitude: float | None = None,
    longitude: float | None = None,
    radius: int = Query(default=10000, ge=500, le=50000),
    provider: Literal["all", "amap", "baidu", "tencent", "osm"] = "all",
):
    db = _read_db()
    city = (city or "").strip()
    district = (district or "").strip() or None
    has_coordinate = latitude is not None and longitude is not None
    search_district = None if has_coordinate else district
    region = f"{city}{district or ''}".strip()
    if not region:
        region = "当前位置" if has_coordinate else ""
    keys = _provider_keys()
    provider_results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    venues: list[dict[str, Any]] = []
    keywords = [keyword, "五人制足球场", "七人制足球场"] if keyword == "足球场" else [keyword]

    def should_run(name: str) -> bool:
        return provider in {"all", name}

    for search_keyword in keywords:
        if should_run("amap") and keys["amap"]:
            try:
                items = _search_amap(city, search_district, search_keyword, latitude, longitude, radius)
                venues.extend(items)
                provider_results["amap"] = provider_results.get("amap", 0) + len(items)
            except Exception as exc:
                errors["amap"] = f"{type(exc).__name__}: {exc}"
        if region and should_run("baidu") and keys["baidu"]:
            try:
                items = _search_baidu(region, search_keyword)
                venues.extend(items)
                provider_results["baidu"] = provider_results.get("baidu", 0) + len(items)
            except Exception as exc:
                errors["baidu"] = f"{type(exc).__name__}: {exc}"
        if region and should_run("tencent") and keys["tencent"]:
            try:
                items = _search_tencent(region, search_keyword)
                venues.extend(items)
                provider_results["tencent"] = provider_results.get("tencent", 0) + len(items)
            except Exception as exc:
                errors["tencent"] = f"{type(exc).__name__}: {exc}"

    if should_run("osm") and keys["osm"]:
        try:
            items: list[dict[str, Any]] = []
            if latitude is not None and longitude is not None:
                items = _search_osm_around(latitude, longitude, radius)
            if not items and region:
                items = _search_osm_text(region, keyword)
            venues.extend(items)
            provider_results["osm"] = provider_results.get("osm", 0) + len(items)
        except Exception as exc:
            errors["osm"] = f"{type(exc).__name__}: {exc}"
            if region:
                try:
                    items = _search_osm_text(region, keyword)
                    venues.extend(items)
                    provider_results["osm"] = provider_results.get("osm", 0) + len(items)
                except Exception as fallback_exc:
                    errors["osm_fallback"] = f"{type(fallback_exc).__name__}: {fallback_exc}"

    for correction in db.get("venue_corrections") or []:
        correction_region = str(correction.get("region") or "")
        if region and city and city in correction_region and (not district or district in correction_region):
            venues.append(
                _normalise_venue(
                    source="user_correction",
                    provider_id=str(correction.get("id") or ""),
                    name=str(correction.get("name") or "用户补充球场"),
                    address=str(correction.get("address") or "地址待补充"),
                    lng=None,
                    lat=None,
                    phone=None,
                    raw=correction,
                )
            )

    items = _dedupe_venues(venues)
    return {
        "status": "ok",
        "query": {
            "city": city,
            "district": district,
            "keyword": keyword,
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "provider": provider,
        },
        "provider_keys": keys,
        "venue_search_ready": any(keys.values()),
        "provider_result_count": provider_results,
        "provider_errors": errors,
        "items": items,
        "setup_hint": None
        if any(keys.values())
        else "请先配置 KICK_AMAP_KEY、KICK_BAIDU_MAP_AK 或 KICK_TENCENT_MAP_KEY，才能拉取真实地图 POI。",
    }


@router.post("/venues/corrections")
def create_venue_correction(req: VenueCorrectionCreate):
    db = _read_db()
    item = {
        "id": f"venue-correction-{uuid.uuid4().hex[:12]}",
        "venue_id": req.venue_id,
        "name": req.name.strip(),
        "region": req.region.strip() or "未知地区",
        "address": req.address,
        "price_text": req.price_text,
        "turf_type": req.turf_type,
        "lighting": req.lighting,
        "open_time": req.open_time,
        "note": req.note,
        "reporter_name": req.reporter_name.strip() or "匿名球友",
        "created_at": _now_iso(),
    }
    db.setdefault("venue_corrections", []).append(item)
    _write_db(db)
    return {"status": "ok", "item": item}


@router.get("/coaches")
def list_coaches(region: str | None = None):
    db = _read_db()
    coaches = list(db.get("coaches") or [])
    if region:
        coaches = [coach for coach in coaches if region in str(coach.get("region") or "") or "全国" in str(coach.get("region") or "")]
    return {"status": "ok", "items": coaches}


@router.post("/coaches/bookings")
def create_coach_booking(req: CoachBookingCreate):
    db = _read_db()
    coach = next((item for item in db.get("coaches") or [] if item.get("id") == req.coach_id), None)
    if coach is None:
        return {"status": "error", "error_code": "coach_not_found", "message": "教练不存在"}
    booking = {
        "id": f"booking-{uuid.uuid4().hex[:12]}",
        "coach_id": req.coach_id,
        "coach_name": coach.get("name"),
        "user_name": req.user_name.strip() or "匿名用户",
        "contact": req.contact.strip(),
        "region": req.region.strip() or "未填写",
        "goal": req.goal.strip(),
        "preferred_time": req.preferred_time,
        "analysis_result_id": req.analysis_result_id,
        "status": "pending_contact",
        "created_at": _now_iso(),
    }
    db.setdefault("bookings", []).insert(0, booking)
    _write_db(db)
    return {"status": "ok", "item": booking}


@router.get("/coaches/bookings")
def list_bookings():
    db = _read_db()
    return {"status": "ok", "items": list(db.get("bookings") or [])}


@router.post("/coaches/conversations")
def create_coach_conversation(req: CoachConversationCreate):
    db = _read_db()
    coach = next((item for item in db.get("coaches") or [] if item.get("id") == req.coach_id), None)
    if coach is None:
        return {"status": "error", "error_code": "coach_not_found", "message": "教练不存在"}

    user_id = req.user_id.strip() or "kickai-demo-user"
    conversations = db.setdefault("coach_conversations", [])
    existing = next(
        (
            item
            for item in conversations
            if item.get("coach_id") == req.coach_id
            and item.get("user_id") == user_id
            and item.get("status") != "closed"
        ),
        None,
    )

    if existing is None:
        now = _now_iso()
        existing = {
            "id": f"coach-chat-{uuid.uuid4().hex[:12]}",
            "coach_id": req.coach_id,
            "coach_name": coach.get("name"),
            "user_id": user_id,
            "user_name": req.user_name.strip() or "KickAI 用户",
            "region": req.region.strip() or "未填写",
            "analysis_result_id": req.analysis_result_id,
            "status": "open",
            "created_at": now,
            "updated_at": now,
            "messages": [
                {
                    "id": f"msg-{uuid.uuid4().hex[:12]}",
                    "conversation_id": "",
                    "sender_id": "coach-system",
                    "sender_name": coach.get("name") or "私教",
                    "role": "coach",
                    "body": "你好，我已经收到你的私教咨询。你可以把本次分析报告的问题点、想提升的动作和方便训练时间发给我。",
                    "created_at": now,
                }
            ],
        }
        existing["messages"][0]["conversation_id"] = existing["id"]
        conversations.insert(0, existing)

    if req.initial_message and req.initial_message.strip():
        message = {
            "id": f"msg-{uuid.uuid4().hex[:12]}",
            "conversation_id": existing["id"],
            "sender_id": user_id,
            "sender_name": req.user_name.strip() or "KickAI 用户",
            "role": "user",
            "body": req.initial_message.strip(),
            "created_at": _now_iso(),
        }
        existing.setdefault("messages", []).append(message)

    existing["updated_at"] = _now_iso()
    _write_db(db)
    return {"status": "ok", "item": _normalise_conversation(existing)}


@router.get("/coaches/conversations/{conversation_id}")
def get_coach_conversation(conversation_id: str):
    db = _read_db()
    conversation = next(
        (item for item in db.get("coach_conversations") or [] if item.get("id") == conversation_id),
        None,
    )
    if conversation is None:
        return {"status": "error", "error_code": "conversation_not_found", "message": "会话不存在"}
    return {"status": "ok", "item": _normalise_conversation(conversation)}


@router.post("/coaches/conversations/{conversation_id}/messages")
def create_coach_message(conversation_id: str, req: CoachMessageCreate):
    db = _read_db()
    conversation = next(
        (item for item in db.get("coach_conversations") or [] if item.get("id") == conversation_id),
        None,
    )
    if conversation is None:
        return {"status": "error", "error_code": "conversation_not_found", "message": "会话不存在"}

    message = {
        "id": f"msg-{uuid.uuid4().hex[:12]}",
        "conversation_id": conversation_id,
        "sender_id": req.sender_id.strip() or "kickai-demo-user",
        "sender_name": req.sender_name.strip() or "KickAI 用户",
        "role": "user",
        "body": req.body.strip(),
        "created_at": _now_iso(),
    }
    conversation.setdefault("messages", []).append(message)
    conversation["updated_at"] = _now_iso()
    _write_db(db)
    return {"status": "ok", "item": _normalise_conversation(conversation)}
