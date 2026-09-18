"""无障碍设施专项检查接口测试。"""

from datetime import datetime, timedelta

RESOURCE = "/api/v1/accessibility-inspections"


def make_items(handrail="完好", ramp="轻微破损", tactile="严重损坏", stall=None) -> list[dict]:
    """构造四项设施登记：stall=None 表示未配置无障碍专用间。"""
    items = [
        {"key": "handrail", "configured": True, "condition": handrail},
        {"key": "ramp", "configured": True, "condition": ramp},
        {"key": "tactile_path", "configured": True, "condition": tactile},
    ]
    if stall is None:
        items.append({"key": "accessible_stall", "configured": False})
    else:
        items.append({"key": "accessible_stall", "configured": True, "condition": stall})
    return items


def create_record(client, restroom_id, items=None, inspector="张检查") -> dict:
    response = client.post(
        RESOURCE,
        json={
            "restroom_id": restroom_id,
            "inspector": inspector,
            "items": items if items is not None else make_items(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_accessibility_judgement_and_auto_issues(client, restroom):
    record = create_record(client, restroom["id"])

    conformity_by_key = {item["key"]: item["conformity"] for item in record["items"]}
    assert conformity_by_key == {
        "handrail": "符合",
        "ramp": "部分符合",
        "tactile_path": "不符合",
        "accessible_stall": "不符合",
    }
    assert record["compliant_count"] == 1
    assert record["partial_count"] == 1
    assert record["non_compliant_count"] == 2
    assert record["rate"] == 37.5
    assert record["conformity"] == "不符合"

    # 两个不符合项各自生成一条待整改工单
    assert len(record["issues"]) == 2
    titles = {issue["title"] for issue in record["issues"]}
    assert titles == {"盲道不符合无障碍检查标准", "无障碍专用间不符合无障碍检查标准"}
    assert all(issue["status"] == "待整改" for issue in record["issues"])

    # 工单进入问题模块，可按分类过滤，且回链到本次检查
    issues = client.get(
        "/api/v1/issues", params={"category": "无障碍设施", "restroom_id": restroom["id"]}
    ).json()
    assert issues["meta"]["total"] == 2
    for issue in issues["items"]:
        assert issue["accessibility_inspection_id"] == record["id"]
        assert issue["category"] == "无障碍设施"
        assert issue["reporter"] == "张检查"
    severity_by_title = {issue["title"]: issue["severity"] for issue in issues["items"]}
    assert severity_by_title["无障碍专用间不符合无障碍检查标准"] == "严重"  # 未配置
    assert severity_by_title["盲道不符合无障碍检查标准"] == "一般"  # 严重损坏


def test_accessibility_issue_dedup(client, restroom):
    first = create_record(client, restroom["id"])
    assert len(first["issues"]) == 2

    # 复查时同一设施仍不符合，但已有未闭环工单，不重复生成
    second = create_record(client, restroom["id"])
    assert second["issues"] == []

    total = client.get(
        "/api/v1/issues", params={"category": "无障碍设施", "restroom_id": restroom["id"]}
    ).json()["meta"]["total"]
    assert total == 2


def test_accessibility_validation(client, restroom):
    unknown = client.post(
        RESOURCE,
        json={
            "restroom_id": restroom["id"],
            "inspector": "张检查",
            "items": [{"key": "elevator", "configured": True, "condition": "完好"}],
        },
    )
    assert unknown.status_code == 400
    assert "未知的无障碍检查项" in unknown.json()["detail"]

    duplicate = client.post(
        RESOURCE,
        json={
            "restroom_id": restroom["id"],
            "inspector": "张检查",
            "items": [
                {"key": "ramp", "configured": True, "condition": "完好"},
                {"key": "ramp", "configured": True, "condition": "轻微破损"},
            ],
        },
    )
    assert duplicate.status_code == 400
    assert "重复提交" in duplicate.json()["detail"]

    missing_condition = client.post(
        RESOURCE,
        json={
            "restroom_id": restroom["id"],
            "inspector": "张检查",
            "items": [{"key": "ramp", "configured": True}],
        },
    )
    assert missing_condition.status_code == 400
    assert "完好状态" in missing_condition.json()["detail"]

    empty = client.post(
        RESOURCE,
        json={"restroom_id": restroom["id"], "inspector": "张检查", "items": []},
    )
    assert empty.status_code == 422


def test_accessibility_summary(client):
    """用两个专属区域的公厕验证汇总口径，避免与同库其他用例互相干扰。"""
    bad_room = client.post(
        "/api/v1/restrooms",
        json={"name": "汇总甲区公厕", "district": "汇总甲区", "address": "甲路 1 号"},
    ).json()
    good_room = client.post(
        "/api/v1/restrooms",
        json={"name": "汇总乙区公厕", "district": "汇总乙区", "address": "乙路 1 号"},
    ).json()

    # 甲区公厕：2 不符合 -> 判定不符合，达标率 37.5
    bad_record = create_record(client, bad_room["id"])
    # 乙区公厕：全部完好 -> 判定符合，达标率 100
    good_record = create_record(
        client,
        good_room["id"],
        items=make_items(handrail="完好", ramp="完好", tactile="完好", stall="完好"),
    )

    summary = client.get(f"{RESOURCE}/summary").json()
    overall = summary["overall"]
    assert overall["inspection_total"] >= 2
    assert overall["restroom_covered"] >= 2
    assert overall["item_total"] >= 8
    assert overall["non_compliant_items"] >= 2
    assert overall["open_issue_count"] >= 2

    districts = {item["district"]: item for item in summary["districts"]}
    district_a = districts["汇总甲区"]
    assert district_a["restroom_count"] == 1
    assert district_a["inspected_count"] == 1
    assert district_a["non_compliant_count"] == 1
    assert district_a["avg_rate"] == 37.5
    assert district_a["open_issue_count"] == 2
    district_b = districts["汇总乙区"]
    assert district_b["compliant_count"] == 1
    assert district_b["avg_rate"] == 100.0
    assert district_b["open_issue_count"] == 0

    restrooms = {item["restroom_id"]: item for item in summary["restrooms"]}
    bad = restrooms[bad_room["id"]]
    assert bad["inspection_count"] == 1
    assert bad["latest_conformity"] == "不符合"
    assert bad["latest_rate"] == 37.5
    assert bad["avg_rate"] == 37.5
    assert bad["open_issue_count"] == 2
    good = restrooms[good_room["id"]]
    assert good["latest_conformity"] == "符合"
    assert good["latest_rate"] == 100.0
    assert bad_record["id"] != good_record["id"]


def test_accessibility_filters_and_update(client, restroom):
    bad = create_record(client, restroom["id"])
    good = create_record(
        client,
        restroom["id"],
        items=make_items(handrail="完好", ramp="完好", tactile="完好", stall="完好"),
        inspector="李复查",
    )

    scoped = {"restroom_id": restroom["id"]}
    filtered = client.get(RESOURCE, params={**scoped, "conformity": "符合"}).json()
    assert filtered["meta"]["total"] == 1
    assert filtered["items"][0]["id"] == good["id"]

    non_compliant = client.get(RESOURCE, params={**scoped, "conformity": "不符合"}).json()
    assert non_compliant["meta"]["total"] == 1
    assert non_compliant["items"][0]["id"] == bad["id"]

    by_inspector = client.get(RESOURCE, params={**scoped, "inspector": "李复查"}).json()
    assert by_inspector["meta"]["total"] == 1

    today = datetime.now().date().isoformat()
    ranged = client.get(
        RESOURCE, params={**scoped, "date_from": today, "date_to": today}
    ).json()
    assert ranged["meta"]["total"] == 2

    updated = client.patch(
        f"{RESOURCE}/{bad['id']}",
        json={"items": make_items(handrail="完好", ramp="完好", tactile="完好", stall="完好")},
    ).json()
    assert updated["conformity"] == "符合"
    assert updated["rate"] == 100.0
    assert updated["non_compliant_count"] == 0

    removed = client.delete(f"{RESOURCE}/{good['id']}")
    assert removed.status_code == 200
    assert client.get(f"{RESOURCE}/{good['id']}").status_code == 404


def test_accessibility_delete_guard_and_dictionaries(client, restroom):
    payload = client.get("/api/v1/meta/dictionaries").json()
    assert [item["key"] for item in payload["accessibility_check_items"]] == [
        "handrail",
        "ramp",
        "tactile_path",
        "accessible_stall",
    ]
    assert payload["accessibility_conditions"] == ["完好", "轻微破损", "严重损坏"]
    assert payload["accessibility_conformity"] == ["符合", "部分符合", "不符合"]
    assert "无障碍设施" in payload["issue_category"]

    create_record(client, restroom["id"])
    blocked = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert blocked.status_code == 409
    assert "无障碍检查记录" in blocked.json()["detail"]

    ok = client.delete(f"/api/v1/restrooms/{restroom['id']}", params={"force": "true"})
    assert ok.status_code == 200


def test_accessibility_issue_lifecycle_link(client, restroom):
    """自动生成的工单可正常走整改闭环，超期口径与手工上报一致。"""
    record = create_record(client, restroom["id"])
    issue_id = record["issues"][0]["id"]

    detail = client.get(f"/api/v1/issues/{issue_id}").json()
    assert detail["accessibility_inspection_id"] == record["id"]
    assert detail["records"][0]["action"] == "上报问题"

    moved = client.post(
        f"/api/v1/issues/{issue_id}/transitions",
        json={"to_status": "整改中", "operator": "设施维修班", "remark": "已安排加固扶手"},
    )
    assert moved.status_code == 200

    # 整改期限按检查时间推算（未配置 3 天 / 严重损坏 7 天）
    assert detail["deadline"] is not None
    deadline = datetime.fromisoformat(detail["deadline"])
    inspect_time = datetime.fromisoformat(record["inspect_time"])
    assert deadline - inspect_time in (timedelta(days=3), timedelta(days=7))
