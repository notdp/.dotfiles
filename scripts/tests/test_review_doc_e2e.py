"""End-to-end acceptance for assist-review-doc.

Drives the full loop: baseline → render → simulated browser export →
diff → apply resolutions → re-render → verify second-round baseline.
The browser interaction is simulated by constructing the comments.json
payload that the in-page export button would produce.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import review_doc_consume  # noqa: E402
import review_doc_migrate  # noqa: E402

IDS = REPO_ROOT / "scripts" / "review_doc_ids.py"
RENDER = REPO_ROOT / "scripts" / "review_doc_render.py"
CONSUME = REPO_ROOT / "scripts" / "review_doc_consume.py"
MIGRATE = REPO_ROOT / "scripts" / "review_doc_migrate.py"


LONG_DOC = """# RBAC 产品方案 v0

## 概述

权限管理系统支持租户、用户、权限组、权限点四层模型。本文档规定 v0 阶段交付范围。

## 角色

- 超管：跨租户操作，能开通租户、分配租户管理员
- 租户管理员：本租户内的权限组、用户、绑定关系管理
- 普通用户：只能看分配到的功能

## 权限组创建

权限组由租户管理员在权限组页面创建，每个权限组有 name、slug、描述、所属租户字段。

## 权限点分配

权限点是最小授权单元，按资源动作组织（resource:action）。权限组通过 N:N 关联权限点。

## 人员管理

人员页面支持分配权限组、启用/停用、查看历史绑定记录。

## 边界

