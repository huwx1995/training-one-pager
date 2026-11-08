from __future__ import annotations

import ipaddress
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


RULE_VERSION = "bank-cn-2026.11-v2"
LARGE_AMOUNT_RMB = Decimal("500000")

TYPE_LABELS = {
    "name": "姓名", "id_card": "身份证号", "passport": "护照号", "phone": "手机号",
    "landline": "固定电话", "email": "邮箱", "address": "地址", "bank_card": "银行卡号",
    "social_security": "社保号", "provident_fund": "公积金账号", "customer_id": "客户号",
    "account": "银行账号", "policy_no": "保单号", "loan_contract": "贷款合同号",
    "wealth_agreement": "理财协议号", "transaction_no": "交易流水号", "login_name": "登录名",
    "employee_id": "员工工号", "system_name": "内部系统", "internal_ip": "内部IP",
    "internal_domain": "内部域名", "branch_code": "机构内部编码",
    "approval_opinion": "内部审批意见", "organization": "机构", "large_amount": "大额交易金额",
    "credit_limit": "授信额度", "rate": "利率费率", "asset_scale": "客户资产规模",
    "financial_data": "未公开财务数据", "risk_rating": "风险评级", "credit_code": "统一社会信用代码",
    "corporate_account": "对公账号", "contract_party": "合同相对方", "contract_clause": "合同敏感条款",
    "credit_report": "征信信息", "aml_flag": "反洗钱标识", "sanctions": "制裁名单结果",
    "secret": "密码密钥令牌", "document_image": "证件影像描述", "custom": "自定义",
}

CATEGORY_LABELS = {
    "personal": "个人身份信息", "customer_account": "客户与账户信息", "internal": "机构与内部信息",
    "financial": "金额与经营敏感信息", "corporate": "企业与对公信息", "regulatory": "监管与高风险敏感项",
    "custom": "自定义",
}

PUBLIC_EMAIL_DOMAINS = {"qq.com", "163.com", "126.com", "gmail.com", "outlook.com", "hotmail.com", "sina.com"}
ORG_GENERIC_VALUES = {
    "银行", "分行", "支行", "公司", "中心", "机构", "医疗机构", "国际机构", "其他银行",
    "企业电子银行", "企业网上银行", "企业手机银行", "个人网上银行", "手机银行", "网上银行",
    "网点支行", "所在分支行", "由分支行", "通过银行", "近一年银行", "中级银行", "小小银行",
    "所属机构", "所在机构", "客户机构", "合作机构",
}
ORG_BAD_PREFIXES = ("通过", "由", "在", "对", "向", "每增加一个", "其中", "整合", "则以", "最近的", "个人客户", "企业客户", "客户经理", "管户客户经理", "年代表", "贵宾理财经理", "近一年")
NAME_BAD_WORDS = ("客户", "经理", "负责人", "数量", "标准", "银行", "机构", "营销", "产品")


def _meta(rule_id: str, kind: str, category: str, sensitivity: str, method: str,
          reason: str, default_highlight: bool = True) -> dict[str, Any]:
    return {"rule_id": rule_id, "type": kind, "type_label": TYPE_LABELS[kind],
            "category": category, "category_label": CATEGORY_LABELS[category],
            "sensitivity": sensitivity, "match_method": method, "reason": reason,
            "default_highlight": default_highlight, "rule_version": RULE_VERSION}


