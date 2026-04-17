# 任务说明（Web Framework TDD Matrix）

你需要根据服务测试需求输入，生成稳定、可程序化校验的 Web 框架 TDD 策略矩阵 CSV。

## 输入
- 输入文件：`workspace/input/service_tdd_requirements.csv`
- 字段顺序固定为：
  - `service_id`
  - `framework`
  - `needs_api`
  - `needs_db`
  - `needs_auth`
  - `needs_external_service`
  - `criticality`
- `framework` 只会出现 `django`、`laravel`、`springboot`。
- `needs_api`、`needs_db`、`needs_auth`、`needs_external_service` 的取值为 `yes` 或 `no`。
- `criticality` 的取值为 `critical`、`high`、`medium`、`low`。

## 输出
- 主输出文件：`/app/workspace/output/web_framework_tdd_matrix.csv`
- 输出字段必须且仅能按以下顺序出现：
  - `service_id`
  - `framework`
  - `unit_strategy`
  - `api_strategy`
  - `persistence_strategy`
  - `isolation_strategy`
  - `coverage_gate`

## 处理规则
1. 每条输入记录必须生成一条输出记录，不允许丢行。
2. 输出按 `service_id` 升序排序。
3. `framework` 原样带入输出。
4. `unit_strategy` 必须体现框架专属 TDD 模式：
   - `django` 使用 `pytest-django` 与 `factory_boy`
   - `laravel` 使用 `PHPUnit` 或 `Pest` 与 factories
   - `springboot` 使用 `JUnit5` 与 `Mockito`
5. `api_strategy` 必须体现框架专属 API 测试模式：
   - `django` 使用 DRF 测试方式
   - `laravel` 使用 HTTP 测试；若需要认证则体现 Sanctum 风格认证测试
   - `springboot` 使用 `MockMvc`；若需要认证则体现 security request post-processors
6. `persistence_strategy` 必须体现框架专属持久化测试模式：
   - `django` 使用 `pytest-django` 数据库测试
   - `laravel` 使用 factories、`RefreshDatabase` 或 database fakes
   - `springboot` 使用 `DataJpaTest` 与 `Testcontainers`，或在无数据库需求时使用仓储 mock
7. `isolation_strategy` 必须根据是否依赖外部服务选择稳定的隔离方案：
   - 有外部服务依赖时，使用框架常见 fake、stub 或 mock 边界方案
   - 无外部服务依赖时，使用框架内常见依赖隔离方式
8. `coverage_gate` 仅由 `criticality` 决定：
   - `critical` -> `line>=95%;branch>=90%`
   - `high` -> `line>=90%;branch>=85%`
   - `medium` -> `line>=85%;branch>=75%`
   - `low` -> `line>=80%;branch>=70%`
9. 禁止输出额外列，禁止改变列名、列顺序或主输出路径。
10. 禁止输出空值、`null`、`None`、`nan`、`n/a` 等空指示字符串。

## 禁止事项
- 不允许修改输入文件。
- 不允许引入联网、随机数或主观打分逻辑。
- 不允许生成替代主结果文件来绕过 `web_framework_tdd_matrix.csv`。
