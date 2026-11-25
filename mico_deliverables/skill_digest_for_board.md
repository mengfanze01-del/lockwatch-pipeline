# 看板能力增强：从周报 Skill 提取的可用口径（交接给 Claude）

来源：skill `device-lock-installment-weekly-report`（ID `c0fc1dab-9648-46a8-a50b-bca8a8891285`）。以下是其中**对看板抓取/入库能力有直接增益**的部分，已剔除纯写作 SOP（模板、期号管理、飞书交付四件套——那些与看板无关）。请把下面内容加进 `lockwatch-pipeline` 的现有能力（`configs/keywords.yaml`、抓取口径、入库规则）。

---

## 1. 检索关键词模板（净增量）

现有 `configs/keywords.yaml` 是 6 品牌矩阵。skill 3.1 节提供两类净增量：

### 1.1 行业玩家词（补品牌矩阵覆盖不到的玩家面）

```
# 玩家/生态
PayJoy, Trustonic, M-KOPA, Watu, Sun King, Cashea
Samsung Finance+, Galaxy Forever, Knox Guard, KG Lock, Samsung Knox financing, Galaxy Upgrade Program, Samsung Finance Lock
device financing, device locking, phone lock installment
Transsion / 德信 Easybuy / Palmcredit
# 车辆/电动车线
vehicle financing immobilizer, car finance remote lock, EV installment
car finance immobilizer Europe, auto leasing remote lock Russia
车辆金融 中东, 汽车分期 东欧, 车企金融 东南亚, EV financing South Asia
Telimob, Navionyx, Ecocosmo GPS, Technauto FMC920, 智信通, Navixy
UAE 车辆监控, telematics box, 极氪 海外锁车, 蔚来金融
```

### 1.2 社媒/短视频解锁黑产巡检词（看板 08 栏与灰产监控缺的面，skill 要求每期必扫）

```
phone unlock service
mkopa unlock
m-kopa d-light sunking watu unlock
payjoy phone unlock
手机解锁 广告
unlock service (facebook | youtube)
Knox Guard bypass
```

命中按**威胁情报条目**处理：记录 平台 / 日期 / 覆盖品牌 / 报价（**联系方式脱敏**），归入看板 08 三星专档或灰产监控。

### 1.3 监管/市场/技术补充词

```
# 监管
RBI device locking rules, OJK BNPL PADK, CBK non-deposit taking credit providers
CEIR IMEI Nigeria, BNPL regulation Thailand
# 市场
Africa smartphone shipments Omdia, India EMI penetration Counterpoint
smartphone ASP memory price, smartphone affordability emerging markets
# 技术
TEE Kinibi, Samsung Knox device financing, Google DLC, PAYGO solar
```

### 1.4 时效过滤

只取覆盖窗口内的信息（搜索加时间过滤）；窗口外确需引用时注明日期并标「窗口外」，不与窗口内新闻混排。

---

## 2. 信源分级（抓取优先采信顺序）

1. **一手来源**：公司 Newsroom / 官方博客（PayJoy Newsroom、Samsung Newsroom India、Trustonic Blog、M-KOPA、传音公告）、监管机构官网（RBI、OJK、CBK、CBN、NCC）。
2. **权威研究机构 / 垂媒**：IDC、Omdia、Counterpoint、GSMA、Strategy Analytics；TechCabal、Tech-ish、WeeTracker、Business Matters、BW Businessworld、Economic Times。
3. 知名财经媒体。

规则：同一事件优先取一手来源；无一手来源时标明媒体名。**关键结论和数据必须附来源链接**（对应看板条目的 `source` + `url` 字段必填逻辑）。

---

## 3. 去重与交叉验证（入库规则）

- 同一事件只保留一条，合并信息点（跨天/跨源重复报道去重）。
- 关键数字（出货量、均价、分期渗透率、放款额、监管阈值、罚款金额）**必须跨来源交叉核对**。
- 来源冲突时以官方/一手公告为准；无法确认时标注「据报 / 待确认」。

---

## 4. 筛选与分级（入库门槛）

- **每条必须给数字**：金额、比例、时间点、覆盖量；缺数字的动态降级或合并。
- **"无动态"如实写**：某玩家/某市场窗口内确无公开信息，直接写「无新增动态」占位，**不做推测性补全**。
- **区分新增与背景延续**：历史数据、旧事件延续标注「背景延续 / 背景数据」，不与新增新闻混排。
- **排除面**（skill 2.3）：与设备分期无关的泛科技/宏观新闻；无业务含义的纯融资快讯（锁机赛道玩家除外）；无法验证来源的内容（内容农场、无出处爆料）。

---

## 5. 地理与主题权重（抓取源优先级）

- 地理权重：非洲（肯尼亚/尼日利亚）> 南亚（印度）> 东南亚（印尼/泰国/菲律宾/越南）> 拉美（巴西/墨西哥/委内瑞拉/哥伦比亚）> 北非（摩洛哥）> 中国（政策外溢）。**小米海外重点市场（印度、东南亚、拉美、非洲）单独加权。**
- 电动车条线区域全覆盖：非洲、东南亚、欧洲、中东、东欧、俄罗斯、东亚、南亚；跟踪所有车企（OEM）、汽车金融公司/银行/租赁方、合作三方技术公司（远程锁/GPS/immobilizer/车联网风控平台）。
- 重点监控对象（三星 KG 锁为全球被破解最多的融资锁）：对应看板 08 栏需保持高优先级，含破解生态威胁情报条目。

---

## 6. 与看板 8 栏的映射建议

| skill 主线 | 看板栏目 |
|---|---|
| 玩家动态（非品牌专属） | 01 今日信息流 |
| 泰国相关（BOT/AIS/True/电商泰站） | 02 今日泰国锁机 |
| 小米/天星相关 | 03 小米锁机 |
| 监管与合规 | 04 监管与合规 |
| 区域市场/数据 | 05 区域市场 |
| 技术与产品（TEE/DLC/解锁攻防） | 06 技术与产品 |
| 三星/Knox/KG Lock + 解锁黑产 | 08 三星专档 |
| 车辆/电动车锁机 | 09 电动车锁机条线 |

注：skill 是周报口径（四主线 + 业务启示），看板是 8 栏日度舆情——**按上表映射，不要照搬周报章节结构**。

---

## 7. 不适用部分（明确不加）

- 写作模板（六章结构、期号管理、5 条核心要点限制、6000-12000 字符篇幅）——周报交付格式，看板不需要。
- 飞书交付四件套（本地 md + 云文档 + wiki 登记 + DM）——看板有自己的 commit/push/Pages 链路。
- 「对小米/天星数科的启示」必写项——看板是信息流，不强制观点输出。