RULE_CATALOG = {
    "personal.name": _meta("personal.name", "name", "personal", "high", "词典+上下文", "由姓名或人员角色字段识别"),
    "personal.id_card": _meta("personal.id_card", "id_card", "personal", "high", "正则+校验位", "符合居民身份证格式并通过校验"),
    "personal.passport": _meta("personal.passport", "passport", "personal", "high", "正则+上下文", "由护照或证件字段识别"),
    "personal.mobile": _meta("personal.mobile", "phone", "personal", "high", "正则", "符合中国大陆手机号格式"),
    "personal.landline": _meta("personal.landline", "landline", "personal", "medium", "正则+上下文", "由固定电话字段识别"),
    "personal.email": _meta("personal.email", "email", "personal", "high", "正则", "符合邮箱地址格式"),
    "personal.address": _meta("personal.address", "address", "personal", "high", "词典+上下文", "由家庭或联系地址字段识别"),
    "personal.bank_card": _meta("personal.bank_card", "bank_card", "personal", "high", "正则+Luhn", "符合银行卡号格式并通过校验"),
    "personal.social_security": _meta("personal.social_security", "social_security", "personal", "high", "正则+上下文", "由社保号码字段识别"),
    "personal.provident_fund": _meta("personal.provident_fund", "provident_fund", "personal", "high", "正则+上下文", "由公积金账号字段识别"),
    "account.customer_id": _meta("account.customer_id", "customer_id", "customer_account", "high", "正则+上下文", "由客户号或CIF字段识别"),
    "account.account": _meta("account.account", "account", "customer_account", "high", "正则+上下文", "由账户字段识别"),
    "account.policy": _meta("account.policy", "policy_no", "customer_account", "high", "正则+上下文", "由保单号字段识别"),
    "account.loan_contract": _meta("account.loan_contract", "loan_contract", "customer_account", "high", "正则+上下文", "由贷款合同字段识别"),
    "account.wealth_agreement": _meta("account.wealth_agreement", "wealth_agreement", "customer_account", "high", "正则+上下文", "由理财协议字段识别"),
    "account.transaction": _meta("account.transaction", "transaction_no", "customer_account", "high", "正则+上下文", "由交易流水或凭证字段识别"),
    "account.login": _meta("account.login", "login_name", "customer_account", "high", "正则+上下文", "由网银或手机银行登录字段识别"),
    "internal.employee": _meta("internal.employee", "employee_id", "internal", "high", "正则+上下文", "由员工工号或柜员号字段识别"),
    "internal.system": _meta("internal.system", "system_name", "internal", "medium", "词典+上下文", "由系统或平台专有名称识别"),
    "internal.system_generic": _meta("internal.system_generic", "system_name", "internal", "low", "词典", "通用系统称谓，请人工判断", False),
    "internal.ip": _meta("internal.ip", "internal_ip", "internal", "high", "正则+网段校验", "识别到私网IP地址"),
    "internal.domain": _meta("internal.domain", "internal_domain", "internal", "high", "正则+上下文", "识别到内部域名、主机或内网URL"),
    "internal.email": _meta("internal.email", "email", "internal", "high", "正则+域名判断", "识别到非公共邮箱域名"),
    "internal.branch_code": _meta("internal.branch_code", "branch_code", "internal", "medium", "正则+上下文", "由机构或网点内部编码字段识别"),
    "internal.approval": _meta("internal.approval", "approval_opinion", "internal", "high", "词典+上下文", "识别到内部审批或复核意见"),
    "internal.organization": _meta("internal.organization", "organization", "internal", "medium", "后缀+上下文", "识别到企业或分支机构名称"),
    "financial.large_amount": _meta("financial.large_amount", "large_amount", "financial", "high", "金额解析+上下文", "交易金额达到产品内置大额候选阈值"),
    "financial.credit_limit": _meta("financial.credit_limit", "credit_limit", "financial", "high", "金额解析+上下文", "识别到授信或可用额度"),
    "financial.rate": _meta("financial.rate", "rate", "financial", "medium", "正则+上下文", "识别到客户专属利率或费率"),
    "financial.asset": _meta("financial.asset", "asset_scale", "financial", "high", "金额解析+上下文", "识别到客户资产或余额"),
    "financial.unpublished": _meta("financial.unpublished", "financial_data", "financial", "high", "词典+上下文", "识别到内部或未公开财务数据"),
    "financial.risk": _meta("financial.risk", "risk_rating", "financial", "high", "词典+上下文", "识别到客户或授信风险评级结果"),
    "financial.generic": _meta("financial.generic", "large_amount", "financial", "low", "金额正则", "普通金额或比例，缺少敏感业务上下文", False),
    "corporate.credit_code": _meta("corporate.credit_code", "credit_code", "corporate", "high", "正则+校验位", "符合统一社会信用代码格式"),
    "corporate.account": _meta("corporate.account", "corporate_account", "corporate", "high", "正则+上下文", "由对公结算账户字段识别"),
    "corporate.party": _meta("corporate.party", "contract_party", "corporate", "medium", "词典+上下文", "识别到合同相对方"),
    "corporate.clause": _meta("corporate.clause", "contract_clause", "corporate", "medium", "词典+上下文", "识别到合同敏感条款内容"),
    "regulatory.credit": _meta("regulatory.credit", "credit_report", "regulatory", "high", "词典+上下文", "识别到客户征信结果"),
    "regulatory.aml": _meta("regulatory.aml", "aml_flag", "regulatory", "high", "词典+上下文", "识别到反洗钱审核结果"),
    "regulatory.sanctions": _meta("regulatory.sanctions", "sanctions", "regulatory", "high", "词典+上下文", "识别到制裁或名单命中结果"),
    "regulatory.secret": _meta("regulatory.secret", "secret", "regulatory", "high", "正则+上下文", "识别到密码、密钥或访问令牌"),
    "regulatory.image": _meta("regulatory.image", "document_image", "regulatory", "medium", "词典", "识别到证件影像或扫描件描述"),
}

