# R6 close-boundary rejection — cloud review

日期：2026-09-16

Identity：`R6_close_boundary_rejection_v1`

## 1. Execution integrity

R6 的 preanalysis / protocol / runner / tests / execution freeze 均在任何 real-data R6 outcome 可见前冻结。

受控执行：GitHub Actions run `35041067183`，head `d8dccf3738169686076d11420deccfbdad316de3`，job `104620817694`，conclusion=`success`。

- frozen tests：4/4 passed；
- frozen artifact blob identities：passed；
- source SHA256=`bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`；
- rows=70,114；symbol=`000852.SH`；max day=`2020-12-31`；
- structure cache read=false；B1 feature read=false；
- BLACKBOX=false；post-2020=false；PnL=false；fresh-OOS claim=false；production authority=false。

Artifact id=`10424898798`，digest=`sha256:4acf96c01f0bba12f44f226fdb615942290427ac3296086165a99ef83ab32334`。

## 2. Supply gate 通过

总 event count=`7,384`。

TRAIN：failed=`1,054`，control=`3,694`。

VALIDATION：failed=`584`，control=`2,052`。

2019：failed=`290`，control=`1,060`；2020：failed=`294`，control=`992`。

VALIDATION upper：failed=`283`，control=`1,073`；lower：failed=`301`，control=`979`。

因此 `supply_supported=true`。

## 3. Direction evidence

TRAIN pooled：mean effect=`-0.0462789`，reversal-fraction delta=`+0.0189317`。

VALIDATION pooled：mean effect=`-0.0364475`，reversal-fraction delta=`+0.0441634`。

2019 mean effect=`-0.0310399`；2020=`-0.0383044`。

VALIDATION upper breakout：mean effect=`-0.1244371`，符合 failed breakout 后反转更强的预注册方向。

但 VALIDATION lower breakout：

- failed mean=`+0.0207698`；
- control mean=`-0.0371780`；
- mean effect=`+0.0579478`，与冻结要求 `<0` 相反；
- reversal-fraction delta 虽为 `+0.0323505`，但不能覆盖主 mean-effect gate 失败。

因此 `direction_supported=false`。

## 4. Formal adjudication

`R6_direction_not_supported`

这说明 close-only failed-breakout identity 在 pooled / year-level 和 upper-breakout 上有反转形状，但上下方向不具有冻结定义要求的对称机制支持。

不得 outcome 后只保留 upper breakout、改变 12-bar boundary、改变 1-bar rejection、改变 3-bar horizon、重新定义 control、筛时段/年份，或增加其它特征来把同一 identity 改判为通过。

Program-level consequence：`R6_closed_direction_asymmetry_no_rescue`。

## 5. Authority

- bounded diagnostic：false；
- specialist handoff：false；
- BLACKBOX：false；
- HMM/rSLDS/Koopman 或其它 complex rescue：false；
- PnL/Sharpe/economic mapping：false；
- paper trading / production / Layer 4：false。

下一步回到 broad discovery，优先研究与 R5-B1 和 R6 均独立、且能区分 market-common shock 与 idiosyncratic shock 的跨指数机制；在冻结新科学 identity 前先做纯数据资产 inventory。
