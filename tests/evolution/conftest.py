import os

# 演化层测试默认品类 tourism（与 tests/tourism 一致）；需 gift-box 的用例用 monkeypatch.setenv 切换
# （active_profile 运行时读 env，可动态切）。
os.environ.setdefault("GEO_CATEGORY", "tourism")
