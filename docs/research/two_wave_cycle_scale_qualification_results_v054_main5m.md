# v0.5.4 完整周期尺度资格：主 5m 机制审计

日期：2026-09-06  
状态：`main5m_mechanism_pass_expand_to_multiview`

## 1. 结果前假说

冻结 v0.5.2 exact-ridge parent identity 与 v0.4.3 全部 qualification 数值阈值，仅把：

`corresponding_leg_duration_mismatch`

从 same-scale hard gate 降为 morphology diagnostic。

完整周期的 duration ratio `<=2.0` 仍是 hard gate；short / long cycle、pair、amplitude、raw ER=0.5、jump=0.5、flat、clock、confirmation、D1、ledger 全部不变。

## 2. 正式主 5m 证据

- workflow run：`33984455043` — success
- commit：`17108111ec9d5e6066f9f8718bcfebf4059b1c36`
- artifact：`9974744445`
- artifact SHA256：`217348e93d47a3364a4c3496e2752743923bba7cf6626c3dcf15e92078c95469`
- package validation / full regression / single-component invariants：全部通过

后续 commit `030ca624...` 只给同一 workflow 加了触发注释，不改变任何研究代码；因此 run #1 是有效正式证据。

## 3. 单组件归因完全成立

`5m_offset_0`：

- evaluated：38,049
- parent candidate identity exact match：**true**
- v0.5.2 qualified：425
- v0.5.4 qualified：734
- newly qualified：**309**
- lost qualified：**0**
- newly qualified 集合与事前 attribution 的 `corresponding_leg_duration_mismatch` exclusive-only 集合：**完全一致**

因此结果没有混入 representation、其它 qualification rule 或 ledger 漂移。

734 / 404 的 qualified / selected 数量只作描述，不作为晋级理由。

## 4. 新释放 309 个结构的机制特征

完整周期时长比：

- median 1.50
- p90 1.917
- max 2.0

即全部仍满足冻结的 full-cycle same-scale hard gate。

对应半浪最大时长比：

- min 2.059
- median 2.75
- p90 4.15
- max 7.25

raw min-leg ER：

- min 0.5002
- median 0.5781

max jump share：

- median 0.4012
- p90 0.4772
- max 0.4978

所以这些不是通过同步放松 ER/jump 获得的对象；它们只违反“对应半浪必须近似同长”。

## 5. 固定窗口

### 2018-06-20

原 v0.5.2 的 24/29 父结构完整保留：

- v052 qualified = 1
- v054 qualified = 1
- 新释放 = 0

没有出现 v0.5.3 那种把已通过父结构反向杀掉的问题。

### 2019-04-15

释放事前 attribution 指定的唯一 duration-only near-pass：

- raw points `[49927,49934,49943,49961,49967]`
- cycles `16/24`
- legs `7/9/18/6`
- full-cycle ratio `1.5`
- corresponding-leg max ratio `2.571`
- raw min ER `0.563`
- max jump `0.357`
- D1 `uncertain`

### 2020-07-15

释放事前 attribution 指定的唯一 duration-only near-pass：

- raw points `[64511,64517,64532,64543,64549]`
- cycles `21/17`
- legs `6/15/11/6`
- full-cycle ratio `1.235`
- corresponding-leg max ratio `2.5`
- raw min ER `0.662`
- max jump `0.443`
- D1 `uncertain`

## 6. case_02 安全门

legacy case_02 的已知坏结构是：

- raw `[4565,4617,4655,4656,4658]`
- cycles `90/3`
- legs `52/38/1/2`

它没有被 v0.5.4 复活。

v0.5.4 在宽松 overlap audit 中显示的唯一新增对象实际上是：

- raw `[4658,4667,4672,4688,4699]`
- cycles `14/27`
- legs `9/5/16/11`
- full-cycle ratio `1.929`
- corresponding-leg max ratio `2.2`
- raw min ER `0.563`
- max jump `0.422`
- pair duration 41

它的**第一个** raw extremum 才等于 legacy case_02 的**最后一个** raw extremum `4658`；主体在 legacy case 之后。两者不是同一结构，也不是 90/3 / 1-bar-leg pathology。

因此 case_02 安全门通过。

## 7. 其它 legacy case

- case_00：v052 qualified=0，v054 qualified=0；没有声称解决 case_00。
- case_11：5 -> 12 qualified，新增7个全部来自事前 frozen duration-only 集合；旧跨周巨型 legacy 结构仍受 long-cycle/pair/session/calendar 等 hard rules 限制。
- case_14：9 -> 16 qualified，新增7个全部来自 duration-only 集合；旧 379/606 巨型 legacy 结构未因本实验获得资格。

## 8. 主 5m 判定

**通过主 5m 机制门，扩展至正式 multiview causal/stability adjudication。**

通过的不是“候选更多”，而是：

1. candidate identity 完全冻结；
2. 新增集合严格等于事前锁定的单一 rejection 集合；
3. full-cycle scale hard gate 完整保留；
4. 2018 已通过结构不丢失；
5. case_02 的 90/3 假结构不复活；
6. 没有联动放松 jump / ER / short / amplitude。

下一步按冻结 protocol：五个 native 5m + 1m official，18 次 prefix zero-rewrite，native-5m offset IoU 与 case safety audit。未完成该门前，v0.5.4 不升格为 baseline；操作 baseline 仍为 v0.4.3。