# 培训材料优先避免把业务说明整段遮掉。其余规则仍可供人工检查，默认不标黄。
DEFAULT_HIGHLIGHT_RULES = {
    "personal.name", "personal.id_card", "personal.passport", "personal.mobile", "personal.email",
    "personal.bank_card", "personal.social_security", "personal.provident_fund",
    "account.customer_id", "account.account", "account.policy", "account.loan_contract",
    "account.wealth_agreement", "account.transaction", "account.login",
    "internal.employee", "internal.ip", "internal.domain", "internal.email", "corporate.credit_code",
    "corporate.account", "regulatory.secret",
}
for _rule_id, _rule in RULE_CATALOG.items():
    _rule["default_highlight"] = _rule_id in DEFAULT_HIGHLIGHT_RULES


def _luhn(value: str) -> bool:
    digits = [int(ch) for ch in re.sub(r"\D", "", value)]
    if not 16 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _valid_id_card(value: str) -> bool:
    value = value.upper()
    if not re.fullmatch(r"\d{17}[0-9X]", value):
        return False
    try:
        date(int(value[6:10]), int(value[10:12]), int(value[12:14]))
    except ValueError:
        return False
    weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    checks = "10X98765432"
    return checks[sum(int(value[i]) * weights[i] for i in range(17)) % 11] == value[-1]


def _valid_credit_code(value: str) -> bool:
    alphabet = "0123456789ABCDEFGHJKLMNPQRTUWXY"
    weights = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)
    value = value.upper()
    if not re.fullmatch(r"[0-9A-HJ-NPQRTUWXY]{18}", value):
        return False
    return alphabet[(31 - sum(alphabet.index(value[i]) * weights[i] for i in range(17)) % 31) % 31] == value[-1]


