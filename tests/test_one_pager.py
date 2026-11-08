# 测试中的机构、姓名、联系方式、业务条件和制度片段均为虚构测试数据。
import io
import json
import os
import threading
import unittest
import zipfile
from PIL import Image
from xml.etree import ElementTree as ET
from unittest.mock import patch

import server


class OnePagerTests(unittest.TestCase):
    def test_framework_word_keeps_diagram_and_full_structure(self):
        segments = self.knowledge_segments("policy")
        result = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料",
                                             presentation_mode="framework")
        result["generation_requirements"] = {
            "version": 1, "presentation_mode": "framework", "max_chars": None,
            "detail_depth": "normal", "tone": "plain", "include_overview": True,
            "include_full_structure": True, "include_architecture": True,
            "include_practice": True, "explain_terms": False,
        }
        normalized = server.normalize_one_pager(result, segments, {"template": "knowledge-policy"})
        picture = io.BytesIO()
        Image.new("RGB", (800, 300), "white").save(picture, format="PNG")
        body = server.build_one_pager_docx(normalized, picture.getvalue())
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
            self.assertTrue(any(name.startswith("word/media/image") for name in archive.namelist()))
        self.assertIn("全文架构", xml)
        self.assertIn("<wp:docPr", xml)
        self.assertNotIn("知识架构 ·", xml)

    def test_focus_prompt_keeps_other_main_topics(self):
        requirements = server.validate_generation_requirements({"version": 1, "presentation_mode": "framework",
            "include_overview": True, "include_full_structure": True, "include_architecture": True,
            "include_practice": True, "explain_terms": False})
        prompt = server.prompt_for_one_pager(self.knowledge_segments("policy"), "客户经理",
            "knowledge-policy", focus="借用期限", requirements=requirements)
        self.assertIn("其他有依据的主要主题仍须保留标题和简短结论", prompt)
        self.assertIn("原文有目录时以目录为线索", prompt)

    def test_focused_draft_restores_evidenced_other_sections(self):
        texts = ["一、服务对象", "适用于普通客户。", "二、办理准备", "办理前核对申请资料。",
                 "三、办理流程", "先受理申请，再审核。", "四、异常处理", "失败时说明原因。"]
        segments = [{"id": f"P1-{index:02d}", "file_name": "培训.txt", "page": 1,
                     "index": index, "text": text} for index, text in enumerate(texts, 1)]
        result = {"schema_version": "3.0", "meta": {"title": "培训", "overview": "", "training_type": "operation"},
            "original_structure": [{"title": "办理流程", "source_ids": ["P1-05"]}],
            "knowledge_architecture": {"type": "process", "show_diagram": True, "central_topic": "培训",
                "modules": [{"id": "module-3", "title": "办理流程", "source_ids": ["P1-05"]}]},
            "knowledge_modules": [{"architecture_id": "module-3", "title": "办理流程",
                "points": [{"text": "先受理申请，再审核。", "source_ids": ["P1-06"]}]}],
            "generation_requirements": {"version": 1, "presentation_mode": "framework", "detail_target": "办理流程",
                "include_full_structure": True, "include_architecture": True, "include_overview": False,
                "include_practice": False, "explain_terms": False}}
        normalized = server.normalize_one_pager(result, segments, {"template": "knowledge-auto"})
        self.assertEqual(["服务对象", "办理准备", "办理流程", "异常处理"],
                         [item["title"] for item in normalized["knowledge_architecture"]["modules"]])
        self.assertEqual(4, len(normalized["original_structure"]))
        self.assertEqual(4, len(normalized["knowledge_modules"]))
        removed = normalized["knowledge_architecture"]["modules"].pop(0)
        normalized["original_structure"].pop(0)
        normalized["knowledge_modules"] = [group for group in normalized["knowledge_modules"]
                                           if group["architecture_id"] != removed["id"]]
        normalized["user_deleted_content"] = True
        exported = server.normalize_one_pager(normalized, segments, normalized["meta"])
        self.assertEqual(3, len(exported["knowledge_architecture"]["modules"]))
        self.assertEqual(3, len(exported["original_structure"]))

    def test_directory_titles_need_matching_body_before_becoming_themes(self):
        rows = ["目录", "一、服务对象", "二、办理准备", "一、服务对象", "适用于普通客户。",
                "二、办理准备", "办理前核对资料。", "三、未写正文"]
        segments = [{"id": f"P1-{index:02d}", "text": text} for index, text in enumerate(rows, 1)]
        self.assertEqual(["服务对象", "办理准备"],
                         [item["title"] for item in server.source_theme_outline(segments)])
    def test_cancel_stops_remaining_model_batches(self):
        job_id = "11111111-1111-1111-1111-111111111111"
        event = threading.Event()
        server.GENERATION_CANCEL_EVENTS[job_id] = event
        server.GENERATION_CONTEXT.job_id = job_id
        segments = [{"id": "P1", "text": "甲" * 12000}, {"id": "P2", "text": "乙" * 12000}]
        calls = []

        def fake_call(*args, **kwargs):
            calls.append(args)
            event.set()
            return {"facts": [], "outline": []}

        try:
            with patch.object(server, "call_llm", side_effect=fake_call):
                with self.assertRaisesRegex(RuntimeError, "生成已取消"):
                    server.generate_one_pager_with_llm(segments, "客户经理", "report", "auto", "", "key")
            self.assertEqual(1, len(calls))
        finally:
            del server.GENERATION_CONTEXT.job_id
            server.GENERATION_CANCEL_EVENTS.pop(job_id, None)

    def test_cancel_endpoint_sets_generation_event(self):
        job_id = "22222222-2222-2222-2222-222222222222"
        body = json.dumps({"generation_id": job_id}).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.send_response = lambda status: None
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        try:
            handler.handle_cancel_generate()
            self.assertTrue(server.GENERATION_CANCEL_EVENTS[job_id].is_set())
        finally:
            server.GENERATION_CANCEL_EVENTS.pop(job_id, None)

    def test_presentation_mode_is_validated_and_preserved(self):
        value = {"version": 1, "presentation_mode": "framework", "include_overview": True,
                 "include_architecture": True, "include_practice": True, "explain_terms": False}
        self.assertEqual("framework", server.validate_generation_requirements(value)["presentation_mode"])
        with self.assertRaisesRegex(ValueError, "呈现方式"):
            server.validate_generation_requirements({**value, "presentation_mode": "unknown"})

    def test_local_framework_groups_source_headings_without_inventing_branches(self):
        rows = ["商圈培训", "一、管理方", "活动合作：举办节日活动。", "二、商户", "结算账户：提供线上对账。",
                "三、消费者", "支付优惠：提供满减活动。"]
        segments = [{"id": f"P1-{index:02d}", "text": text, "file_name": "培训.txt", "page": 1, "index": index}
                    for index, text in enumerate(rows, 1)]
        result = server.local_evidence_draft(segments, "客户经理", "knowledge-auto", presentation_mode="framework")
        self.assertEqual(["管理方", "商户", "消费者"],
                         [item["title"] for item in result["knowledge_architecture"]["modules"]])
        self.assertEqual("活动合作：举办节日活动。", result["knowledge_modules"][0]["points"][0]["text"])
        self.assertEqual(["P1-03"], result["knowledge_modules"][0]["points"][0]["source_ids"])

    def test_local_rules_find_late_critical_fact_and_keep_its_source(self):
        rows = ["业务培训"] + [f"背景介绍第{index}部分。" for index in range(1, 10)] + [
            "工具借用期限为3天，归还前必须清点配件，不得遗失工具。"]
        segments = [{"id": f"P1-{index:02d}", "text": text} for index, text in enumerate(rows, 1)]
        result = server.local_evidence_draft(segments, "全体员工", "knowledge-policy")
        self.assertTrue(any(point["source_ids"] == ["P1-11"] and "3天" in point["text"]
                            for module in result["knowledge_modules"] for point in module["points"]))
        self.assertEqual(["P1-11"], result["key_reminders"][0]["source_ids"])

    def test_local_rules_use_source_sections_in_text_layout(self):
        rows = ["商圈培训", "一、管理方", "活动合作：举办节日活动。", "二、商户", "结算账户：提供线上对账。"]
        segments = [{"id": f"P1-{index:02d}", "text": text} for index, text in enumerate(rows, 1)]
        result = server.local_evidence_draft(segments, "客户经理", "knowledge-auto", presentation_mode="text")
        self.assertEqual(["管理方", "商户"],
                         [item["title"] for item in result["knowledge_architecture"]["modules"]])
        self.assertEqual(["P1-05"], result["knowledge_modules"][1]["points"][0]["source_ids"])

    def test_business_contact_candidates_keep_pairs_and_partial_values(self):
        segments = [
            {"id": "P1", "text": "业务联系人：张三 联系电话：13800138000"},
            {"id": "P2", "text": "咨询电话：010-12345678"},
            {"id": "P3", "text": "联系人：李四 邮箱：li@example.com"},
            {"id": "P4", "text": "本页介绍产品期限和办理流程。"},
            {"id": "P6", "text": "业务联系人：王五"},
        ]
        found = server.business_contact_candidates(segments)
        self.assertEqual(("张三", "13800138000"), (found[0]["name"], found[0]["method"]))
        self.assertEqual(("", "010-12345678"), (found[1]["name"], found[1]["method"]))
        self.assertEqual(("李四", "li@example.com"), (found[2]["name"], found[2]["method"]))
        self.assertEqual(("王五", ""), (found[3]["name"], found[3]["method"]))
        self.assertEqual(4, len(found))
        self.assertEqual([], server.business_contact_candidates([segments[3]]))
        ambiguous = server.business_contact_candidates([{"id": "P5", "text": "联系人：王五 联系人：赵六 电话：010-88888888"}])
        self.assertTrue(all(item["ambiguous"] for item in ambiguous))
        self.assertFalse(any(item["name"] and item["method"] for item in ambiguous))

    def test_business_contact_pairs_adjacent_labelled_lines(self):
        segments = [
            {"id": "P1-01", "file_name": "培训.txt", "page": 1, "index": 1, "text": "业务联系人：张三"},
            {"id": "P1-02", "file_name": "培训.txt", "page": 1, "index": 2, "text": "联系电话：13800138000"},
            {"id": "P2-01", "file_name": "培训.txt", "page": 2, "index": 1, "text": "联系人：李四"},
            {"id": "P3-01", "file_name": "培训.txt", "page": 3, "index": 1, "text": "电话：010-12345678"},
        ]
        found = server.business_contact_candidates(segments)
        self.assertEqual(3, len(found))
        self.assertEqual(("张三", "13800138000"), (found[0]["name"], found[0]["method"]))
        self.assertEqual(["P1-01", "P1-02"], found[0]["source_ids"])
        self.assertEqual(("李四", ""), (found[1]["name"], found[1]["method"]))

    def test_business_contact_survives_normalization_and_word_export(self):
        result = self.sample_result()
        result["business_contact"] = {"name": "张三", "method": "13800138000", "source_ids": ["P1-01"]}
        normalized = server.normalize_one_pager(result, self.segments)
        self.assertEqual("张三", normalized["business_contact"]["name"])
        self.assertIn("13800138000", server.visible_one_pager_fields(normalized))
        with zipfile.ZipFile(io.BytesIO(server.build_one_pager_docx(normalized))) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("业务联系", xml)
        self.assertIn("13800138000", xml)

    def setUp(self):
        self.segments = [
            {"id": "P1-01", "file_name": "汇报.txt", "page": 1, "index": 1,
             "text": "本季度营收达到1.2亿元，同比增长18%，完成率96%。"},
            {"id": "P2-01", "file_name": "汇报.txt", "page": 2, "index": 1,
             "text": "6月底前完成渠道复盘，由华东区负责。"},
            {"id": "P3-01", "file_name": "汇报.txt", "page": 3, "index": 1,
             "text": "下一步工作重点是降低风险并提升客户覆盖。"},
        ]

    def sample_result(self):
        return {
            "meta": {"title": "季度经营一纸通", "subtitle": "经营结果与下一步安排", "document_type": "工作汇报"},
            "conclusions": [
                {"text": "营收同比增长18%", "source_ids": ["P1-01"]},
                {"text": "6月底前完成渠道复盘", "source_ids": ["P2-01"]},
                {"text": "下一步重点降低风险", "source_ids": ["P3-01"]},
            ],
            "metrics": [
                {"label": "营收", "value": "1.2亿元", "comparison": "同比18%", "source_ids": ["P1-01"]},
            ],
            "logic": {"type": "目标—举措—结果", "nodes": [
                {"title": "结果", "text": "营收增长", "source_ids": ["P1-01"]},
                {"title": "举措", "text": "渠道复盘", "source_ids": ["P2-01"]},
                {"title": "重点", "text": "降低风险", "source_ids": ["P3-01"]},
            ]},
            "actions": [
                {"kind": "待办", "priority": "high", "text": "完成渠道复盘", "owner": "华东区", "due": "6月底", "source_ids": ["P2-01"]},
            ],
            "supplements": [],
        }

    def test_excluded_section_removes_its_body_but_keeps_following_section(self):
        segments = [
            {"id": "P1-01", "text": "一、**业务概要情况**"},
            {"id": "P1-02", "text": "这里是不要呈现的背景内容。"},
            {"id": "P2-01", "text": "（一）背景明细"},
            {"id": "P3-01", "text": "二、办理要求"},
            {"id": "P3-02", "text": "办理前须核验客户资料。"},
        ]
        kept = server.filter_excluded_sections(segments, "一、业务概要情况")
        self.assertEqual(["P3-01", "P3-02"], [item["id"] for item in kept])
        with self.assertRaisesRegex(ValueError, "未找到"):
            server.filter_excluded_sections(segments, "三、未知章节")

    def test_full_document_chunking_includes_last_segment(self):
        segments = [
            {"id": f"P{i}-01", "file_name": "长文.txt", "page": i, "index": 1, "text": "内容" * 2500}
            for i in range(1, 8)
        ]
        chunks = server.chunk_segments(segments, max_chars=6000)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("P7-01", chunks[-1][-1]["id"])
        self.assertEqual(len(segments), sum(len(chunk) for chunk in chunks))

    def test_llm_json_parser_accepts_code_fence_and_trailing_comma(self):
        parsed = server._parse_llm_json('```json\n{"ok": true,}\n```')
        self.assertEqual({"ok": True}, parsed)

    def test_call_llm_repairs_malformed_json_once(self):
        malformed = '{"title":"季度汇报" "status":"待确认"}'
        repaired = '{"title":"季度汇报","status":"待确认"}'
        with patch.object(server, "_request_llm_content", side_effect=[malformed, repaired]) as request:
            result = server.call_llm("生成一纸通", "test-key")
        self.assertEqual("季度汇报", result["title"])
        self.assertEqual(2, request.call_count)
        self.assertIn("只修复 JSON 语法", request.call_args_list[1].args[0])

    def test_llm_request_disables_thinking_mode(self):
        response_body = json.dumps({
            "choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}]
        }).encode()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return response_body

        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            content = server._request_llm_content("测试", "test-key", "deepseek-flash", "https://api.deepseek.com")
        self.assertEqual('{"ok":true}', content)
        self.assertEqual("none", captured["payload"]["reasoning_effort"])
        self.assertNotIn("thinking", captured["payload"])
        self.assertEqual(16384, captured["payload"]["max_tokens"])
        self.assertEqual(server.LLM_REQUEST_TIMEOUT_SECONDS, captured["timeout"])

    def test_selected_reasoning_is_validated_and_sent(self):
        options = server.model_options_from_headers({
            "X-LLM-Base-URL": "https://api.deepseek.com", "X-LLM-Model": "deepseek-flash",
            "X-LLM-Reasoning": "high",
        })
        self.assertEqual("high", options["reasoning_override"])
        with self.assertRaisesRegex(ValueError, "思考程度"):
            server.model_options_from_headers({
                "X-LLM-Base-URL": "https://api.moonshot.cn/v1", "X-LLM-Model": "kimi-k2.6",
                "X-LLM-Reasoning": "high",
            })

        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self):
                return b'{"choices":[{"message":{"content":"{\\"ok\\":true}"},"finish_reason":"stop"}]}'

        captured = {}
        def fake_urlopen(request, timeout):
            captured.update(json.loads(request.data))
            return FakeResponse()
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual({"ok": True}, server.call_llm("测试", "test-key", **options))
        self.assertEqual("high", captured["reasoning_effort"])

    def test_explicit_local_generation_ignores_server_model_key(self):
        segments = self.knowledge_segments("policy")
        payload = json.dumps({"document_id": "test-doc", "confirmation_token": "test-token",
                              "template": "knowledge-policy"}).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(payload)), "X-Generation-Mode": "local"}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        with patch.dict(os.environ, {"LLM_API_KEY": "server-key"}), \
             patch.object(server, "get_confirmation", return_value={"primary_masked_segments": segments}), \
             patch.object(server, "get_document_session", return_value={"file_name": "政策.txt", "page_count": 3}), \
             patch.object(server, "generate_one_pager_with_llm") as model_call:
            handler.handle_generate()
        self.assertEqual([200], statuses)
        self.assertEqual("local_rules", json.loads(handler.wfile.getvalue())["mode"])
        model_call.assert_not_called()

    def test_llm_length_response_is_retried_before_json_repair(self):
        truncated = json.dumps({
            "choices": [{"message": {"content": '{"title":"未完成"'}, "finish_reason": "length"}]
        }).encode()
        complete = json.dumps({
            "choices": [{"message": {"content": '{"title":"完成"}'}, "finish_reason": "stop"}]
        }).encode()

        class FakeResponse:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return self.body

        requests = []

        def fake_urlopen(request, timeout):
            requests.append(json.loads(request.data.decode("utf-8")))
            return FakeResponse(truncated if len(requests) == 1 else complete)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = server.call_llm("生成一纸通", "test-key")
        self.assertEqual({"title": "完成"}, result)
        self.assertEqual([16384, 32768], [item["max_tokens"] for item in requests])
        self.assertEqual("生成一纸通", requests[1]["messages"][1]["content"])

    def test_llm_read_timeout_returns_friendly_error(self):
        errors = (
            TimeoutError("The read operation timed out"),
            server.urllib.error.URLError(TimeoutError("The read operation timed out")),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                with patch("urllib.request.urlopen", side_effect=error):
                    with self.assertRaisesRegex(RuntimeError, "大模型服务等待响应超时") as raised:
                        server.call_llm("生成一纸通", "test-key")
                self.assertNotIn("The read operation timed out", str(raised.exception))

    def test_generate_returns_gateway_error_when_model_times_out(self):
        payload = json.dumps({"document_id": "test-doc", "confirmation_token": "test-token"}).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(payload)), "X-LLM-API-Key": "test-key"}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        confirmation = {"primary_masked_segments": self.segments}
        with patch.object(server, "get_confirmation", return_value=confirmation), \
             patch.object(server, "get_document_session", return_value={"file_name": "汇报.txt", "page_count": 3}), \
             patch.object(server, "generate_one_pager_with_llm", side_effect=RuntimeError("大模型服务等待响应超时")):
            handler.handle_generate()
        self.assertEqual([502], statuses)
        self.assertIn("等待响应超时", json.loads(handler.wfile.getvalue())["error"])

    def test_llm_request_omits_deepseek_thinking_for_other_providers(self):
        response_body = json.dumps({
            "choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "stop"}]
        }).encode()

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return response_body

        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            content = server._request_llm_content("test", "test-key", "example-model", "https://llm.example/v1")
        self.assertEqual('{"ok":true}', content)
        self.assertNotIn("thinking", captured["payload"])

    def test_kimi_request_uses_selected_region_and_supported_parameters(self):
        response_body = b'{"choices":[{"message":{"content":"{\\"ok\\":true}"},"finish_reason":"stop"}]}'

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return response_body

        for base_url in ("https://api.moonshot.cn/v1",):
            with self.subTest(base_url=base_url):
                captured = {}

                def fake_urlopen(request, timeout):
                    captured["url"] = request.full_url
                    captured["payload"] = json.loads(request.data)
                    return FakeResponse()

                with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                    result = server.call_llm("测试", "test-key", model_override="kimi-k2.6", base_url_override=base_url)
                self.assertEqual({"ok": True}, result)
                self.assertEqual(f"{base_url}/chat/completions", captured["url"])
                self.assertNotIn("temperature", captured["payload"])
                self.assertEqual({"type": "disabled"}, captured["payload"]["thinking"])

    def test_kimi_401_does_not_expose_key_fragment(self):
        error = server.urllib.error.HTTPError(
            "https://api.moonshot.cn/v1/chat/completions", 401, "Unauthorized", {},
            io.BytesIO(b'Your api key: ****DEMO is invalid'),
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "中国站 Kimi API") as raised:
                server.call_llm("测试", "test-key", model_override="kimi-k2.6", base_url_override="https://api.moonshot.cn/v1")
        self.assertNotIn("DEMO", str(raised.exception))

    def test_model_headers_require_valid_base_url_and_model(self):
        options = server.model_options_from_headers({
            "X-LLM-Base-URL": "https://api.moonshot.cn/v1/", "X-LLM-Model": "kimi-k2.6",
        })
        self.assertEqual("https://api.moonshot.cn/v1", options["base_url_override"])
        with self.assertRaises(ValueError):
            server.model_options_from_headers({"X-LLM-Model": "kimi-k2.6"})
        with self.assertRaises(ValueError):
            server.model_options_from_headers({
                "X-LLM-Base-URL": "https://api.moonshot.cn/v1/chat/completions", "X-LLM-Model": "kimi-k2.6",
            })

    def test_test_connection_forwards_selected_kimi_configuration(self):
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {
            "X-LLM-API-Key": "test-key", "X-LLM-Base-URL": "https://api.moonshot.cn/v1",
            "X-LLM-Model": "kimi-k2.6",
        }
        handler.wfile = io.BytesIO()
        handler.send_response = lambda status: None
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        with patch.object(server, "_request_llm_content", return_value='{"ok":true}') as request:
            handler.handle_test_llm()
        self.assertTrue(json.loads(handler.wfile.getvalue())["ok"])
        self.assertEqual("kimi-k2.6", request.call_args.args[2])
        self.assertEqual("https://api.moonshot.cn/v1", request.call_args.args[3])

    def test_recommended_models_prioritize_new_flagship_and_keep_fallback(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self, *_):
                return json.dumps({"data": [{"id": "kimi-k4"}, {"id": "kimi-k3"},
                                            {"id": "kimi-k4-code"}, {"id": "moonshot-v1"}]}).encode()

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            models = server.recommended_models("kimi", "test-key")
        self.assertEqual("kimi-k4", models[0])
        self.assertIn("kimi-k2.6", models)
        self.assertNotIn("kimi-k4-code", models)

    def test_recommended_models_use_local_order_when_listing_is_unavailable(self):
        with patch("urllib.request.urlopen", side_effect=server.urllib.error.URLError("不可用")):
            self.assertEqual(["kimi-k3", "kimi-k2.6"], server.recommended_models("kimi", "test-key"))
        self.assertEqual("https://dashscope.aliyuncs.com/compatible-mode/v1", server.MODEL_PRESETS["qwen"]["base_url"])
        self.assertEqual("https://ark.cn-beijing.volces.com/api/v3", server.MODEL_PRESETS["doubao"]["base_url"])

    def test_model_pair_refreshes_deepseek_from_account_listing(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, *_):
                return json.dumps({"data": [{"id": name} for name in (
                    "deepseek-flash", "deepseek-v5-flash", "deepseek-v5-pro", "deepseek-v5-code", "deepseek-v4-pro",
                )]}).encode()

        with patch("urllib.request.urlopen", return_value=FakeResponse()) as request:
            pair, refreshed = server.current_model_pair("deepseek", "test-key")
        self.assertTrue(refreshed)
        self.assertEqual(["deepseek-flash", "deepseek-v5-pro"], pair)
        self.assertEqual("https://api.deepseek.com/models", request.call_args.args[0].full_url)
        self.assertNotIn("test-key", repr(pair))

    def test_qwen_and_doubao_do_not_send_generation_keys_to_unsupported_list_endpoint(self):
        with patch("urllib.request.urlopen") as request:
            for provider in ("qwen", "doubao"):
                pair, refreshed = server.current_model_pair(provider, "test-key")
                self.assertEqual(list(server.MODEL_CHOICES[provider]), pair)
                self.assertFalse(refreshed)
            request.assert_not_called()

    def test_model_pair_falls_back_to_two_current_roles_when_listing_fails(self):
        with patch("urllib.request.urlopen", side_effect=server.urllib.error.URLError("不可用")):
            pair, refreshed = server.current_model_pair("doubao", "test-key")
        self.assertFalse(refreshed)
        self.assertEqual(["doubao-seed-2-1-turbo-260628", "doubao-seed-2-1-pro-260915"], pair)

    def test_model_pair_rejects_specialized_models_and_accepts_new_flagship(self):
        self.assertIsNone(server.model_role_rank("kimi", "kimi-k4-code", "flagship"))
        self.assertIsNone(server.model_role_rank("doubao", "doubao-seed-2-2-vision-260901", "fast"))
        self.assertIsNotNone(server.model_role_rank("kimi", "kimi-k4.1-pro", "flagship"))
        self.assertIsNotNone(server.model_role_rank("doubao", "doubao-seed-2-2-turbo-260901", "fast"))

    def test_model_choices_endpoint_returns_two_roles_without_key(self):
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"X-LLM-API-Key": "test-key", "X-LLM-Provider": "deepseek"}
        handler.wfile = io.BytesIO()
        handler.send_response = lambda *_: None
        handler.send_header = lambda *_: None
        handler.end_headers = lambda: None
        with patch.object(server, "current_model_pair", return_value=(["deepseek-flash", "deepseek-v5-pro"], True)):
            handler.handle_model_choices()
        response = json.loads(handler.wfile.getvalue())
        self.assertEqual(["deepseek-flash", "deepseek-v5-pro"], response["models"])
        self.assertEqual([], response["reasoning_levels"]["deepseek-v5-pro"])
        self.assertNotIn("test-key", handler.wfile.getvalue().decode())

    def test_preset_connection_falls_back_and_reports_actual_model(self):
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"X-LLM-API-Key": "test-key", "X-LLM-Provider": "kimi"}
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda *_: None
        handler.end_headers = lambda: None
        with patch.object(server, "recommended_models", return_value=["kimi-k3", "kimi-k2.6"]), \
             patch.object(server, "call_llm", side_effect=[server.ModelUnavailableError("无权限"), {"ok": True}]) as request:
            handler.handle_test_llm()
        payload = json.loads(handler.wfile.getvalue())
        self.assertEqual([200], statuses)
        self.assertEqual("kimi-k2.6", payload["model"])
        self.assertEqual("https://api.moonshot.cn/v1", payload["base_url"])
        self.assertEqual("kimi-k2.6", request.call_args.kwargs["model_override"])

    def test_preset_connection_falls_back_when_flagship_output_is_incompatible(self):
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"X-LLM-API-Key": "test-key", "X-LLM-Provider": "deepseek"}
        handler.wfile = io.BytesIO()
        handler.send_response = lambda *_: None
        handler.send_header = lambda *_: None
        handler.end_headers = lambda: None
        with patch.object(server, "recommended_models", return_value=["deepseek-v4-pro", "deepseek-flash"]), \
             patch.object(server, "call_llm", side_effect=[server.ModelOutputError("无法生成 JSON"), {"ok": True}]):
            handler.handle_test_llm()
        self.assertEqual("deepseek-flash", json.loads(handler.wfile.getvalue())["model"])

    def test_manual_preset_model_uses_fixed_domestic_endpoint_without_auto_fallback(self):
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"X-LLM-API-Key": "test-key", "X-LLM-Provider": "deepseek", "X-LLM-Model": "deepseek-flash"}
        handler.wfile = io.BytesIO()
        handler.send_response = lambda *_: None
        handler.send_header = lambda *_: None
        handler.end_headers = lambda: None
        with patch.object(server, "recommended_models") as discovery, \
             patch.object(server, "call_llm", return_value={"ok": True}) as request:
            handler.handle_test_llm()
        discovery.assert_not_called()
        request.assert_called_once()
        self.assertEqual("deepseek-flash", request.call_args.kwargs["model_override"])
        self.assertEqual("https://api.deepseek.com", request.call_args.kwargs["base_url_override"])
        self.assertEqual("deepseek-flash", json.loads(handler.wfile.getvalue())["model"])

    def test_new_manual_model_uses_platform_default_and_compatible_json_mode(self):
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"X-LLM-API-Key": "test-key", "X-LLM-Provider": "deepseek",
                           "X-LLM-Model": "deepseek-v9-flash"}
        handler.wfile = io.BytesIO()
        handler.send_response = lambda *_: None
        handler.send_header = lambda *_: None
        handler.end_headers = lambda: None
        with patch.object(server, "call_llm", side_effect=[server.ModelParameterError("bad"), {"ok": True}]) as request:
            handler.handle_test_llm()
        payload = json.loads(handler.wfile.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual("deepseek-v9-flash", payload["model"])
        self.assertEqual("platform", payload["reasoning"])
        self.assertEqual("prompt", payload["json_mode"])
        self.assertEqual("prompt", request.call_args.kwargs["json_mode_override"])

    def test_probe_removes_rejected_reasoning_and_reports_effective_mode(self):
        with patch.object(server, "call_llm", side_effect=[server.ModelParameterError("bad"), {"ok": True}]) as request:
            reasoning, json_mode, adjusted = server.probe_llm_compatibility(
                "test-key", "deepseek-flash", "https://api.deepseek.com", "none")
        self.assertEqual(("platform", "native", True), (reasoning, json_mode, adjusted))
        self.assertEqual("platform", request.call_args.kwargs["reasoning_override"])

    def test_generation_uses_tested_prompt_json_and_platform_reasoning(self):
        headers = {"X-LLM-Model": "deepseek-v9-flash", "X-LLM-Base-URL": "https://api.deepseek.com",
                   "X-LLM-Reasoning": "platform", "X-LLM-JSON-Mode": "prompt"}
        options = server.model_options_from_headers(headers)
        self.assertEqual("platform", options["reasoning_override"])
        self.assertEqual("prompt", options["json_mode_override"])

        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self):
                return b'{"choices":[{"message":{"content":"{\\"ok\\":true}"},"finish_reason":"stop"}]}'

        with patch("urllib.request.urlopen", return_value=FakeResponse()) as request:
            self.assertEqual({"ok": True}, server.call_llm("测试", "test-key", **options))
        payload = json.loads(request.call_args.args[0].data)
        self.assertNotIn("reasoning_effort", payload)
        self.assertNotIn("response_format", payload)
        self.assertNotIn("temperature", payload)

    def test_preset_request_parameters_match_flagship_capabilities(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b'{"choices":[{"message":{"content":"{\\"ok\\":true}"},"finish_reason":"stop"}]}'

        captured = []

        def fake_urlopen(request, timeout):
            captured.append(json.loads(request.data))
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            server._request_llm_content("测试", "test-key", "kimi-k3", "https://api.moonshot.cn/v1")
            server._request_llm_content("测试", "test-key", "kimi-k2.6", "https://api.moonshot.cn/v1")
            server._request_llm_content("测试", "test-key", "doubao-seed-2-1-pro-260915", "https://ark.cn-beijing.volces.com/api/v3")
            server._request_llm_content("测试", "test-key", "doubao-seed-2-0-pro-260215", "https://ark.cn-beijing.volces.com/api/v3")
            server._request_llm_content("测试", "test-key", "qwen3.8-max", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            server._request_llm_content("测试", "test-key", "qwen3.8-flash", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            server._request_llm_content("测试", "test-key", "deepseek-v4-pro", "https://api.deepseek.com")
        self.assertEqual("low", captured[0]["reasoning_effort"])
        self.assertNotIn("thinking", captured[0])
        self.assertEqual({"type": "disabled"}, captured[1]["thinking"])
        self.assertNotIn("reasoning_effort", captured[1])
        for payload in captured[2:4]:
            self.assertEqual({"type": "disabled"}, payload["thinking"])
            self.assertNotIn("reasoning_effort", payload)
        for payload in captured[4:]:
            self.assertEqual("none", payload["reasoning_effort"])
        self.assertEqual(16384, captured[0]["max_tokens"])
        self.assertEqual(16384, captured[-1]["max_tokens"])
        for payload in captured[1:-1]:
            self.assertEqual(8192, payload["max_tokens"])
        for payload in captured:
            self.assertEqual({"type": "json_object"}, payload["response_format"])

    def test_generation_uses_selected_model_for_each_llm_call(self):
        options = {"model_override": "kimi-k2.6", "base_url_override": "https://api.moonshot.cn/v1"}
        with patch.object(server, "call_llm", return_value=self.sample_result()) as call:
            server.generate_one_pager_with_llm(self.segments, "客户经理", "report", "auto", "", "test-key", options)
        self.assertEqual(options, call.call_args.kwargs)

    def test_call_llm_returns_friendly_error_after_failed_repair(self):
        with patch.object(server, "_request_llm_content", return_value='{"broken" "secret-material"}'), \
             patch.object(server.LOGGER, "warning") as warning:
            with self.assertRaisesRegex(RuntimeError, "自动修复一次"):
                server.call_llm("生成一纸通", "test-key")
        self.assertNotIn("secret-material", str(warning.call_args_list))

    def test_multi_pass_generation_uses_facts_from_final_chunk(self):
        segments = [
            {"id": f"P{i}-01", "file_name": "长文.txt", "page": i, "index": 1,
             "text": ("第%d页内容" % i) + "甲" * 6500}
            for i in range(1, 4)
        ]
        prompts = []

        def fake_call(prompt, api_key_override=""):
            prompts.append(prompt)
            if "文档证据提取助手" in prompt:
                source_id = "P3-01" if "[P3-01]" in prompt else ("P2-01" if "[P2-01]" in prompt else "P1-01")
                return {"facts": [{"kind": "结论", "text": source_id, "source_ids": [source_id]}]}
            result = self.sample_result()
            result["conclusions"][0] = {"text": "末页事实已参与汇总", "source_ids": ["P3-01"]}
            return result

        with patch.object(server, "call_llm", side_effect=fake_call):
            result = server.generate_one_pager_with_llm(segments, "管理人员", "report", "auto", "", "key")
        self.assertIn("P3-01", prompts[-1])
        self.assertEqual("P3-01", result["conclusions"][0]["source_ids"][0])

    def test_long_material_analyzes_two_chunks_together_and_keeps_source_order(self):
        barrier = threading.Barrier(2, timeout=2)
        segments = [{"id": f"P{i}-01", "file_name": "长文.txt", "page": i, "index": 1,
                     "text": f"第{i}页" + "甲" * 12000} for i in range(1, 4)]
        final_prompts = []

        def fake_call(prompt, api_key_override="", **kwargs):
            if "文档证据提取助手" in prompt:
                if "[P1-01]" in prompt or "[P2-01]" in prompt:
                    barrier.wait()
                source_id = next(f"P{i}-01" for i in range(1, 4) if f"[P{i}-01]" in prompt)
                return {"facts": [{"text": source_id, "source_ids": [source_id]}], "outline": []}
            final_prompts.append(prompt)
            return self.sample_result()

        with patch.object(server, "call_llm", side_effect=fake_call):
            server.generate_one_pager_with_llm(segments, "管理人员", "report", "auto", "", "key")
        prompt = final_prompts[0]
        self.assertLess(prompt.index('"text": "P1-01"'), prompt.index('"text": "P2-01"'))
        self.assertLess(prompt.index('"text": "P2-01"'), prompt.index('"text": "P3-01"'))

    def test_parallel_rate_limit_retries_remaining_chunks_sequentially(self):
        segments = [{"id": f"P{i}-01", "text": f"第{i}页" + "甲" * 12000}
                    for i in range(1, 4)]
        attempts = []
        lock = threading.Lock()

        def fake_call(prompt, api_key_override="", **kwargs):
            if "文档证据提取助手" not in prompt:
                return self.sample_result()
            source_id = next(f"P{i}-01" for i in range(1, 4) if f"[P{i}-01]" in prompt)
            with lock:
                attempts.append(source_id)
                first = source_id == "P1-01" and attempts.count(source_id) == 1
            if first:
                raise server.ModelRateLimitError("限流")
            return {"facts": [], "outline": []}

        with patch.object(server, "call_llm", side_effect=fake_call):
            server.generate_one_pager_with_llm(segments, "管理人员", "report", "auto", "", "key")
        self.assertEqual(2, attempts.count("P1-01"))
        self.assertIn("P3-01", attempts)

    def test_normalize_enforces_limits_and_flags_unsupported_number(self):
        result = self.sample_result()
        result["conclusions"].append({"text": "虚构增长99%", "source_ids": ["P1-01"]})
        result["conclusions"].append({"text": "第五条", "source_ids": ["P3-01"]})
        result["conclusions"].append({"text": "第六条应被移除", "source_ids": ["P3-01"]})
        normalized = server.normalize_one_pager(result, self.segments, {
            "file_name": "汇报.txt", "page_count": 3, "audience": "管理人员", "template": "report",
        })
        self.assertEqual("2.0", normalized["schema_version"])
        self.assertEqual(5, len(normalized["conclusions"]))
        unsupported = next(item for item in normalized["conclusions"] if "99%" in item["text"])
        self.assertTrue(unsupported["needs_confirmation"])
        self.assertTrue(any("99%" in warning for warning in normalized["quality_warnings"]))

    def test_docx_export_contains_editable_text(self):
        normalized = server.normalize_one_pager(self.sample_result(), self.segments, {
            "file_name": "汇报.txt", "page_count": 3, "audience": "管理人员", "template": "report",
        })
        body = server.build_one_pager_docx(normalized)
        self.assertTrue(body.startswith(b"PK"))
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("季度经营一纸通", xml)
        self.assertIn("完成渠道复盘", xml)
        self.assertNotIn("出处", xml)

    def test_compaction_removes_low_priority_volume(self):
        normalized = server.normalize_one_pager(self.sample_result(), self.segments)
        normalized["supplements"] = [{"term": str(i), "explanation": "说明" * 30} for i in range(5)]
        compacted = server.compact_one_pager(normalized)
        self.assertLessEqual(len(compacted["supplements"]), 2)
        self.assertTrue(compacted["layout"]["compact"])

    def knowledge_segments(self, kind):
        samples = {
            "product": [
                "虚构便携画板面向绘画爱好者，体验期限为7天。",
                "使用前必须检查画板支架，支架未锁定不得使用。",
                "使用流程包括打开包装、展开支架、放置画纸和收纳工具。",
            ],
            "policy": [
                "本规则适用于虚构手工社团成员，目的是规范工具借用。",
                "工具借用期限为3天，归还前必须清点配件，不得遗失工具。",
                "借用者负责归还工具，社团志愿者负责整理工具架。",
            ],
            "operation": [
                "绘画前检查画纸和画笔是否齐全。",
                "第一步铺好画纸，第二步选择画笔，第三步完成绘画。",
                "发现画板支架松动时暂停使用并请志愿者协助。",
            ],
        }
        return [
            {"id": f"P{index}-01", "file_name": f"{kind}.txt", "page": index, "index": 1, "text": text}
            for index, text in enumerate(samples[kind], 1)
        ]

    def test_training_templates_choose_matching_architecture(self):
        cases = (
            ("product", "knowledge-product", "product", "module"),
            ("policy", "knowledge-policy", "policy", "hierarchy"),
            ("operation", "knowledge-operation", "operation", "process"),
        )
        for kind, template, training_type, architecture_type in cases:
            with self.subTest(kind=kind):
                segments = self.knowledge_segments(kind)
                draft = server.local_evidence_draft(segments, "一线员工", template, "培训材料")
                normalized = server.normalize_one_pager(draft, segments, {
                    "file_name": f"{kind}.txt", "page_count": 3, "audience": "一线员工", "template": template,
                })
                self.assertEqual("3.0", normalized["schema_version"])
                self.assertEqual(training_type, normalized["meta"]["training_type"])
                self.assertEqual(architecture_type, normalized["knowledge_architecture"]["type"])
                architecture_ids = [item["id"] for item in normalized["knowledge_architecture"]["modules"]]
                knowledge_ids = [item["architecture_id"] for item in normalized["knowledge_modules"]]
                self.assertEqual(architecture_ids, knowledge_ids)

    def test_knowledge_schema_preserves_sources_and_flags_changed_number(self):
        segments = self.knowledge_segments("product")
        result = server.local_evidence_draft(segments, "客户经理", "knowledge-product", "培训材料")
        result["meta"]["overview"] = "本培训介绍虚构便携画板的适用对象、7天体验期限、支架检查、画纸放置和收纳步骤，帮助绘画爱好者了解工具特点，按步骤完成练习并在使用前检查支架是否锁定。"
        result["knowledge_modules"][0]["points"][0]["text"] = "体验期限为14天"
        normalized = server.normalize_one_pager(result, segments, {"template": "knowledge-product"})
        self.assertTrue(normalized["knowledge_modules"][0]["points"][0]["needs_confirmation"])
        self.assertTrue(any("14天" in warning for warning in normalized["quality_warnings"]))
        self.assertEqual("P1-01", normalized["knowledge_modules"][0]["points"][0]["sources"][0]["id"])

    def test_knowledge_compaction_keeps_recoverable_complete_result(self):
        segments = self.knowledge_segments("operation")
        normalized = server.normalize_one_pager(
            server.local_evidence_draft(segments, "柜员", "knowledge-operation", "培训材料"),
            segments, {"template": "knowledge-operation"},
        )
        original_title = normalized["meta"]["title"]
        compacted = server.compact_one_pager(normalized)
        self.assertTrue(compacted["layout"]["compact"])
        self.assertEqual(original_title, compacted["complete_result"]["meta"]["title"])
        self.assertEqual(len(normalized["knowledge_modules"]), len(compacted["knowledge_modules"]))

    def test_knowledge_docx_export_contains_new_sections(self):
        segments = self.knowledge_segments("policy")
        normalized = server.normalize_one_pager(
            server.local_evidence_draft(segments, "全体员工", "knowledge-policy", "培训材料"),
            segments, {"template": "knowledge-policy"},
        )
        body = server.build_one_pager_docx(normalized)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("核心结论", xml)
        self.assertIn("知识架构", xml)
        self.assertIn("关键规定", xml)
        self.assertIn("工作中怎么做", xml)

    def test_deleted_knowledge_block_stays_out_of_word_export(self):
        segments = self.knowledge_segments("policy")
        result = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料")
        result["generation_requirements"] = {
            "version": 1, "max_chars": None, "detail_target": "", "detail_depth": "normal", "tone": "plain",
            "include_overview": False, "include_architecture": False, "include_knowledge_modules": False,
            "include_practice": False, "must_keep": "", "explain_terms": False,
        }
        result["knowledge_modules"] = []
        result["key_reminders"] = []
        normalized = server.normalize_one_pager(result, segments, {"template": "knowledge-policy"})
        self.assertEqual([], normalized["knowledge_modules"])
        self.assertFalse(normalized["generation_requirements"]["include_knowledge_modules"])
        body = server.build_one_pager_docx(normalized)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertNotIn("关键规定", xml)
        self.assertNotIn("核心结论", xml)

    def test_guided_requirements_and_included_answer_survive_normalization_and_word_export(self):
        segments = self.knowledge_segments("policy")
        result = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料")
        result["generation_requirements"] = {
            "version": 1, "max_chars": 200, "detail_target": "工具借用", "detail_depth": "detailed",
            "tone": "plain", "include_overview": False, "include_architecture": False,
            "include_practice": True, "must_keep": "3天", "explain_terms": False,
        }
        result["qa_items"] = [{"question": "工具归还前做什么？", "answer": "必须清点配件。", "source_ids": ["P2-01"]}]
        normalized = server.normalize_one_pager(result, segments, {"template": "knowledge-policy"})
        self.assertEqual("3天", normalized["generation_requirements"]["must_keep"])
        self.assertEqual("P2-01", normalized["qa_items"][0]["sources"][0]["id"])
        self.assertGreater(normalized["layout"]["char_count"], 0)
        body = server.build_one_pager_docx(normalized)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("材料问答", xml)
        self.assertIn("必须清点配件", xml)
        self.assertNotIn("知识架构 ·", xml)

    def test_guided_requirements_reject_bad_limit_and_sensitive_text(self):
        base = {"version": 1, "max_chars": 500, "detail_depth": "normal", "tone": "plain",
                "detail_target": "", "must_keep": "", "include_overview": True,
                "include_architecture": True, "include_practice": True, "explain_terms": False}
        with self.assertRaisesRegex(ValueError, "字数上限"):
            server.validate_generation_requirements({**base, "max_chars": 50})
        with self.assertRaisesRegex(ValueError, "未脱敏"):
            server.validate_generation_requirements({**base, "must_keep": "手机号13800138000"})

    def test_guided_prompt_uses_priority_and_coverage_review(self):
        requirements = server.validate_generation_requirements({
            "version": 1, "max_chars": 500, "detail_depth": "detailed", "tone": "plain",
            "detail_target": "借用规则", "must_keep": "",
            "include_overview": True, "include_architecture": True,
            "include_practice": True, "explain_terms": False,
        })
        prompt = server.prompt_for_one_pager(self.knowledge_segments("policy"), "客户经理",
            "knowledge-policy", "培训材料", focus="借用规则", max_chars=500, requirements=requirements)
        self.assertIn("关注重点：借用规则", prompt)
        self.assertIn("优先详解用户指定重点", prompt)
        self.assertIn("适用对象、执行要求、时间期限", prompt)

    def test_knowledge_without_diagram_keeps_points_and_hides_diagram_in_export(self):
        segments = self.knowledge_segments("policy")
        draft = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料")
        draft["knowledge_architecture"] = {"type": "grouped", "show_diagram": False, "modules": []}
        normalized = server.normalize_one_pager(draft, segments, {"template": "knowledge-policy"})
        self.assertFalse(normalized["knowledge_architecture"]["show_diagram"])
        self.assertGreater(len(normalized["knowledge_modules"]), 0)
        self.assertTrue(normalized["coverage_review"])
        with_diagram = json.loads(json.dumps(normalized, ensure_ascii=False))
        with_diagram["knowledge_architecture"]["show_diagram"] = True
        self.assertLess(server.count_one_pager_chars(normalized), server.count_one_pager_chars(with_diagram))
        body = server.build_one_pager_docx(normalized)
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertNotIn("知识架构 ·", xml)

    def test_short_local_preview_uses_complete_source_sentences_and_skips_title_module(self):
        segments = [{"id": "P1-01", "file_name": "材料.txt", "page": 1, "index": 1,
                     "text": "虚构社团工具借用规则"},
                    {"id": "P1-02", "file_name": "材料.txt", "page": 1, "index": 2,
                     "text": "本规则适用于社团成员。工具借用包括登记和归还。"},
                    {"id": "P1-03", "file_name": "材料.txt", "page": 1, "index": 3,
                     "text": "工具须在3天内归还。"}]
        draft = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料", max_chars=500)
        self.assertEqual("本规则适用于社团成员。工具借用包括登记和归还。", draft["meta"]["overview"])
        self.assertFalse(draft["knowledge_architecture"]["show_diagram"])
        self.assertEqual("P1-02", draft["knowledge_modules"][0]["points"][0]["source_ids"][0])
        self.assertEqual(segments[1]["text"], draft["knowledge_modules"][0]["points"][0]["text"])

    def test_generate_endpoint_accepts_guided_requirements_without_model_key(self):
        requirements = {"version": 1, "max_chars": 200, "detail_depth": "normal", "tone": "plain",
                        "detail_target": "渠道复盘", "must_keep": "6月底", "include_overview": True,
                        "include_architecture": True, "include_practice": True, "explain_terms": False}
        payload = json.dumps({"document_id": "test-doc", "confirmation_token": "test-token",
                              "audience": "客户经理", "template": "knowledge-auto", "requirements": requirements}).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        with patch.object(server, "get_confirmation", return_value={"primary_masked_segments": self.segments}), \
             patch.object(server, "get_document_session", return_value={"file_name": "汇报.txt", "page_count": 3}), \
             patch.object(server, "generate_one_pager_with_llm", side_effect=RuntimeError("未配置 LLM_API_KEY")):
            handler.handle_generate()
        response = json.loads(handler.wfile.getvalue())
        self.assertEqual([200], statuses)
        self.assertEqual(200, response["one_pager"]["generation_requirements"]["max_chars"])
        self.assertLessEqual(response["one_pager"]["layout"]["char_count"], 200)
        self.assertFalse(server.missing_required_phrases(response["one_pager"], requirements))
        self.assertIn("qa_items", response["one_pager"])

    def test_guided_generation_rewrites_and_enforces_500_and_800(self):
        segments = self.knowledge_segments("policy")
        draft = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料")
        for limit in (500, 800):
            with self.subTest(limit=limit):
                requirements = {"version": 1, "max_chars": limit, "detail_depth": "normal", "tone": "plain",
                    "detail_target": "", "must_keep": "", "include_overview": True,
                    "include_architecture": True, "include_practice": True, "explain_terms": False}
                payload = json.dumps({"document_id": "test-doc", "confirmation_token": "test-token",
                    "audience": "客户经理", "template": "knowledge-policy", "requirements": requirements}).encode()
                handler = server.Handler.__new__(server.Handler)
                handler.headers = {"Content-Length": str(len(payload)), "X-LLM-API-Key": "test-key"}
                handler.rfile = io.BytesIO(payload)
                handler.wfile = io.BytesIO()
                statuses = []
                handler.send_response = statuses.append
                handler.send_header = lambda name, value: None
                handler.end_headers = lambda: None
                with patch.object(server, "get_confirmation", return_value={"primary_masked_segments": segments}), \
                     patch.object(server, "get_document_session", return_value={"file_name": "政策.txt", "page_count": 2}), \
                     patch.object(server, "generate_one_pager_with_llm", return_value=draft), \
                     patch.object(server, "revise_one_pager_to_budget", return_value=draft) as rewrite:
                    handler.handle_generate()
                response = json.loads(handler.wfile.getvalue())
                self.assertEqual([200], statuses, response)
                self.assertLessEqual(response["one_pager"]["layout"]["char_count"], limit)
                if server.count_one_pager_chars(server.normalize_one_pager(draft, segments,
                        {"template": "knowledge-policy"})) > limit:
                    self.assertGreater(rewrite.call_count, 0)

    def test_budget_selection_preserves_required_phrase_and_whole_points(self):
        segments = self.knowledge_segments("policy")
        requirements = {"version": 1, "max_chars": 200, "detail_depth": "normal", "tone": "plain",
            "detail_target": "", "must_keep": "3天", "include_overview": False,
            "include_architecture": True, "include_practice": True, "explain_terms": False}
        draft = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料")
        draft["generation_requirements"] = requirements
        normalized = server.normalize_one_pager(draft, segments, {"template": "knowledge-policy"})
        selected = server.select_within_budget(normalized, requirements)
        self.assertLessEqual(server.count_one_pager_chars(selected), 200)
        self.assertFalse(server.missing_required_phrases(selected, requirements))
        source_points = {point["text"] for group in normalized["knowledge_modules"] for point in group["points"]}
        self.assertTrue(all(point["text"] in source_points for group in selected["knowledge_modules"] for point in group["points"]))

    def test_included_answer_is_kept_within_total_budget(self):
        segments = self.knowledge_segments("policy")
        draft = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料")
        draft["generation_requirements"] = {"version": 1, "max_chars": 500, "detail_depth": "normal", "tone": "plain",
            "detail_target": "", "must_keep": "", "include_overview": True,
            "include_architecture": True, "include_practice": True, "explain_terms": False}
        draft["qa_items"] = [{"question": "工具归还前做什么？", "answer": "清点配件。", "source_ids": [segments[0]["id"]]}]
        payload = json.dumps({"document_id": "test-doc", "confirmation_token": "test-token",
            "one_pager": draft}).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        with patch.object(server, "get_confirmation", return_value={"primary_masked_segments": segments}):
            handler.handle_compact_one_pager()
        response = json.loads(handler.wfile.getvalue())
        self.assertEqual([200], statuses, response)
        self.assertEqual(1, len(response["one_pager"]["qa_items"]))
        self.assertLessEqual(response["one_pager"]["layout"]["char_count"], 500)

    def test_compact_button_compacts_even_below_word_limit(self):
        segments = self.knowledge_segments("policy")
        draft = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料")
        draft["generation_requirements"] = {"version": 1, "max_chars": 2000, "detail_depth": "normal",
            "tone": "plain", "detail_target": "", "must_keep": "", "include_overview": True,
            "include_architecture": True, "include_practice": True, "explain_terms": False}
        self.assertLess(server.count_one_pager_chars(draft), 2000)
        payload = json.dumps({"document_id": "test-doc", "confirmation_token": "test-token", "one_pager": draft}).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        with patch.object(server, "get_confirmation", return_value={"primary_masked_segments": segments}):
            handler.handle_compact_one_pager()
        response = json.loads(handler.wfile.getvalue())
        self.assertEqual([200], statuses, response)
        self.assertTrue(response["one_pager"]["layout"]["compact"])
        self.assertIn("complete_result", response["one_pager"])

    def test_long_model_field_is_preserved_then_rewritten_to_total_budget(self):
        segments = self.knowledge_segments("policy")
        draft = server.local_evidence_draft(segments, "客户经理", "knowledge-policy", "培训材料")
        short_draft = json.loads(json.dumps(draft, ensure_ascii=False))
        long_text = segments[0]["text"] * 20
        draft["knowledge_modules"][0]["points"][0]["text"] = long_text
        requirements = {"version": 1, "max_chars": 500, "detail_depth": "normal", "tone": "plain",
            "detail_target": "", "must_keep": "", "include_overview": True,
            "include_architecture": True, "include_practice": True, "explain_terms": False}
        draft["generation_requirements"] = requirements
        normalized = server.normalize_one_pager(draft, segments, {"template": "knowledge-policy"})
        self.assertEqual(long_text, normalized["knowledge_modules"][0]["points"][0]["text"])
        payload = json.dumps({"document_id": "test-doc", "confirmation_token": "test-token",
            "audience": "客户经理", "template": "knowledge-policy", "requirements": requirements}).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.headers = {"Content-Length": str(len(payload)), "X-LLM-API-Key": "test-key"}
        handler.rfile = io.BytesIO(payload)
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        with patch.object(server, "get_confirmation", return_value={"primary_masked_segments": segments}), \
             patch.object(server, "get_document_session", return_value={"file_name": "政策.txt", "page_count": 2}), \
             patch.object(server, "generate_one_pager_with_llm", return_value=draft), \
             patch.object(server, "revise_one_pager_to_budget", return_value=short_draft) as rewrite:
            handler.handle_generate()
        response = json.loads(handler.wfile.getvalue())
        self.assertEqual([200], statuses, response)
        self.assertGreater(rewrite.call_count, 0)
        self.assertLessEqual(response["one_pager"]["layout"]["char_count"], 500)

    def test_knowledge_docx_export_sets_cjk_font_and_language_on_all_text_runs(self):
        segments = self.knowledge_segments("policy")
        normalized = server.normalize_one_pager(
            server.local_evidence_draft(segments, "全体员工", "knowledge-policy", "培训材料"),
            segments, {"template": "knowledge-policy"},
        )
        font_name = "Codex Test CJK Sans"
        with patch.dict(os.environ, {"DOCX_CJK_FONT": font_name}):
            body = server.build_one_pager_docx(normalized)

        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            document_root = ET.fromstring(archive.read("word/document.xml"))
            styles_root = ET.fromstring(archive.read("word/styles.xml"))

        east_asia = "{%(w)s}eastAsia" % namespace
        language_value = "{%(w)s}val" % namespace
        text_runs = [
            run for run in document_root.findall(".//w:r", namespace)
            if "".join(node.text or "" for node in run.findall(".//w:t", namespace)).strip()
        ]
        self.assertGreater(len(text_runs), 10)
        for run in text_runs:
            fonts = run.find("w:rPr/w:rFonts", namespace)
            language = run.find("w:rPr/w:lang", namespace)
            self.assertIsNotNone(fonts)
            self.assertEqual(font_name, fonts.get(east_asia))
            self.assertIsNotNone(language)
            self.assertEqual("zh-CN", language.get(language_value))
            self.assertEqual("zh-CN", language.get(east_asia))

        default_fonts = styles_root.find(
            "w:docDefaults/w:rPrDefault/w:rPr/w:rFonts", namespace
        )
        default_language = styles_root.find(
            "w:docDefaults/w:rPrDefault/w:rPr/w:lang", namespace
        )
        self.assertIsNotNone(default_fonts)
        self.assertEqual(font_name, default_fonts.get(east_asia))
        self.assertIsNotNone(default_language)
        self.assertEqual("zh-CN", default_language.get(language_value))
        self.assertEqual("zh-CN", default_language.get(east_asia))

    def test_docx_export_rejects_environment_without_a_cjk_font(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(server.sys, "platform", "linux"), \
                patch.object(server.Path, "exists", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "未检测到可用的中文字体"):
                server._select_docx_cjk_font()


if __name__ == "__main__":
    unittest.main()
