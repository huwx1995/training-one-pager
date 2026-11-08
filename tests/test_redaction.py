# 测试中的机构、姓名、联系方式、业务条件和制度片段仅用于合成测试。
# 身份号码和信用代码使用未分配的全零行政/登记前缀，非真实人员或企业证件。
import io
import json
import unittest

import server


class RedactionTests(unittest.TestCase):
    def setUp(self):
        server.DOCUMENT_SESSIONS.clear()
        self.segments = [
            {
                "id": "P1-01",
                "file_name": "张三客户资料.txt",
                "page": 1,
                "index": 1,
                "text": (
                    "客户姓名：张三，手机号13800138000，身份证号000000200001010013，"
                    "邮箱zhangsan@example.com。张三任职于华东某某有限公司，"
                    "地址：虚构市示例区测试路1号。银行卡号0000000000000000001。"
                ),
            },
            {
                "id": "P2-01",
                "file_name": "张三客户资料.txt",
                "page": 2,
                "index": 1,
                "text": "张三完成工具借用登记，复核人为李四。",
            },
        ]

    def test_detects_common_types_and_all_name_occurrences(self):
        candidates = server.detect_sensitive_candidates(self.segments)
        by_type = {item["type"] for item in candidates}
        self.assertTrue({"name", "phone", "id_card", "bank_card", "email", "address", "organization"} <= by_type)
        name = next(item for item in candidates if item["type"] == "name" and item["value"] == "张三")
        self.assertEqual(4, len(name["occurrences"]))
        self.assertTrue(all(item["selected"] for item in name["occurrences"]))

    def test_one_occurrence_can_remain_visible(self):
        candidates = server.detect_sensitive_candidates(self.segments)
        name = next(item for item in candidates if item["type"] == "name" and item["value"] == "张三")
        second_page = next(item for item in name["occurrences"] if item["segment_id"] == "P2-01")
        second_page["selected"] = False
        second_page["status"] = "cancelled"
        masked, _ = server.apply_redactions(self.segments, candidates)
        self.assertIn("张三完成工具借用登记", masked[1]["text"])
        self.assertNotIn("张三", masked[0]["text"])
        self.assertEqual("[姓名1]客户资料.txt", masked[0]["file_name"])

    def test_manual_value_matches_every_occurrence(self):
        candidates = server.detect_sensitive_candidates(self.segments)
        candidates = server.add_manual_candidate(candidates, self.segments, "李四", "name")
        manual = next(item for item in candidates if item["value"] == "李四")
        self.assertTrue(manual["manual"])
        masked, _ = server.apply_redactions(self.segments, candidates)
        self.assertNotIn("李四", masked[1]["text"])

    def test_question_uses_existing_mapping_and_detects_new_value(self):
        candidates = server.detect_sensitive_candidates(self.segments)
        masked, new_candidates = server.mask_free_text("请问张三的手机号13900139000？", candidates, False)
        self.assertIn("[姓名1]", masked)
        self.assertIn("13900139000", masked)
        self.assertEqual(["13900139000"], [item["value"] for item in new_candidates])
        masked_confirmed, _ = server.mask_free_text("请问张三的手机号13900139000？", candidates, True)
        self.assertNotIn("张三", masked_confirmed)
        self.assertNotIn("13900139000", masked_confirmed)

    def test_generate_sends_only_masked_segments_to_model(self):
        candidates = server.detect_sensitive_candidates(self.segments)
        for candidate in candidates:
            for occurrence in candidate["occurrences"]:
                occurrence["status"] = "confirmed"
                occurrence["selected"] = True
        parsed = {"segments": self.segments, "blocks": [], "image_assets": [], "page_count": 2}
        session = server.create_document_session("test-doc", parsed, "张三客户资料.txt", ".txt")
        confirmation = server.create_confirmation("test-doc", session["version"], candidates, [])
        payload = json.dumps(
            {"document_id": "test-doc", "confirmation_token": confirmation["token"],
             "audience": "客户经理", "template": "制度解读版"},
            ensure_ascii=False,
        ).encode("utf-8")
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(payload)), "X-LLM-API-Key": "test-key"}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        handler.send_response = lambda status: None
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        captured = []
        original_call = server.call_llm

        def fake_call(prompt, api_key_override=""):
            captured.append(prompt)
            return {
                "title": "测试",
                "sections": [{"key": "key_points", "title": "核心要点", "items": []}],
            }

        try:
            server.call_llm = fake_call
            handler.handle_generate()
        finally:
            server.call_llm = original_call
        response = json.loads(handler.wfile.getvalue())
        self.assertTrue(response["ok"])
        self.assertNotIn("张三", captured[0])
        self.assertNotIn("13800138000", captured[0])
        self.assertIn("[姓名1]", captured[0])

    def test_generate_rejects_forged_boolean_without_confirmation_token(self):
        payload = json.dumps({
            "segments": self.segments,
            "redaction_confirmed": True,
            "audience": "客户经理",
        }, ensure_ascii=False).encode("utf-8")
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        handler.handle_generate()
        response = json.loads(handler.wfile.getvalue())
        self.assertEqual(400, statuses[0])
        self.assertFalse(response["ok"])
        self.assertIn("会话", response["error"])

    def test_confidence_defaults_and_business_phrase_exclusions(self):
        segments = [{
            "id": "P1-01", "file_name": "培训材料.txt", "page": 1, "index": 1,
            "text": (
                "示例商业银行负责承办，示例商业银行提供支持。"
                "个人客户净增数量由客户经理统计，企业电子银行和其他银行不属于客户名称。"
                "可与华东中心进一步核实。"
            ),
        }]
        candidates = server.detect_sensitive_candidates(segments)
        values = {item["value"]: item for item in candidates}
        self.assertNotIn("个人客户净增数量", values)
        self.assertNotIn("企业电子银行", values)
        self.assertNotIn("其他银行", values)
        bank = values["示例商业银行"]
        self.assertEqual("high", bank["confidence"])
        self.assertTrue(all(not item["selected"] for item in bank["occurrences"]))
        center = next(item for item in candidates if item["value"].endswith("华东中心"))
        self.assertEqual("low", center["confidence"])
        self.assertTrue(all(not item["selected"] for item in center["occurrences"]))
        self.assertTrue(all(item["status"] == "cancelled" for item in center["occurrences"]))

    def test_full_bank_branch_links_aliases_to_one_replacement(self):
        segments = [{
            "id": "P1-01", "file_name": "机构说明.txt", "page": 1, "index": 1,
            "text": "机构名称：示例银行北京分行。示例银行负责受理，北京分行负责复核。",
        }]
        candidates = server.detect_sensitive_candidates(segments)
        institution = next(item for item in candidates if item["value"] == "示例银行北京分行")
        self.assertEqual(["示例银行", "北京分行"], institution["aliases"])
        matched = {item["matched_text"] for item in institution["occurrences"]}
        self.assertTrue({"示例银行北京分行", "示例银行", "北京分行"} <= matched)
        masked, _ = server.apply_redactions(segments, candidates)
        self.assertIn("示例银行", masked[0]["text"])
        server.add_manual_candidate(candidates, segments, "示例银行北京分行", "organization")
        masked, _ = server.apply_redactions(segments, candidates)
        self.assertNotIn("示例银行", masked[0]["text"])
        self.assertNotIn("北京分行", masked[0]["text"])
        self.assertEqual(3, masked[0]["text"].count(institution["replacement"]))

    def test_manual_add_promotes_existing_low_confidence_candidate(self):
        segments = [{
            "id": "P1-01", "file_name": "说明.txt", "page": 1, "index": 1,
            "text": "华东中心负责处理。",
        }]
        candidates = server.detect_sensitive_candidates(segments)
        center = next(item for item in candidates if item["value"] == "华东中心")
        self.assertFalse(center["occurrences"][0]["selected"])
        server.add_manual_candidate(candidates, segments, "华东中心", "organization")
        self.assertTrue(center["manual"])
        self.assertEqual("high", center["confidence"])
        self.assertTrue(all(item["selected"] for item in center["occurrences"]))


if __name__ == "__main__":
    unittest.main()
