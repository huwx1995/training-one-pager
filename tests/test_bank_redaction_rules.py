# 测试中的机构、姓名、联系方式、业务条件和制度片段仅用于合成测试。
# 身份号码和信用代码使用未分配的全零行政/登记前缀，非真实人员或企业证件。
import tempfile
import unittest
from pathlib import Path

import server
from bank_redaction_rules import RULE_VERSION, find_bank_sensitive_matches
from document_parser import parse_txt_structured


class BankRedactionRuleTests(unittest.TestCase):
    def test_six_rule_categories_and_contextual_values(self):
        text = (
            "姓名：张三，护照号E12345678，客户号CIF123456，工号A12345，"
            "系统名称：示例业务系统，内网10.0.0.1，授信额度人民币800万元，"
            "统一社会信用代码000000000000000000，客户征信逾期3次，制裁名单未命中。"
        )
        matches = find_bank_sensitive_matches(text)
        categories = {item["category"] for item in matches}
        self.assertEqual(
            {"personal", "customer_account", "internal", "financial", "corporate", "regulatory"},
            categories,
        )
        self.assertTrue(all(item["rule_version"] == RULE_VERSION for item in matches))

    def test_public_amounts_and_generic_system_are_low_and_not_highlighted(self):
        matches = find_bank_sensitive_matches("公开费率3.2%，培训公式100万元，核心系统用于教学。")
        low_values = {item["value"] for item in matches if item["sensitivity"] == "low"}
        self.assertTrue({"3.2%", "100万元", "核心系统"} <= low_values)
        self.assertTrue(all(not item["default_highlight"] for item in matches))

    def test_training_policy_phrases_are_not_highlighted_by_default(self):
        text = "某某银行北京分行，客户征信逾期3次，授信额度人民币800万元，内部工具清单仅供演示。"
        matches = find_bank_sensitive_matches(text)
        self.assertTrue(matches)
        self.assertTrue(all(not item["default_highlight"] for item in matches))

    def test_explicit_identifiers_remain_highlighted(self):
        matches = find_bank_sensitive_matches("客户号CIF123456，联系电话13800138000，邮箱test@example.com。")
        highlighted = {item["value"] for item in matches if item["default_highlight"]}
        self.assertTrue({"CIF123456", "13800138000", "test@example.com"} <= highlighted)

    def test_generic_bank_phrases_do_not_become_organizations(self):
        matches = find_bank_sensitive_matches(
            "个人客户净增数量、企业电子银行、由分支行、通过银行、医疗机构、所属机构。"
        )
        self.assertFalse(any(item["type"] == "organization" for item in matches))

    def test_specific_rule_wins_overlap_and_keeps_rule_sources(self):
        matches = find_bank_sensitive_matches("公积金账号GJJ123456，对公账号123456789012。")
        provident = next(item for item in matches if item["value"] == "GJJ123456")
        corporate = next(item for item in matches if item["value"] == "123456789012")
        self.assertEqual("personal.provident_fund", provident["rule_id"])
        self.assertIn("account.account", provident["rule_ids"])
        self.assertEqual("corporate.account", corporate["rule_id"])

    def test_invalid_luhn_with_explicit_label_is_manual_review_candidate(self):
        candidate = next(item for item in find_bank_sensitive_matches("银行卡号0000000000000000001。")
                         if item["type"] == "bank_card")
        self.assertEqual("low", candidate["sensitivity"])
        self.assertFalse(candidate["default_highlight"])

    def test_txt_preview_is_continuous_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("第一段\n第二段", encoding="utf-8")
            parsed = parse_txt_structured(path, "sample.txt", server.SourceSegment)
        self.assertEqual("flow", parsed["document_preview"]["mode"])
        self.assertEqual(2, len(parsed["document_preview"]["flow_blocks"]))

    def test_confirmation_manifest_records_operator_and_local_decisions(self):
        server.DOCUMENT_SESSIONS.clear()
        segments = [{"id": "P1-01", "file_name": "客户.txt", "page": 1, "index": 1,
                     "text": "姓名：张三"}]
        candidates = server.detect_sensitive_candidates(segments)
        for candidate in candidates:
            for occurrence in candidate["occurrences"]:
                occurrence["status"] = "confirmed"
                occurrence["selected"] = True
                occurrence["decision_origin"] = "instance_double_click"
                occurrence["updated_at"] = 123456
        parsed = {"segments": segments, "blocks": [], "image_assets": [], "page_count": 1,
                  "document_preview": {"mode": "flow", "flow_blocks": []}}
        session = server.create_document_session("manifest-doc", parsed, "客户.txt", ".txt")
        confirmation = server.create_confirmation(
            "manifest-doc", session["version"], candidates, [],
            [{"id": "action-1", "action": "确认", "timestamp": 123456,
              "related_action_id": "", "operator": "A001"}], "A001",
        )
        manifest = confirmation["decision_manifest"]
        self.assertEqual("A001", manifest["operator"])
        self.assertEqual(123456, manifest["text_decisions"][0]["operation_time"])
        self.assertEqual("action-1", manifest["action_log"][0]["id"])
        (server.RECORD_DIR / "manifest-doc.json").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
