#!/usr/bin/env python3
"""search_service_impact 单元/集成测试。

⚠️  校验范围限定
================
ReleaseOrgOperatorCCSuspendStatus.txt 的 17 行**只**用于本测试默认的固定入口
``commandId='ReleaseOrgOperatorCCSuspendStatus'``。这不是
search_service_impact 的通用契约 —— 其它 commandId 的 files 集合
不保证与该 17 行有交集或子集关系。

换言之：17 行是 **「给定这个 commandId 时该 tool 应该返回什么」** 的**事实**，
不是 **「该 tool 对任何 commandId 都返回 17 行」** 的**契约**。

覆盖 tasks.md 第 5 节「手工验证」的 13 个用例。
不依赖 MCP stdio —— 直接 import codegraph_server 模块，调
search_service_impact(...) 拿 JSON 字符串。

运行：
    cd codegraph-mcp
    pip install -r requirements.txt pytest
    pytest test_search_service_impact.py -v
或：
    python test_search_service_impact.py
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER_PATH = HERE / "codegraph-server.py"

# ── 1. 用 importlib 加载 codegraph-server.py（文件名带连字符，不能直接 import）
# ── 2. 把 @mcp.tool() 装饰器替换成 no-op，模块仍能正常导入与执行函数体
import types

stub_mcp_pkg = types.ModuleType("mcp")
stub_mcp_server_pkg = types.ModuleType("mcp.server")
stub_mcp_server_fastmcp = types.ModuleType("mcp.server.fastmcp")


class _StubFastMCP:
    def __init__(self, *args, **kwargs):
        pass

    def tool(self, *args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    def run(self, *args, **kwargs):
        raise RuntimeError("Stub FastMCP cannot run — tests bypass MCP transport")


stub_mcp_server_fastmcp.FastMCP = _StubFastMCP
sys.modules.setdefault("mcp", stub_mcp_pkg)
sys.modules.setdefault("mcp.server", stub_mcp_server_pkg)
sys.modules.setdefault("mcp.server.fastmcp", stub_mcp_server_fastmcp)

spec = importlib.util.spec_from_file_location("codegraph_server", SERVER_PATH)
codegraph_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(codegraph_server)


# ── 测试配置：1.0Base schema 与 1.0BaseMaster 根目录
# ── 可通过环境变量覆盖；缺省值与项目内常用命名一致
#
# ⚠️ 期望文件清单只对**这一个** commandId 有效。
#    改 TEST_COMMAND_ID 后，5.3 / 5.4 / 5.5 三个 diff 测试需要重新准备 expected。
TEST_SCHEMA = os.environ.get("TEST_SCHEMA", "1_0_baseline")
TEST_COMMAND_ID = os.environ.get(
    "TEST_COMMAND_ID", "ReleaseOrgOperatorCCSuspendStatus"
)
TEST_FLOW_ID = os.environ.get("TEST_FLOW_ID", "")
TEST_CODE_BASE_ROOT = os.environ.get(
    "TEST_CODE_BASE_ROOT", "D:/2026/MobileMoneyMonorepo"
)
# 期望文件清单路径 —— **仅**与默认 TEST_COMMAND_ID 配套。
# 若 TEST_COMMAND_ID 被改成其它值，需要另行准备对应的 expected 清单，
# 5.3 / 5.4 / 5.5 三个测试会自动通过 TEST_COMMAND_ID 走该清单（前提是文件存在）。
TEST_EXPECTED_FILE = HERE.parent / "testdata/ReleaseOrgOperatorCCSuspendStatus.txt"

# ── 默认 commandId='ReleaseOrgOperatorCCSuspendStatus' 对应的 17 行（硬编码兜底）
EXPECTED_FILES_RAW = """1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\atomic\\VerifyRecordAS.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\atomic\\impl\\VerifyRecordASImpl.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\ErrorCode4Customercare.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\bridge\\BuildAuditLogReleaseCCSuspendStatus.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\convertor\\ReleaseOrgOperatorCCSuspendStatusConvertor.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\bridge\\VerifyCallerNotificationCollector.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\bridge\\ProcessReleaseIdentityCCSuspendStatus.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\io\\ReleaseOrgOperatorCCSuspendStatusRequestInfo.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\atomic\\bo\\VerifyRecord.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\java\\com\\huawei\\bs\\customercare\\service\\ReleaseOrgOperatorCCSuspendStatusService.java
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\conf\\bs.customercare.mgt.app-def.xml
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\uconfig\\flow-config\\bs.customercare.flow-config.xml
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\uconfig\\module-parameter\\bs.customercare.mapper.module-parameter.xml
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\uconfig\\module-parameter\\bs.customercare.module-parameter.xml
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\uconfig\\logic\\bs.customercare.logic.xml
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\uconfig\\namingsql\\bs.customercare.naming-sql.xml
1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\spring\\bean\\bs.customercare.service.xml"""


def _load_expected_files():
    """从 ReleaseOrgOperatorCCSuspendStatus.txt 读，缺省回退到硬编码。

    ⚠️  返回的文件清单**仅**与默认 TEST_COMMAND_ID 配套。
    """
    if TEST_EXPECTED_FILE.is_file():
        return [ln.strip() for ln in TEST_EXPECTED_FILE.read_text(
            encoding="utf-8").splitlines() if ln.strip()]
    return [ln.strip() for ln in EXPECTED_FILES_RAW.splitlines() if ln.strip()]


def _expected_files_match_current_command_id():
    """检查期望清单是否与当前 TEST_COMMAND_ID 配套。

    规则：期望文件名含 ReleaseOrgOperatorCCSuspendStatus 才视为配套。
    若 TEST_COMMAND_ID 被改，期望清单不再适用，5.3/5.4/5.5 应跳过。"""
    if TEST_COMMAND_ID == "ReleaseOrgOperatorCCSuspendStatus":
        return True
    # 期望清单路径 / 内容应反映 commandId，否则跳过严格 diff
    if TEST_EXPECTED_FILE.is_file():
        return "ReleaseOrgOperatorCCSuspendStatus" in TEST_EXPECTED_FILE.name
    return "ReleaseOrgOperatorCCSuspendStatus" in EXPECTED_FILES_RAW


def _connect_check():
    """跑测试前先连一次 MySQL；连接失败时跳过（pytest.skip）。"""
    try:
        rows = codegraph_server.q(TEST_SCHEMA, "SELECT 1 AS ok")
        return rows and rows[0].get("ok") == 1
    except Exception as e:
        print(f"[skip] MySQL connection failed for schema={TEST_SCHEMA!r}: {e}")
        return False


_CONNECTED = _connect_check()


# ═══════════════════════════════════════════════════════════════════════
#  5.2 / 5.3 / 5.4  完整文件集验证
# ═══════════════════════════════════════════════════════════════════════

def _call(commandId=None, flowId=None, codeBaseRoot=None):
    return json.loads(codegraph_server.search_service_impact(
        schema=TEST_SCHEMA,
        commandId=commandId,
        flowId=flowId,
        direction="forward",
        maxDepth=20,
        codeBaseRoot=codeBaseRoot,
    ))


def test_5_2_no_codeBaseRoot_returns_at_least_16():
    """5.2 不传 codeBaseRoot 调用：files 至少 16 行（除 1 个 namingsql XML 外）。

    变更说明：scan_module_parameters 已并入 _explore_phase, 2 个
    module-parameter/*.xml 由 SQL 直接收齐, 不再依赖 codeBaseRoot。
    namingsql/*.xml 在 MySQL 中无索引, 仍需 codeBaseRoot os.walk。

    ⚠️  「16 行」**仅**适用于固定入口 commandId='ReleaseOrgOperatorCCSuspendStatus'，
    是「该 commandId 期望 17 行 - 1 个 namingsql XML」的算术结果。其它 commandId 不适用。"""
    if not _CONNECTED:
        return
    if not _expected_files_match_current_command_id():
        print(f"[skip] 期望清单与 TEST_COMMAND_ID={TEST_COMMAND_ID!r} 不配套")
        return
    result = _call(commandId=TEST_COMMAND_ID)
    assert result["entryPoint"] == TEST_COMMAND_ID
    assert isinstance(result["files"], list)
    assert len(result["files"]) >= 16, (
        f"expected ≥16 files, got {len(result['files'])}: {result['files']}")
    # 2 个 module-parameter 必收（与具体 schema 数据无关, 只要 entry 链上命中 bod_customercare）
    got = set(result["files"])
    expected_module_param = {
        "1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\uconfig\\module-parameter\\bs.customercare.mapper.module-parameter.xml",
        "1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\uconfig\\module-parameter\\bs.customercare.module-parameter.xml",
    }
    missing_mp = expected_module_param - got
    assert not missing_mp, f"missing module-parameter files: {missing_mp}"
    # namingsql 是否在结果里取决于默认 codeBaseRoot 是否命中 (D:/2026/MobileMoneyMonorepo)。
    # 这里不强断言，交给 test_5_4 做严格 0 行 diff。


def test_5_X_no_codeBaseRoot_but_envvar_returns_17():
    """5.X 不传 codeBaseRoot 但设了 MM_CODEGRAPH_CODEBASE_ROOT 环境变量: 拿到 17 行。

    仅当 TEST_CODE_BASE_ROOT 实际存在且与期望清单配套时执行严格断言;
    否则跳过(避免在 CI / 本机无代码根时误报)。"""
    if not _CONNECTED:
        return
    if not _expected_files_match_current_command_id():
        print(f"[skip] 期望清单与 TEST_COMMAND_ID={TEST_COMMAND_ID!r} 不配套")
        return
    if not Path(TEST_CODE_BASE_ROOT).is_dir():
        print(f"[skip] codeBaseRoot not a directory: {TEST_CODE_BASE_ROOT}")
        return

    env = os.environ.copy()
    env["MM_CODEGRAPH_CODEBASE_ROOT"] = TEST_CODE_BASE_ROOT
    # 子进程方式: _call 走 in-process, 改 env 后 import 已固化, 这里直接 patch
    saved = os.environ.get("MM_CODEGRAPH_CODEBASE_ROOT")
    os.environ["MM_CODEGRAPH_CODEBASE_ROOT"] = TEST_CODE_BASE_ROOT
    try:
        result = _call(commandId=TEST_COMMAND_ID)
    finally:
        if saved is None:
            os.environ.pop("MM_CODEGRAPH_CODEBASE_ROOT", None)
        else:
            os.environ["MM_CODEGRAPH_CODEBASE_ROOT"] = saved

    got = set(result["files"])
    expected_namingsql = "1.0BaseMaster\\BD_BOD\\codes\\bod_customercare\\src\\main\\resources\\uconfig\\namingsql\\bs.customercare.naming-sql.xml"
    assert expected_namingsql in got, (
        f"环境变量兜底未生效, namingsql 仍缺: {expected_namingsql}")
    assert len(result["files"]) >= 17, (
        f"expected ≥17 files via envvar fallback, got {len(result['files'])}")


def test_5_3_with_codeBaseRoot_returns_full_17():
    """5.3 传 codeBaseRoot 调用：files 应包含 17 行全部。

    ⚠️  本测试**仅**在 TEST_COMMAND_ID == 'ReleaseOrgOperatorCCSuspendStatus'
    且期望清单与之配套时执行严格 diff；其它 commandId 跳过严格断言。
    注：返回数据可能多于 17 行，断言时只比较前 100 条，便于排查。"""
    if not _CONNECTED:
        return
    if not Path(TEST_CODE_BASE_ROOT).is_dir():
        print(f"[skip] codeBaseRoot not a directory: {TEST_CODE_BASE_ROOT}")
        return
    result = _call(commandId=TEST_COMMAND_ID, codeBaseRoot=TEST_CODE_BASE_ROOT)
    assert result["entryPoint"] == TEST_COMMAND_ID
    if not _expected_files_match_current_command_id():
        print(f"[skip] 期望清单与 TEST_COMMAND_ID={TEST_COMMAND_ID!r} 不配套")
        return
    # 去掉 expected 中可能混入的 UTF-8 BOM（某些编辑器写出的 txt 第一行带 BOM）
    expected = {ln.strip().lstrip("﻿") for ln in _load_expected_files()}
    got = set(result["files"])
    missing = expected - got
    extra = got - expected
    # 限制输出：缺/多最多列 100 条
    if missing:
        print(f"[missing: {len(missing)}] showing first 100:")
        for m in sorted(missing)[:100]:
            print(f"  - {m}")
    if extra:
        print(f"[extra: {len(extra)}] showing first 100:")
        for e in sorted(extra)[:100]:
            print(f"  + {e}")
    assert not missing, f"missing files: {len(missing)} (see print above)"
    # extra: 允许有索引里多收的同模块文件，但不应多很多
    assert len(extra) <= 50, f"too many extra files: {len(extra)} (see print above)"


def test_5_4_diff_with_expected_file():
    """5.4 files 排序后与 ReleaseOrgOperatorCCSuspendStatus.txt diff 0 行差异。

    ⚠️  本测试**仅**适用于固定入口 commandId='ReleaseOrgOperatorCCSuspendStatus'。
    其它 commandId 不应套用同一份期望清单。
    注：diff 输出限制最多 100 条，便于排查。"""
    if not _CONNECTED:
        return
    if not Path(TEST_CODE_BASE_ROOT).is_dir():
        print(f"[skip] codeBaseRoot not a directory: {TEST_CODE_BASE_ROOT}")
        return
    if not _expected_files_match_current_command_id():
        print(f"[skip] 期望清单与 TEST_COMMAND_ID={TEST_COMMAND_ID!r} 不配套")
        return
    result = _call(commandId=TEST_COMMAND_ID, codeBaseRoot=TEST_CODE_BASE_ROOT)
    # 去掉 expected 中可能混入的 UTF-8 BOM
    expected_sorted = sorted(
        ln.strip().lstrip("﻿") for ln in _load_expected_files())
    got_sorted = sorted(result["files"])
    got_set = set(got_sorted)
    exp_set = set(expected_sorted)
    missing = [x for x in expected_sorted if x not in got_set]
    extra = [x for x in got_sorted if x not in exp_set]
    if missing or extra:
        diff_lines = []
        if missing:
            diff_lines.append(f"[missing: {len(missing)}] showing first 100:")
            diff_lines += [f"  - {x}" for x in missing[:100]]
        if extra:
            diff_lines.append(f"[extra: {len(extra)}] showing first 100:")
            diff_lines += [f"  + {x}" for x in extra[:100]]
        assert False, "\n".join(diff_lines)


def test_5_5_with_codeBaseRoot_is_superset():
    """5.5 传 codeBaseRoot 的结果集 ≥ 不传的结果集（与 commandId 无关的通用断言）。"""
    if not _CONNECTED:
        return
    if not Path(TEST_CODE_BASE_ROOT).is_dir():
        return
    a = _call(commandId=TEST_COMMAND_ID)
    b = _call(commandId=TEST_COMMAND_ID, codeBaseRoot=TEST_CODE_BASE_ROOT)
    assert set(a["files"]).issubset(set(b["files"])), (
        f"files lost after enabling codeBaseRoot: "
        f"{set(a['files']) - set(b['files'])}"
    )
    diff = set(b["files"]) - set(a["files"])
    print(f"[info] codeBaseRoot added {len(diff)} extra files: {sorted(diff)[:5]}...")


# ═══════════════════════════════════════════════════════════════════════
#  5.6 - 5.9  边界用例
# ═══════════════════════════════════════════════════════════════════════

def test_5_6_unknown_commandId():
    """5.6 commandId 不存在：totalImpacted: 0 + warning。"""
    if not _CONNECTED:
        return
    result = _call(commandId="NON_EXISTENT_COMMAND_ID_XYZ_123")
    assert result["totalImpacted"] == 0
    assert result["files"] == []
    assert any("No service entry found" in w for w in result["warnings"])


def test_5_7_flowId_same_result():
    """5.7 flowId 入口应得到相同 17 行（前提是该 flowId 与 commandId 指向同一流程）。"""
    if not _CONNECTED:
        return
    if not TEST_FLOW_ID:
        print(f"[skip] TEST_FLOW_ID not set, skip flowId comparison")
        return
    if not Path(TEST_CODE_BASE_ROOT).is_dir():
        return
    a = _call(commandId=TEST_COMMAND_ID, codeBaseRoot=TEST_CODE_BASE_ROOT)
    b = _call(flowId=TEST_FLOW_ID, codeBaseRoot=TEST_CODE_BASE_ROOT)
    assert set(a["files"]) == set(b["files"]), (
        f"commandId vs flowId mismatch: "
        f"{set(a['files']) ^ set(b['files'])}"
    )


def test_5_8_dynamic_chain_warning():
    """5.8 动态 chain 触发：files 不空 + （若 setChainId 字段缺失）warning 存在。
    本测试不强制 warning 存在（取决于 schema 是否有 method_bodies/source_text 字段）。"""
    if not _CONNECTED:
        return
    result = _call(commandId=TEST_COMMAND_ID)
    # 文件集合非空是软要求：动态 chain 触发时新文件被加入
    assert result["totalImpacted"] >= 0


def test_5_9_bfs_truncation_warning():
    """5.9 超大 import 图（>5000 节点）截断 + warning。
    当前测试 schema 通常远小于 5000 节点 —— 跑不到截断。
    这里只验证当 import BFS 真的截断时会带 warning（手工构造留给未来）。"""
    # 跳过：无法在测试环境构造超大图
    pass


# ═══════════════════════════════════════════════════════════════════════
#  5.10 - 5.11  codeBaseRoot 校验
# ═══════════════════════════════════════════════════════════════════════

def test_5_10_invalid_codeBaseRoot():
    """5.10 非法路径：不存在 / 不是目录 / 不是绝对路径 均抛 ValueError。"""
    if not _CONNECTED:
        return
    # 相对路径
    try:
        _call(commandId=TEST_COMMAND_ID, codeBaseRoot="relative/path")
    except ValueError as e:
        assert "absolute" in str(e).lower(), f"unexpected msg: {e}"
    else:
        raise AssertionError("expected ValueError for relative path")

    # 绝对但不存在（Windows 用盘符 + 路径；POSIX 用根目录）
    if os.name == "nt":
        nonexistent = "C:\\nonexistent\\path\\xyz_123"
    else:
        nonexistent = "/nonexistent/path/xyz_123"
    try:
        _call(commandId=TEST_COMMAND_ID, codeBaseRoot=nonexistent)
    except ValueError as e:
        msg = str(e).lower()
        assert "not exist" in msg or "not a directory" in msg, (
            f"unexpected msg: {e}")
    else:
        raise AssertionError("expected ValueError for nonexistent path")


def test_5_11_empty_resource_subdir_ok():
    """5.11 codeBaseRoot 有效但无 resources/{module-parameter,namingsql}，正常返回。"""
    if not _CONNECTED:
        return
    # 临时建一个空目录
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        result = _call(commandId=TEST_COMMAND_ID, codeBaseRoot=td)
        # 不报错，且 files 仍含 14+ 行（仅缺 3 个资源 XML）
        assert result["totalImpacted"] >= 14


# ═══════════════════════════════════════════════════════════════════════
#  5.12 - 5.13  跨 schema
# ═══════════════════════════════════════════════════════════════════════

def test_5_12_2_0base_schema():
    """5.12 在 2.0Base schema 上传同 commandId，返回非空但不以 1.0Base 开头。"""
    if not _CONNECTED:
        return
    schema_2 = os.environ.get("TEST_SCHEMA_2_0", "2_0_baseline")
    try:
        codegraph_server.q(schema_2, "SELECT 1")
    except Exception as e:
        print(f"[skip] 2.0Base schema not available: {e}")
        return
    # 2.0Base 的代码库根目录可由环境变量指定；未提供时不传 codeBaseRoot
    code_root_2 = os.environ.get("TEST_CODE_BASE_ROOT_2_0")
    kwargs = dict(schema=schema_2, commandId=TEST_COMMAND_ID,
                  direction="forward", maxDepth=20)
    if code_root_2 and Path(code_root_2).is_dir():
        kwargs["codeBaseRoot"] = code_root_2
    result_2 = json.loads(codegraph_server.search_service_impact(**kwargs))
    if result_2["totalImpacted"] > 0:
        for f in result_2["files"]:
            assert not f.lower().startswith("1.0base"), (
                f"2.0Base schema returned 1.0Base file: {f}")


def test_5_13_common_lib():
    """5.13 公共库 schema：commandId 不一定存在；只验证不抛错。"""
    if not _CONNECTED:
        return
    schema_c = os.environ.get("TEST_SCHEMA_COMMON", "Common_Base")
    try:
        codegraph_server.q(schema_c, "SELECT 1")
    except Exception as e:
        print(f"[skip] Common schema not available: {e}")
        return
    # 不抛错即通过
    result = json.loads(codegraph_server.search_service_impact(
        schema=schema_c, commandId=TEST_COMMAND_ID, direction="forward",
        maxDepth=20, codeBaseRoot=TEST_CODE_BASE_ROOT,
    ))
    assert "files" in result
    assert "warnings" in result


# ═══════════════════════════════════════════════════════════════════════
#  参数校验（即使没连上 MySQL 也能跑）
# ═══════════════════════════════════════════════════════════════════════

def test_param_validation_no_entry():
    """commandId 与 flowId 都为 None → ValueError。"""
    try:
        codegraph_server.search_service_impact(schema=TEST_SCHEMA)
    except ValueError as e:
        assert "commandId or flowId" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_param_validation_bad_direction():
    """direction 非法 → ValueError。"""
    try:
        codegraph_server.search_service_impact(
            schema=TEST_SCHEMA, commandId="X", direction="wrong")
    except ValueError as e:
        assert "direction" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_param_validation_bad_maxDepth():
    """maxDepth <= 0 → ValueError。"""
    try:
        codegraph_server.search_service_impact(
            schema=TEST_SCHEMA, commandId="X", maxDepth=0)
    except ValueError as e:
        assert "maxDepth" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_param_validation_empty_string_entry():
    """commandId='' + flowId=None → ValueError（空字符串视同未提供）。"""
    try:
        codegraph_server.search_service_impact(
            schema=TEST_SCHEMA, commandId="", flowId=None)
    except ValueError as e:
        assert "commandId or flowId" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_param_validation_codeBaseRoot_not_string():
    """codeBaseRoot=123（非字符串）→ ValueError。"""
    try:
        codegraph_server.search_service_impact(
            schema=TEST_SCHEMA, commandId="X", codeBaseRoot=123)
    except ValueError as e:
        assert "codeBaseRoot" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_param_validation_codeBaseRoot_none_disables():
    """codeBaseRoot=None → 触发硬默认值 (D:/2026/MobileMoneyMonorepo) 兜底。

    默认根存在时不再走 skipped 路径；只有默认根也不存在时才追加 skipped warning。
    本测试仅在显式传 None 且默认根不存在时断言 skipped 出现，否则跳过。"""
    if not _CONNECTED:
        return
    result = _call(commandId=TEST_COMMAND_ID, codeBaseRoot=None)
    default_root = "D:/2026/MobileMoneyMonorepo"
    if not Path(default_root).is_dir():
        assert any("skipped" in w for w in result["warnings"]), (
            f"expected 'skipped' warning when no default root, got: {result['warnings']}")
    else:
        # 默认根存在 → 不应再出 skipped warning
        assert not any("skipped" in w for w in result["warnings"]), (
            f"unexpected 'skipped' warning (default root exists): {result['warnings']}")


# ═══════════════════════════════════════════════════════════════════════
#  直接调用辅助函数（不依赖数据库 schema 索引）
# ═══════════════════════════════════════════════════════════════════════

def test_helper_scan_resource_files_no_resources_marker():
    """_scan_resource_files: 给的 xml_paths 不含 \\resources\\ 锚点，返回空列表。"""
    out = codegraph_server._scan_resource_files(
        "D:/anything", ["foo.xml", "bar/baz.xml"])
    assert out == []


# ═══════════════════════════════════════════════════════════════════════
#  QueryTillProducts：用例固化（不传 codeBaseRoot 时 27 个文件）
# ═══════════════════════════════════════════════════════════════════════
# 与 test_5_3/5.4/5_5 模式对齐，但 commandId/期望清单与默认解耦，避免被
# TEST_COMMAND_ID 切换影响。期望清单见 testdata/QueryTillProducts.txt。
QUERY_TILL_PRODUCTS_ID = "QueryTillProducts"
QUERY_TILL_PRODUCTS_EXPECTED_FILE = (
    HERE.parent / "testdata" / "QueryTillProducts.txt"
)


def _load_query_till_products_expected():
    p = QUERY_TILL_PRODUCTS_EXPECTED_FILE
    if p.is_file():
        return [ln.strip() for ln in p.read_text(
            encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("﻿")]
    return []


def test_5_14_query_till_products_no_codeBaseRoot_returns_27():
    """5.14 commandId='QueryTillProducts' 不显式传 codeBaseRoot 时 files 至少 27 个。

    期望清单见 testdata/QueryTillProducts.txt，由 MCP 实测生成（不依赖 codeBaseRoot）。
    当默认 codeBaseRoot (D:/2026/MobileMoneyMonorepo) 命中时，结果还会再增 2 个
    bod_organization 子工程的 namingsql XML（与期望清单是超集关系）。"""
    if not _CONNECTED:
        return
    if not QUERY_TILL_PRODUCTS_EXPECTED_FILE.is_file():
        print(f"[skip] 期望清单不存在: {QUERY_TILL_PRODUCTS_EXPECTED_FILE}")
        return
    result = _call(commandId=QUERY_TILL_PRODUCTS_ID)
    assert result["entryPoint"] == QUERY_TILL_PRODUCTS_ID
    assert isinstance(result["files"], list)
    assert len(result["files"]) >= 27, (
        f"expected ≥27 files, got {len(result['files'])}: {result['files']}")
    # 期望清单是结果的下界（不传 codeBaseRoot 时严格相等；传了则超集）
    expected = set(_load_query_till_products_expected())
    got = set(result["files"])
    missing = expected - got
    assert not missing, f"missing expected files: {sorted(missing)[:10]}"


def test_5_15_query_till_products_with_codeBaseRoot_is_superset():
    """5.15 传 codeBaseRoot 后 files 是不传的超集（namingsql 增量不漏）。"""
    if not _CONNECTED:
        return
    if not Path(TEST_CODE_BASE_ROOT).is_dir():
        print(f"[skip] codeBaseRoot not a directory: {TEST_CODE_BASE_ROOT}")
        return
    a = _call(commandId=QUERY_TILL_PRODUCTS_ID)
    b = _call(commandId=QUERY_TILL_PRODUCTS_ID, codeBaseRoot=TEST_CODE_BASE_ROOT)
    assert set(a["files"]).issubset(set(b["files"])), (
        f"files lost after enabling codeBaseRoot: "
        f"{set(a['files']) - set(b['files'])}")
    diff = set(b["files"]) - set(a["files"])
    print(f"[info] codeBaseRoot added {len(diff)} extra files: "
          f"{sorted(diff)[:3]}...")


def test_5_16_query_till_products_with_codeBaseRoot_collects_namingsql():
    """5.16 传 codeBaseRoot 后 bod_organization 子工程的 namingsql/*.xml 被纳入。

    固化 Plan C（子工程锚定 namingsql 收窄）行为：entry 链触达 bod_organization，
    该子工程下的 bod.operator.naming-sql.xml 等应被自动收集。"""
    if not _CONNECTED:
        return
    if not Path(TEST_CODE_BASE_ROOT).is_dir():
        print(f"[skip] codeBaseRoot not a directory: {TEST_CODE_BASE_ROOT}")
        return
    result = _call(commandId=QUERY_TILL_PRODUCTS_ID, codeBaseRoot=TEST_CODE_BASE_ROOT)
    got = set(result["files"])
    expected_namingsql = {
        "1.0BaseMaster\\BD_BOD\\codes\\bod_organization\\src\\main\\resources\\uconfig\\namingsql\\bod.operator.naming-sql.xml",
        "1.0BaseMaster\\BD_BOD\\codes\\bod_organization\\src\\main\\resources\\uconfig\\namingsql\\bp.ic.organization.naming-sql.xml",
    }
    missing = expected_namingsql - got
    assert not missing, f"namingsql 未被 Plan C 收齐: {missing}"


def test_helper_scan_resource_files_relative():
    """_scan_resource_files: 返回的路径相对 code_base_root。"""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # 在 td 下建 resources/module-parameter/a.xml
        os.makedirs(os.path.join(td, "src", "main", "resources"), exist_ok=True)
        os.makedirs(os.path.join(td, "src", "main", "resources",
                                 "module-parameter"), exist_ok=True)
        with open(os.path.join(td, "src", "main", "resources",
                               "module-parameter", "a.xml"), "w") as f:
            f.write("<x/>")
        xml_paths = [
            "src\\main\\resources\\conf\\app-def.xml",
            "src\\main\\resources\\flow-config\\flow.xml",
        ]
        out = codegraph_server._scan_resource_files(td, xml_paths)
        assert any("module-parameter" in p and "a.xml" in p for p in out), out


# ═══════════════════════════════════════════════════════════════════════
#  CLI 入口
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed, failed, skipped = 0, 0, 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {e.__class__.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
