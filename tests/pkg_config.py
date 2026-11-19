"""本包自检参数（与 smoke_test.py / test_schema_lib.py 配套）。

通用包没有固定业务表，自检跑在 references/demo-schema.yaml 上；
替换为真实应用语义包时，同步改这里的三项并刷新 scripts.lock。
"""

APP_CODE = "00.GENERIC.DEMO"
CATEGORY = "03-DataAnalysis"
SCHEMA_SKILL = "timus-app-schema"
SCHEMA_FILE = "demo-schema.yaml"
REQUIRED_TABLES = ["客户", "订单"]
FORM_SKILLS = ["record-create-form"]
MAINTENANCE_SKILL = "record-maintenance"