def _money_value(raw: str) -> Decimal | None:
    compact = raw.replace(",", "").replace("，", "").replace("人民币", "").replace("¥", "").replace("￥", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(亿元|万元|万|元)?", compact)
    if not match:
        return None
    try:
        value = Decimal(match.group(1))
    except InvalidOperation:
        return None
    unit = match.group(2) or "元"
    if unit == "亿元": value *= Decimal("100000000")
    elif unit in {"万元", "万"}: value *= Decimal("10000")
    return value


def _add(output: list[dict[str, Any]], rule_id: str, value: str, start: int, end: int,
         reason: str | None = None, **overrides: Any) -> None:
    value = value.strip()
    if not value:
        return
    item = dict(RULE_CATALOG[rule_id])
    item.update(overrides)
    item.update({"value": value, "start": start, "end": end})
    if reason:
        item["reason"] = reason
    output.append(item)


def _labeled(text: str, labels: str, value_pattern: str):
    return re.finditer(rf"(?:{labels})\s*(?:为|是|[:：])?\s*({value_pattern})", text, re.I)


def find_bank_sensitive_matches(text: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    # Strong structured identifiers.
    for match in re.finditer(r"(?<![0-9A-Za-z])\d{17}[0-9Xx](?![0-9A-Za-z])", text):
        if _valid_id_card(match.group()): _add(output, "personal.id_card", match.group(), *match.span())
    for match in re.finditer(r"(?<!\d)1[3-9]\d{9}(?!\d)", text):
        _add(output, "personal.mobile", match.group(), *match.span())
    for match in re.finditer(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])", text):
        _add(output, "personal.email", match.group(), *match.span())
        domain = match.group().rsplit("@", 1)[-1].lower()
        if domain not in PUBLIC_EMAIL_DOMAINS:
            _add(output, "internal.email", match.group(), *match.span())
    for match in re.finditer(r"(?<!\d)(?:\d[ -]?){15,18}\d(?!\d)", text):
        if _luhn(match.group()): _add(output, "personal.bank_card", match.group(), *match.span())
    # 明确的卡号字段即使未通过 Luhn，也保留为低敏、默认不高亮候选，交由人工判断。
    # 这样既不把随机长数字当作银行卡，也不会漏掉测试数据、脱敏后的占位号或录入错误号码。
    for match in _labeled(text, r"银行卡号|借记卡号|信用卡号|卡号", r"(?:\d[ -]?){15,18}\d"):
        value = match.group(1)
        if not _luhn(value):
            _add(
                output, "personal.bank_card", value, *match.span(1),
                sensitivity="low", confidence="low", default_highlight=False,
                reason="字段表明该值可能是银行卡号，但未通过 Luhn 校验，请人工确认",
            )
    for match in re.finditer(r"(?<![0-9A-Z])[0-9A-HJ-NPQRTUWXY]{18}(?![0-9A-Z])", text, re.I):
        if _valid_credit_code(match.group()): _add(output, "corporate.credit_code", match.group(), *match.span())
    for match in re.finditer(r"(?<!\d)(?:10\.(?:\d{1,3}\.){2}\d{1,3}|192\.168\.(?:\d{1,3}\.)\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.)\d{1,3})(?::\d{1,5})?(?!\d)", text):
        host = match.group().split(":", 1)[0]
        try: ipaddress.ip_address(host)
        except ValueError: continue
        _add(output, "internal.ip", match.group(), *match.span())
    for match in re.finditer(r"(?i)\b(?:https?://)?(?:[a-z0-9-]+\.)+(?:local|internal)(?::\d{1,5})?(?:/[\w./?%&=-]*)?", text):
        _add(output, "internal.domain", match.group(), *match.span())
    for match in re.finditer(r"(?i)\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b", text):
        _add(output, "regulatory.secret", match.group(), *match.span(), "符合JWT令牌格式")

    labeled_rules = [
        ("personal.name", r"客户姓名|员工姓名|姓名|联系人|负责人|复核人|户名|经办人", r"[\u4e00-\u9fff·]{2,8}"),
        ("personal.passport", r"护照号|护照号码|Passport(?: No)?", r"[A-Z][A-Z0-9]{7,11}"),
        ("personal.landline", r"固定电话|座机|联系电话|办公电话", r"(?:0\d{2,3}-?)?\d{7,8}(?:-\d{1,6})?"),
        ("personal.address", r"家庭住址|住宅地址|联系地址|住址|所在地|地址", r"[^，。；;\n]{4,80}"),
        ("personal.social_security", r"社保号|社会保障号码", r"[A-Za-z0-9-]{8,30}"),
        ("personal.provident_fund", r"公积金账号|住房公积金账户", r"[A-Za-z0-9-]{6,30}"),
        ("account.customer_id", r"客户号|客户编号|CIF", r"[A-Za-z0-9-]{6,32}"),
        ("account.account", r"银行账号|账户号|账号|结算账户", r"[A-Za-z0-9-]{8,32}"),
        ("account.policy", r"保单号|保险单号", r"[A-Za-z0-9-]{6,40}"),
        ("account.loan_contract", r"贷款合同号|借款合同编号", r"[A-Za-z0-9-]{6,50}"),
        ("account.wealth_agreement", r"理财协议号|认购协议编号|产品协议号", r"[A-Za-z0-9-]{6,50}"),
        ("account.transaction", r"交易流水号|流水号|交易序号|渠道流水|凭证号", r"[A-Za-z0-9-]{6,50}"),
        ("account.login", r"登录名|用户名|网银用户|手机银行用户名", r"[A-Za-z0-9_.@-]{3,50}"),
        ("internal.employee", r"工号|员工号|柜员号|客户经理编号", r"[A-Za-z0-9-]{3,30}"),
        ("internal.branch_code", r"机构号|网点号|分行代码|支行代码", r"[A-Za-z0-9-]{3,30}"),
        ("corporate.account", r"对公账户|对公账号|结算账号|基本户|一般户", r"[A-Za-z0-9-]{8,32}"),
        ("financial.risk", r"风险等级|评级结果|授信评级|预警等级", r"[^，。；;\n]{1,30}"),
    ]
    for rule_id, labels, pattern in labeled_rules:
        for match in _labeled(text, labels, pattern):
            value = match.group(1).strip()
            if rule_id == "personal.name" and any(word in value for word in NAME_BAD_WORDS): continue
            if rule_id == "personal.address" and re.match(r"(?i)(?:https?://|[\w.-]+\.(?:local|internal))", value):
                continue
            highlight = rule_id in DEFAULT_HIGHLIGHT_RULES
            if rule_id == "personal.name":
                highlight = bool(re.search(r"[:：]\s*$", text[match.start():match.start(1)]))
            _add(output, rule_id, value, *match.span(1), default_highlight=highlight)

    # Organizations: complete suffix first; generic descriptions are rejected.
    org_pattern = re.compile(r"([\u4e00-\u9fffA-Za-z0-9（）()·]{2,36}?(?:股份有限公司|有限责任公司|有限公司|银行(?:[\u4e00-\u9fff]{2,10}(?:分行|支行))?|分行|支行|公司|中心|机构))")
    for match in org_pattern.finditer(text):
        value = match.group(1)
        # 机构前常出现“单位：”“任职于”等关系词，规则只保留真正的机构名称。
        prefix = re.search(r"(?:单位|任职于|就职于|供职于|合作方|相对方|甲方|乙方)[：:]?([^：:，。；;\n]+)$", value)
        if prefix:
            value = prefix.group(1)
        value = re.sub(r"^(?:是|为|与|和|在|于)", "", value).strip()
        start = match.end(1) - len(value)
        if value in ORG_GENERIC_VALUES or any(value.startswith(prefix) for prefix in ORG_BAD_PREFIXES): continue
        confidence = "high" if value.endswith(("股份有限公司", "有限责任公司", "有限公司")) or "机构名称" in text else "low"
        _add(output, "internal.organization", value, start, match.end(1), confidence=confidence)

    for match in re.finditer(r"(?:系统名称|内部系统|业务平台)\s*(?:为|是|[:：])?\s*([\u4e00-\u9fffA-Za-z0-9_-]{2,30}(?:系统|平台|应用))", text):
        _add(output, "internal.system", match.group(1), *match.span(1))
    for match in re.finditer(r"(?:核心系统|业务系统|管理平台)", text):
        if not any(item["start"] <= match.start() and item["end"] >= match.end() for item in output if item["type"] == "system_name"):
            _add(output, "internal.system_generic", match.group(), *match.span())

    # Contextual financial and internal results.
    amount_pattern = r"(?:人民币\s*)?[¥￥]?\s*\d[\d,，]*(?:\.\d+)?\s*(?:亿元|万元|万|元)"
    context_rules = [
        ("financial.credit_limit", r"授信额度|敞口|可用额度|贷款额度", amount_pattern),
        ("financial.asset", r"AUM|资产规模|金融资产|存款余额|客户资产", amount_pattern),
        ("financial.unpublished", r"内部|未公开|预测|预算|实际完成", rf"(?:收入|利润|成本|营收|余额)?\s*{amount_pattern}"),
    ]
    for rule_id, labels, pattern in context_rules:
        for match in re.finditer(rf"(?:{labels})[^，。；;\n]{{0,24}}?({pattern})", text, re.I):
            _add(output, rule_id, match.group(1), *match.span(1))
    for match in re.finditer(rf"(?:交易|转账|存款|取款|汇款|支付)[^，。；;\n]{{0,20}}?({amount_pattern})", text):
        if (_money_value(match.group(1)) or 0) >= LARGE_AMOUNT_RMB:
            _add(output, "financial.large_amount", match.group(1), *match.span(1))
    for match in re.finditer(r"(?:客户专属|优惠|内部定价)[^，。；;\n]{0,20}?((?:\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*(?:BP|基点)))", text, re.I):
        _add(output, "financial.rate", match.group(1), *match.span(1))
    # 缺少客户、交易或内部语境的金额和比例仅作为低敏候选，默认不高亮。
    for match in re.finditer(rf"{amount_pattern}|\d+(?:\.\d+)?\s*(?:%|BP|基点)", text, re.I):
        _add(output, "financial.generic", match.group(), *match.span(), confidence="low")

    phrase_rules = [
        ("internal.approval", r"(?:审批意见|复核意见|会签意见|不同意原因)\s*(?:为|是|[:：])?\s*([^，。；;\n]{2,100})"),
        ("corporate.party", r"(?:甲方|乙方|供应商|合作方|相对方)\s*(?:为|是|[:：])?\s*([^，。；;\n]{2,60})"),
        ("corporate.clause", r"(?:保密|违约金|专属定价|返点|结算条件|特殊约定)\s*(?:为|是|[:：])?\s*([^。；;\n]{2,120})"),
        ("regulatory.credit", r"(?:征信|逾期|查询记录|不良记录|负债)[^，。；;\n]{0,50}"),
        ("regulatory.aml", r"(?:可疑交易|高风险客户|受益所有人|名单监控|AML)[^，。；;\n]{0,50}"),
        ("regulatory.sanctions", r"(?:制裁名单|黑名单|观察名单)[^，。；;\n]{0,30}?(?:疑似命中|未命中|命中)"),
        ("regulatory.image", r"(?:身份证正反面|护照照片|营业执照影像|证件扫描件)"),
    ]
    for rule_id, pattern in phrase_rules:
        for match in re.finditer(pattern, text, re.I):
            value = match.group(1) if match.lastindex else match.group()
            start, end = match.span(1) if match.lastindex else match.span()
            if value.startswith("请填写"): continue
            _add(output, rule_id, value.strip(), start, end)
    for match in re.finditer(r"(?i)(?:password|passwd|secret|token|api[_-]?key|access[_-]?key|密码|密钥|令牌)\s*(?:=|:|：)\s*([^\s,，;；]{4,200})", text):
        _add(output, "regulatory.secret", match.group(1), *match.span(1))

    # 合并完全相同的范围，并用更具体的规则覆盖通用规则；所有规则来源仍保留。
    rank = {"high": 3, "medium": 2, "low": 1}
    specific_rank = {
        "personal.provident_fund": 90, "personal.social_security": 90,
        "corporate.account": 85, "personal.bank_card": 80,
        "corporate.party": 75, "internal.email": 70,
        "financial.credit_limit": 70, "financial.asset": 70,
        "financial.unpublished": 70, "financial.large_amount": 70,
        "financial.rate": 70, "financial.generic": 1,
        "account.account": 10, "personal.email": 10,
    }
    exact_ranges: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for item in output:
        exact_ranges.setdefault((item["start"], item["end"]), []).append(item)
    merged: list[dict[str, Any]] = []
    for same_range in exact_ranges.values():
        winner = max(same_range, key=lambda item: (
            rank[item["sensitivity"]], specific_rank.get(item["rule_id"], 50)
        ))
        winner = dict(winner)
        winner["rule_ids"] = list(dict.fromkeys(item["rule_id"] for item in same_range))
        merged.append(winner)
    ordered = sorted(merged, key=lambda item: (
        item["start"], -(item["end"] - item["start"]), -rank[item["sensitivity"]]
    ))
    chosen: list[dict[str, Any]] = []
    for item in ordered:
        covering = next((other for other in chosen
                         if other["start"] <= item["start"] and other["end"] >= item["end"]
                         and rank[other["sensitivity"]] >= rank[item["sensitivity"]]), None)
        if covering:
            covering["rule_ids"] = list(dict.fromkeys(covering.get("rule_ids", []) + item.get("rule_ids", [])))
            continue
        chosen.append(item)
    return chosen


def normalize_term(value: str, kind: str) -> str:
    value = value.strip()
    if kind in {"id_card", "bank_card", "phone", "landline", "account", "corporate_account"}:
        return re.sub(r"[\s-]", "", value).upper()
    return value.casefold()
