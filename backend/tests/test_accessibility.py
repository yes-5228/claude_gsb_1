"""无障碍专项检查接口测试：判定规则、自动建单、达标率汇总。"""

FACILITIES = ["扶手", "坡道", "盲道", "专用间"]


def make_items(configured=True, condition="完好") -> list[dict]:
    return [
        {"facility": name, "configured": configured, "condition": condition if configured else None}
        for name in FACILITIES
    ]


def create_check(client, restroom_id, items, inspector="无障碍检查员") -> dict:
    response = client.post(
        "/api/v1/accessibility-checks",
        json={"restroom_id": restroom_id, "inspector": inspector, "items": items},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_verdict_rules_and_auto_issue(client, restroom):
    # 全部完好 -> 全部符合 -> 达标，不产生整改事项
    good = create_check(client, restroom["id"], make_items())
    assert good["result"] == "达标"
    assert good["score"] == 100.0
    assert good["compliant_count"] == 4
    assert good["issues"] == []
    assert all(item["verdict"] == "符合" for item in good["items"])

    # 轻微破损 -> 部分符合 -> 部分达标，达标率 87.5
    items = make_items()
    items[1]["condition"] = "轻微破损"
    partial = create_check(client, restroom["id"], items)
    assert partial["result"] == "部分达标"
    assert partial["partial_count"] == 1
    assert partial["score"] == 87.5
    assert partial["issues"] == []

    # 未配置 -> 不符合 -> 不达标，自动生成待整改事项
    items = make_items()
    items[2]["configured"] = False
    items[2]["condition"] = None
    failed = create_check(client, restroom["id"], items)
    assert failed["result"] == "不达标"
    assert failed["failed_count"] == 1
    assert failed["score"] == 75.0
    blind = next(item for item in failed["items"] if item["facility"] == "盲道")
    assert blind["condition"] == "未配置"
    assert blind["verdict"] == "不符合"
    assert len(failed["issues"]) == 1
    issue = failed["issues"][0]
    assert issue["title"] == "无障碍盲道未配置"
    assert issue["status"] == "待整改"

    # 生成的问题可回查来源检查记录
    detail = client.get(f"/api/v1/issues/{issue['id']}").json()
    assert detail["category"] == "设施损坏"
    assert detail["accessibility_check_id"] == failed["id"]
    assert detail["records"][0]["action"] == "上报问题"

    # 严重损坏 -> 不符合
    items = make_items()
    items[0]["condition"] = "严重损坏"
    broken = create_check(client, restroom["id"], items)
    assert broken["result"] == "不达标"
    assert len(broken["issues"]) == 1
    assert broken["issues"][0]["title"] == "无障碍扶手严重损坏"


def test_failed_item_issue_dedup(client, restroom):
    items = make_items()
    items[3]["configured"] = False
    items[3]["condition"] = None

    first = create_check(client, restroom["id"], items)
    assert len(first["issues"]) == 1

    # 同一设施已有未闭环事项时不重复建单
    second = create_check(client, restroom["id"], items)
    assert second["failed_count"] == 1
    assert second["issues"] == []

    # 事项关闭后再次检出同一问题，重新建单
    issue_id = first["issues"][0]["id"]
    closed = client.post(
        f"/api/v1/issues/{issue_id}/transitions",
        json={"to_status": "已关闭", "operator": "值班长"},
    )
    assert closed.status_code == 200
    third = create_check(client, restroom["id"], items)
    assert len(third["issues"]) == 1


def test_required_facilities_validation(client, restroom):
    # 缺少必检设施
    missing = client.post(
        "/api/v1/accessibility-checks",
        json={"restroom_id": restroom["id"], "inspector": "检查员", "items": make_items()[:3]},
    )
    assert missing.status_code == 400
    assert "专用间" in missing.json()["detail"]

    # 同一设施重复登记
    duplicated = client.post(
        "/api/v1/accessibility-checks",
        json={
            "restroom_id": restroom["id"],
            "inspector": "检查员",
            "items": make_items() + [make_items()[0]],
        },
    )
    assert duplicated.status_code == 400
    assert "重复" in duplicated.json()["detail"]

    # 非法设施类型
    invalid = client.post(
        "/api/v1/accessibility-checks",
        json={
            "restroom_id": restroom["id"],
            "inspector": "检查员",
            "items": [{"facility": "电梯", "configured": True, "condition": "完好"}],
        },
    )
    assert invalid.status_code == 422


def test_list_filters_and_delete(client, restroom):
    create_check(client, restroom["id"], make_items())
    items = make_items()
    items[0]["condition"] = "严重损坏"
    bad = create_check(client, restroom["id"], items)

    failed = client.get(
        "/api/v1/accessibility-checks",
        params={"result": "不达标", "restroom_id": restroom["id"]},
    ).json()
    assert failed["meta"]["total"] == 1
    assert failed["items"][0]["id"] == bad["id"]

    by_district = client.get("/api/v1/accessibility-checks", params={"district": "测试区"}).json()
    assert by_district["meta"]["total"] >= 2

    detail = client.get(f"/api/v1/accessibility-checks/{bad['id']}").json()
    assert detail["issues"][0]["title"] == "无障碍扶手严重损坏"

    # 删除检查记录后，已生成的整改事项保留但解除关联
    issue_id = detail["issues"][0]["id"]
    assert client.delete(f"/api/v1/accessibility-checks/{bad['id']}").status_code == 200
    assert client.get(f"/api/v1/accessibility-checks/{bad['id']}").status_code == 404
    issue = client.get(f"/api/v1/issues/{issue_id}").json()
    assert issue["accessibility_check_id"] is None


def test_summary_aggregation(client):
    def add_restroom(name):
        response = client.post(
            "/api/v1/restrooms",
            json={"name": name, "district": "汇总区", "address": "汇总路 1 号"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    room_pass = add_restroom("汇总公厕甲")
    room_fail = add_restroom("汇总公厕乙")
    room_idle = add_restroom("汇总公厕丙")  # 不开展检查，计入未检查

    create_check(client, room_pass["id"], make_items())
    items = make_items()
    items[0]["configured"] = False
    items[0]["condition"] = None
    create_check(client, room_fail["id"], items)

    summary = client.get("/api/v1/accessibility-checks/summary").json()
    assert summary["total_checks"] >= 2
    assert summary["failed_items"] >= 1
    assert summary["open_issue_count"] >= 1

    district = next(item for item in summary["districts"] if item["district"] == "汇总区")
    assert district["restroom_count"] == 3
    assert district["inspected_count"] == 2
    assert district["uninspected_count"] == 1
    assert district["compliant_count"] == 1
    assert district["failed_count"] == 1
    assert district["pass_rate"] == 33.3
    assert district["avg_score"] == 87.5
    assert district["open_issue_count"] == 1

    rows = {item["code"]: item for item in summary["restrooms"]}
    assert rows[room_pass["code"]]["last_result"] == "达标"
    assert rows[room_pass["code"]]["last_score"] == 100.0
    assert rows[room_fail["code"]]["last_result"] == "不达标"
    assert rows[room_fail["code"]]["open_issue_count"] == 1
    assert rows[room_idle["code"]]["last_result"] == "未检查"
    assert rows[room_idle["code"]]["check_count"] == 0