不做：跨租户权限共享、权限继承、自动同步外部 IdP。
"""


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", *args], text=True, capture_output=True)


class EndToEndAcceptanceTests(unittest.TestCase):
    def test_full_review_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doc = tmp_path / "rbac-overview.md"
            comments = tmp_path / "rbac-overview.comments.json"
            html = tmp_path / "rbac-overview.review.html"
            doc.write_text(LONG_DOC, encoding="utf-8")

            # Step 1: baseline init — write empty comments + render HTML
            initial = {
                "schema_version": 1,
                "spec_file": str(doc),
                "review_version": 0,
                "anchors": {},
            }
            review_doc_migrate.validate(initial)
            comments.write_text(json.dumps(initial, ensure_ascii=False), encoding="utf-8")

            render_result = _run_cli(
                str(RENDER), "--doc", str(doc), "--output", str(html), "--comments", str(comments)
            )
            self.assertEqual(render_result.returncode, 0, render_result.stderr)
            self.assertTrue(html.exists())
            html_text = html.read_text(encoding="utf-8")
            for anchor_id in ["概述", "角色", "权限组创建", "权限点分配", "人员管理", "边界"]:
                self.assertIn(f'data-review-id="{anchor_id}"', html_text, f"missing anchor {anchor_id}")

            # Step 2: ID stability check against the baseline (empty) — should pass
            verify_result = _run_cli(str(IDS), "verify", str(doc), str(comments))
            self.assertEqual(verify_result.returncode, 0, verify_result.stderr)

            # Step 3: simulate the browser export — user wrote 8 comments
            simulated_download = {
                "schema_version": 1,
                "spec_file": str(doc),
                "review_version": 1,
                "anchors": {
                    "角色": {
                        "heading": "角色",
                        "comments": [
                            {
                                "id": "c-001-roles",
                                "role": "user",
                                "status": "open",
                                "text": "缺一个 'auditor 只读角色' 选项，做风控时要用",
                                "created_in_version": 1,
                            },
                            {
                                "id": "c-002-roles",
                                "role": "user",
                                "status": "open",
                                "text": "超管能否同时充当某租户的管理员？",
                                "created_in_version": 1,
                            },
                        ],
                    },
                    "权限组创建": {
                        "heading": "权限组创建",
                        "comments": [
                            {
                                "id": "c-003-pg",
                                "role": "user",
                                "status": "open",
                                "text": "slug 字段命名是否该改成 code？现网术语一直叫 code",
                                "created_in_version": 1,
                            },
                            {
                                "id": "c-004-pg",
                                "role": "user",
                                "status": "open",
                                "text": "没说权限组能否跨租户复用模板",
                                "created_in_version": 1,
                            },
                        ],
                    },
                    "权限点分配": {
                        "heading": "权限点分配",
                        "comments": [
                            {
                                "id": "c-005-pp",
                                "role": "user",
                                "status": "open",
                                "text": "resource:action 字符串需要长度上限",
                                "created_in_version": 1,
                            }
                        ],
                    },
                    "人员管理": {
                        "heading": "人员管理",
                        "comments": [
                            {
                                "id": "c-006-people",
                                "role": "user",
                                "status": "open",
                                "text": "停用后历史日志保留多久？合规要求一般是 6 个月",
                                "created_in_version": 1,
                            },
                            {
                                "id": "c-007-people",
                                "role": "user",
                                "status": "open",
                                "text": "想加一个 '按权限组批量分配人员' 的能力，但可能 v0 不做",
                                "created_in_version": 1,
                            },
                        ],
                    },
                    "边界": {
                        "heading": "边界",
                        "comments": [
                            {
                                "id": "c-008-bound",
                                "role": "user",
                                "status": "open",
                                "text": "外部 IdP 排除写得太死，至少留一句 '后续可接入 SCIM'",
                                "created_in_version": 1,
                            }
                        ],
                    },
                },
            }
            download = tmp_path / "Downloads-rbac-overview.comments.json"
            download.write_text(json.dumps(simulated_download, ensure_ascii=False), encoding="utf-8")

            # Step 4: subagent runs `consume diff` to extract new comments
            diff_result = _run_cli(
                str(CONSUME), "diff", "--baseline", str(comments), "--incoming", str(download)
            )
            self.assertEqual(diff_result.returncode, 0, diff_result.stderr)
            plan = json.loads(diff_result.stdout)
            self.assertEqual(plan["baseline_version"], 0)
            self.assertEqual(plan["incoming_version"], 1)
            self.assertEqual(len(plan["new_comments"]), 8)
            anchors_in_plan = {c["anchor_id"] for c in plan["new_comments"]}
            self.assertEqual(anchors_in_plan, {"角色", "权限组创建", "权限点分配", "人员管理", "边界"})

            # Step 5: subagent classifies + applies resolutions to comments.json
            classifications: dict[str, tuple[str, str, str]] = {
                "c-001-roles": ("blocker", "resolved", "已在 §角色 加 auditor 只读角色"),
                "c-002-roles": ("question", "answered", "可以；超管对租户的操作走显式 act-as 模式"),
                "c-003-pg": ("nit", "resolved", "字段名改为 code（保留 slug 为 alias）"),
                "c-004-pg": ("blocker", "resolved", "已加 §权限组创建.跨租户：模板可复制不可共享"),
                "c-005-pp": ("nit", "resolved", "已加上限 128 字符"),
                "c-006-people": ("question", "answered", "保留 12 个月，超过自动归档"),
                "c-007-people": ("idea", "moved", "moved to Backlog v1"),
                "c-008-bound": ("nit", "resolved", "已改成 'v0 不接入外部 IdP（后续可接入 SCIM）'"),
            }
            current = json.loads(download.read_text(encoding="utf-8"))
            next_version = current["review_version"] + 1
            current["review_version"] = next_version
            for comment_id, (classification, status, response) in classifications.items():
                review_doc_consume.apply_resolution(
                    current,
                    comment_id=comment_id,
                    classification=classification,
                    status=status,
                    response=response,
                    version=next_version,
                )
            comments.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
            review_doc_migrate.validate(current)

            # Step 6: assert all 8 comments have moved out of `open`
            still_open = []
            for anchor_payload in current["anchors"].values():
                for c in anchor_payload["comments"]:
                    if c["status"] == "open":
                        still_open.append(c["id"])
            self.assertEqual(still_open, [], f"expected zero open comments, still open: {still_open}")

            # Step 7: anchor stability still holds against the consumed comments
            verify2 = _run_cli(str(IDS), "verify", str(doc), str(comments))
            self.assertEqual(verify2.returncode, 0, verify2.stderr)

            # Step 8: re-render HTML, verify historical resolved thread shows up
            render2 = _run_cli(
                str(RENDER), "--doc", str(doc), "--output", str(html), "--comments", str(comments)
            )
            self.assertEqual(render2.returncode, 0, render2.stderr)
            html2 = html.read_text(encoding="utf-8")
            self.assertIn("已解决", html2)
            self.assertIn("已在 §角色 加 auditor 只读角色", html2)
            self.assertIn("agent:", html2)

            # Step 9: second-round baseline check — if user exports again with no new comments,
            # diff must reject (version did not advance)
            stale_download = tmp_path / "stale.json"
            stale_download.write_text(comments.read_text(encoding="utf-8"), encoding="utf-8")
            diff_stale = _run_cli(
                str(CONSUME), "diff", "--baseline", str(comments), "--incoming", str(stale_download)
            )
            self.assertEqual(diff_stale.returncode, 1, "stale download must be rejected")

            # Step 10: subagent classifications fully accounted for — no idea left in spec body
            self.assertEqual(
                sum(1 for a in current["anchors"].values() for c in a["comments"] if c["classification"] == "idea"),
                1,
            )


if __name__ == "__main__":
    unittest.main()
