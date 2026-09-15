# PHASE-04：A 方案——数据集 + 代理模型 + 约束 BO（W6–W9）

## 1. 阶段目标

攒出双机 `D_safe`（每机 2000–4000 条），自训监督代理模型
`f(s,a)→(perf,power,temp)`（LightGBM baseline / MLP 主模型 / 5-Ensemble 不确定度），
上线安全约束 BO，在**回放 + 小步真实**下验证相对 B2 基线 Return +10% 且 shield 不上升。
交付预测器 ONNX v1。对应 V10–V15。

## 2. 前置依赖

- PHASE-03（采集器 + dry-run + BlackBox）；E1 门禁已过（V09+ 可排期）
- 真实下发规则：小步（ΔPL≤5W/Δfreq≤100MHz/UV 步进≤5mV），G4/burst/UV 加深禁入（等 E5）

## 3. 详细步骤

### Step 4-1：采集规程冻结（2 天）
1. 场景覆盖配额：游戏≥2h / 办公≥2h / idle≥1h / 至少 1 次插拔电（影子门禁 §5.2 同口径）。
2. 前台交互探针样本强制混入（任务管理器冷/热启动、Alt-Tab、右键），占比≥15%（防跑分高分体验卡）。
3. 每条样本：`(State48, Action7, 30s 后 perf/power/temp)` + 三版本号 + fluency_violation 标记。
4. A 机先行，B 机按 P1-3 抽样比同步。

### Step 4-2：BO 在线搜参 + 攒数（1.5 周，与 4-3 并行）
1. GP（单机）/TPE（高维），采集函数 Constrained-EI，SafeOpt 初始化 10 点（安全档附近）。
2. 超 `μ+2σ>温度墙` 的点不试；shield 触发步记 `SHIELD_PENALTY −1.0`。
3. 每日归档 `D_safe`，监控覆盖度（8 子模 W0–W7 × AC/DC 九宫格填充率）。

### Step 4-3：代理模型训练与对比（1.5 周）
1. 划分：按时间 7:1:2 + 整机留一做跨机 test；机型独立 z-score。
2. 三模型对比：LightGBM（可解释+特征重要性图）/ MLP 64-64-32+LN（主）/ 5-Ensemble（方差=BO 约束概率）。
3. Loss：`MSE + 0.2·RankLoss + 物理单调性惩罚`；AdamW 3e-4 / batch256 / early-stop patience20。
4. 指标：RMSE/MAE（分 perf/power/temp 三头）、校准曲线、Pareto 排序 Kendall τ。
5. 导出 ONNX（<10MB，CPU 推理<5ms）；CUDA EP 缺失记缺失声明，不阻塞。

### Step 4-4：回放验证 V10–V15（3 天）
1. V10–V12：B0–B2 log 离线重算 reward，可计算率 100%，B2 分布存档为“不退化”锚点。
2. V13–V15：包络符合性观测 + B2 四档实测（小步真实，G4 除外）：违例=0，地板保持率≥SLO。
3. 回合计分 `Return = mean−0.5std−2shield−1clamp`：相对 B2 **+10% 且 shield_rate 不上升**。

## 4. 阶段验收方法

- [ ] `D_safe` 规模达标（A 机≥2000，B 机按抽样比），九宫格覆盖率≥80%，交互探针≥15%
- [ ] 三模型对比表齐：MLP/Ensemble 在 power RMSE 与 τ 上显著优于 LightGBM（或如实记录反例）
- [ ] 回放 Return +10% 达标且 shield 不上升（V10–V15 产物归档）
- [ ] 预测器 ONNX v1 导出 + 推理延迟实测（<5ms CPU）记录
- [ ] 验收：打 `tag phase-04-done`；D_safe 冻结为 P6 的 Replay Buffer（只读快照）

## 5. 产物清单

`D_safe` 快照（版本化）/ 训练代码 + 超参表 / 三模型对比报告 / ONNX v1 /
V10–V15 产物（reward_replay/reward_baseline/envelope_B2.csv 等）

## 6. 风险与回退

- 数据多样性不足 → BO 早熟收敛：监控九宫格覆盖率，缺格定向补采，不凑数。
- 小步真实触发 shield 上升：立即降回影子，查阈值/动作步长，不硬闯。
- 回滚：模型版本化，任一版本可回退上一 ONNX；数据只追加不覆盖。
