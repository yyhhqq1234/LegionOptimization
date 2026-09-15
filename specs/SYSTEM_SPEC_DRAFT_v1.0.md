# 系统规格锁定 v1.0（t1 / p-spec，P0 已验收）

> 性质：规格内容，不写代码。只读基于已锁定讨论（现网 4 档静态胶水层 + 只读分析 t1–t5 结论）。
> 现网基线：Y7000 2025 IAX10 / U7 255HX / RTX 5060；Quiet 3.8GHz/-50mV/25W，
> Balance 4.8GHz/-65mV/40W，Beast 5.0GHz/-55mV/65W，Extreme 5.2GHz/-45mV/65W；
> FIVR fire-and-forget 五步；Fn+Q 双触发链；Boot 双轨；Extreme 双触发竞态等 13+10 项 findings 为本规格输入。
> P0-1已应用：负载子模 m0–m7 改称 **W0–W7**（workload），系统模块保留 M1–M8；P0-2已应用：G0–G4 为唯一档维度，DC 为正交维度（与 AC 同优先级）。E1 已验收，见 `plans/PHASE-00-e0e1-review.md`。

---

## 1. 设计锁定（5 条）

| # | 锁定项 | 内容 |
|---|--------|------|
| L1 | 档位语义 | Fn+Q 物理 4 档 + 1 虚拟档 = **5 档包络**。档位只定**上限包络**（频墙/PL/UV/温度天花板），不直接定执行值。RL 输出被钳位在当前档包络内 |
| L2 | 动作连续化 | 现网 4 套静态 INI → **Action7 连续动作**，经 HAL 换算为 powercfg + TS FIVR/PL/SST/EPP 参数。档内可微调，不再“一刀切” |
| L3 | 状态统一 | 所有策略输入必须走 **State48 统一向量**（§3），任何新增信号先落表再接入，禁止旁路私有采样 |
| L4 | 安全优先 | Reward 只做软引导，**温度 shield / 流畅 shield / 拔电回退 / Burst 预算**做硬截断（详见 t4，本草案只定义接口与触发阈值） |
| L5 | 双触发收敛 | Extreme 双触发（LLT pipeline + Watcher mode=224 并发跑 custom.bat）必须收敛为**单一仲裁入口**：WMI 事件只写“期望档位”，执行权唯一归 HAL 执行器（含互斥锁） |

非目标：不碰 GPU 切模自动化（仍 NVIDIA App 手动，HAL 只读）；不改 LLT 源码（官方版）；不做跨机型自适应（只 Y7000 2025，移植另行标定）。

---

## 2. HAL 分层（5 层 + 2 侧车）

```
┌─────────────────────────────────────────────────┐
│ L4 策略层 Policy（RL Controller + 8子模路由器）    │  输入 State48 → 输出 Action7(期望值)
├─────────────────────────────────────────────────┤
│ L3 围栏层 Guard（温度shield/流畅shield/Burst桶）   │  硬截断 Action7 → Action7'（可审计否决）
├─────────────────────────────────────────────────┤
│ L2 执行层 Actuation（互斥 + 五步序列化 + 回滚）    │  唯一执行权；kill→copy INI→powercfg→TS注入→kill
├─────────────────────────────────────────────────┤
│ L1 抽象层 Abstraction（参数换算：逻辑→物理）       │  频墙→SST/NonTurbo；UV mV→FIVR编码；PL W→EAX/EDX
├─────────────────────────────────────────────────┤
│ L0 传感/事件层 Sense（WMI事件 + 采样器）           │  只读；WMI档位事件 + 1Hz状态采样 + 功耗/帧率探针
└─────────────────────────────────────────────────┘
   侧车 S1：Shadow/Canary（影子执行→只记日志不落盘；金丝雀→单档灰度）
   侧车 S2：BlackBox（switch_log.txt 结构化继任：决策/否决/回退全记录，可轮转）
```

### 2.1 各层职责与接口

| 层 | 输入 | 输出 | 关键约束 |
|----|------|------|----------|
| L0 Sense | WMI 事件（SMART_FAN / THERMAL mode=224/1/2/3/255）、NVML、powercfg 读回、MSR 读回（只读）、前台进程/帧率探针 | `DesiredGear[0..4]` 事件；`State48` @1Hz | 采样失败必须打 `valid=0` 而非填旧值；WMI 事件只做“期望档位”写入，不直接触发 .bat |
| L1 Abstraction | Action7 逻辑值 | powercfg 参数 / TS INI 全量字段 / LLT 期望档位 | 换算表版本化（`HAL_MAP v0.1`）；UV 编码沿用现网公式 `enc = mV×1.024 → hex`；SST/NonTurbo 与频墙严格对齐（现网 slot 对应关系保留） |
| L2 Actuation | Action7 物理参数包 | 落盘结果 + 回滚快照 | **全局互斥**（解决 mode 切换竞态 P2 / 开机竞态 R2 / Extreme 双跑 R5）：同一时刻只允许一个 actuation 事务；事务超时 15s 自动回滚到上一快照；所有返回值必校验（解决 P3 虚假成功日志） |
| L3 Guard | Action7 期望值 + State48 | Action7'（截断后）+ 否决原因码 | 否决码枚举：`TEMP_SHIELD / SMOOTH_SHIELD / BURST_EMPTY / AC_LOST / MANUAL_PIN`；否决必须可审计（记 BlackBox） |
| L4 Policy | State48 | Action7 期望值 + 子模 id[0..7] | 决策周期 1s；输出超包络时由 L3 钳位并记 `CLAMPED`；禁止直写硬件 |

### 2.2 权限分离（沿用并加固现网 Boot 双轨）

- 用户态：L0 采样 + L4 推理 + S1/S2（Run 键启动，Session ≥1，可见可调试）。
- SYSTEM 态：仅 L2 落盘事务中的提权动作（经 `ThrottleStop_NoUAC` 式受限入口；安装包/脚本签名校验见 t4）。
- 跨账户写 HKCU Run 键的 P1 缺陷：HAL 安装器必须以**交互用户上下文**写 Run 键，SYSTEM 任务禁止写 HKCU。

---

## 3. State48 字段表（8 组 × 6 维 = 48）

采样周期 1s；归一化到策略输入时按 `Norm` 列处理；`Src` 为 L0 传感来源。

### G0 档位与电源上下文（s0–s5）

| # | 字段 | 单位/枚举 | 范围 | Src | Norm |
|---|------|-----------|------|-----|------|
| s0 | gear_desired（期望档位） | 枚举 0–4 | 0–4 | WMI 事件保持 | one-hot/5（另行展开，不占本表外维度；此处存标量） |
| s1 | gear_active（当前生效包络） | 枚举 0–4 | 0–4 | L2 回读 | /4 |
| s2 | ac_online（是否插电） | bool | 0/1 | OS 电源 | 原值 |
| s3 | battery_pct | % | 0–100 | OS 电池 | /100 |
| s4 | power_plan（当前计划） | 枚举 Balanced/HighPerf/Ultimate | 0–2 | powercfg 读回 | one-hot（策略侧展开） |
| s5 | manual_pin（用户手动钉住档位） | bool | 0/1 | 看门狗/UI | 原值 |

### G1 CPU 负载与频率（s6–s11）

| # | 字段 | 单位 | 范围 | Src | Norm |
|---|------|------|------|-----|------|
| s6 | cpu_util_total | % | 0–100 | OS 计数器 | /100 |
| s7 | cpu_util_pcore | % | 0–100 | OS 计数器 | /100 |
| s8 | cpu_util_ecore | % | 0–100 | OS 计数器 | /100 |
| s9 | cpu_freq_avg | MHz | 0–5200 | MSR/计数器读回 | /5200 |
| s10 | cpu_freq_max_1s | MHz | 0–5200 | 采样峰值 | /5200 |
| s11 | cpu_c0_residency | % | 0–100 | 计数器 | /100 |

### G2 GPU 状态（s12–s17，只读不控）

| # | 字段 | 单位 | 范围 | Src | Norm |
|---|------|------|------|-----|------|
| s12 | gpu_util | % | 0–100 | NVML | /100 |
| s13 | gpu_freq | MHz | 0–2600 | NVML | /2600 |
| s14 | gpu_power | W | 0–140 | NVML | /140 |
| s15 | gpu_temp | °C | 0–100 | NVML | /100 |
| s16 | gpu_mode（iGPU/Hybrid/dGPU） | 枚举 | 0–2 | NV App/驱动读回 | one-hot（策略侧） |
| s17 | mux_fg_app（前台是否为全屏独占） | bool | 0/1 | 前台窗口探针 | 原值 |

### G3 温度与功耗（s18–s23）

| # | 字段 | 单位 | 范围 | Src | Norm |
|---|------|------|------|-----|------|
| s18 | cpu_temp_pkg | °C | 0–105 | DTS/MSR | /105 |
| s19 | cpu_temp_max_core | °C | 0–105 | DTS | /105 |
| s20 | temp_headroom（距档位天花板余量） | K | -20–+40 | 计算值 | clip/40 |
| s21 | pkg_power | W | 0–120 | MSR/RAPL | /120 |
| s22 | pl1_limit_active | W | 0–120 | MSR 读回 | /120 |
| s23 | fan_rpm_norm（或档位代理） | 归一化 | 0–1 | EC（如不可读则用档位代理+valid=0） | 原值 + valid 位（s47 联动） |

### G4 流畅与前台负载（s24–s29）

| # | 字段 | 单位 | 范围 | Src | Norm |
|---|------|------|------|-----|------|
| s24 | fg_fps（前台帧率，无前台则 0） | fps | 0–360 | 帧率探针 | /120 clip |
| s25 | fps_p1_low（1% Low） | fps | 0–360 | 帧率探针 | /120 clip |
| s26 | stutter_events_10s（卡顿计数） | 次 | 0–50 | 探针 | /10 clip |
| s27 | fg_class（前台类型：桌面/办公/游戏/渲染） | 枚举 | 0–3 | 进程分类器 | one-hot（策略侧） |
| s28 | io_wait_pct | % | 0–100 | OS 计数器 | /100 |
| s29 | mem_pressure | % | 0–100 | OS 计数器 | /100 |

### G5 档位包络与预算（s30–s35）

| # | 字段 | 单位 | 范围 | Src | Norm |
|---|------|------|------|-----|------|
| s30 | gear_freq_cap（当前包络频墙） | MHz | 2800–5200 | L2 回读 | /5200 |
| s31 | gear_pl1_cap | W | 15–65 | L2 回读 | /65 |
| s32 | gear_temp_ceiling | °C | 75–98 | 包络表（§5） | /100 |
| s33 | burst_tokens（剩余 burst 预算） | s·W 归一化 | 0–1 | L3 Burst 桶 | 原值 |
| s34 | shield_active（任一 shield 生效中） | bool | 0/1 | L3 | 原值 |
| s35 | time_in_gear | s | 0–3600 | L2 计时 | log1p/8 |

### G6 时间与历史（s36–s41）

| # | 字段 | 单位 | 范围 | Src | Norm |
|---|------|------|------|-----|------|
| s36 | tod_hour_sin / tod_hour_cos | — | -1–1 | 时钟 | 原值（占 s36, s37 两维） |
| s38 | ac_lost_60s（60s 内掉电事件） | bool | 0/1 | L0 事件 | 原值 |
| s39 | last_action_clamped | bool | 0/1 | L3 | 原值 |
| s40 | switches_10min（档位切换次数） | 次 | 0–20 | L2 计数 | /10 clip |
| s41 | boot_phase（开机 5min 内） | bool | 0/1 | 计时 | 原值 |

> s36 占两维（sin/cos），故本组为 s36–s41 共 6 维。

### G7 有效性与子模（s42–s47）

| # | 字段 | 单位 | 范围 | Src | Norm |
|---|------|------|------|-----|------|
| s42 | submode_id（8 子模当前判定） | 枚举 0–7 | 0–7 | L4 路由器 | /7（+ one-hot 展开供 reward 分档） |
| s43 | submode_conf | 0–1 | 0–1 | 路由器置信度 | 原值 |
| s44 | sensor_valid_mask_cpu | bitmask | 0–63 | L0 自检 | 原值 |
| s45 | sensor_valid_mask_gpu | bitmask | 0–63 | L0 自检 | 原值 |
| s46 | ts_inject_ok（上次 FIVR 注入成功） | bool | 0/1 | L2 事务回执（根治 R3 静默失败） | 原值 |
| s47 | sample_flags（降采样/补值标记） | bitmask | 0–255 | L0 | 原值 |

维度核算：G0 6 + G1 6 + G2 6 + G3 6 + G4 6 + G5 6 + G6 6 + G7 6 = **48** ✓

---

## 4. Action7 字段表

策略输出为逻辑值，经 L1 换算为物理参数；L3 可截断；L2 唯一落盘。

| # | 动作 | 逻辑范围 | 物理映射（HAL_MAP v0.1） | 执行体 | 缺省/步长 |
|---|------|----------|--------------------------|--------|-----------|
| a0 | max_freq（频墙） | 2800–5200 MHz | powercfg `PROCFREQMAX` AC+DC + SST Max/NonTurbo（沿用现网 slot 对齐：38/48/50/52×100MHz） | powercfg + TS INI | 步长 100MHz |
| a1 | turbo_policy（EPP/模式） | 连续 0–1 → {Aggressive,Efficient} | 0–0.5→Aggressive(1)/EPP 0–60；0.5–1→Efficient(2)/EPP 60–150；powercfg `be337238…` + INI EPP | powercfg + TS INI | 缺省跟随档位 |
| a2 | pl1（长时功耗墙） | 15–65 W | TS PowerLimitEAX/EDX（现网单调关系保留，运行时 MSR 复核）；power plan 联动 | TS INI + MSR | 步长 5W |
| a3 | pl2_boost（短时墙 = burst 上限） | pl1–95 W | 受 L3 Burst 桶约束（§6.3）；超桶部分强制钳到 pl1 | TS INI + L3 桶 | 步长 5W |
| a4 | uv_offset（Core+P-Cache 联动） | 0 – -80 mV | FIVR 编码 `mV×1.024→hex`（现网公式）；P-Cache 同值；**负向单调、安全方向只许保守**（放电步长 ≤5mV/次，需 ts_inject_ok 回执） | TS FIVR 注入 | 步长 5mV，钳位 [-80, 0] |
| a5 | power_plan（电源计划） | {0:Balanced, 1:HighPerf, 2:Ultimate} | GUID 映射（Ultimate 不可用则 fallback HighPerf，沿用 custom.bat 逻辑） | powercfg | 缺省跟随档位 |
| a6 | gear_request（档位上/下建议） | {-1:降, 0:保持, +1:升} | 只建议、不直切；需 L2 仲裁 + 用户 manual_pin 可一票否决；Extreme 上行需 mode=224 确认或前台重载证据 | L2 仲裁 | 缺省 0 |

约束：
- a0–a5 全部被当前档包络（§5）钳位；a6 跨档需经 L2 事务（互斥 15s 超时回滚）。
- a4（UV）为最高风险动作：仅允许在 `ts_inject_ok=1` 且温度余量 >5K 时加深；任何注入失败立即冻结 a4 并记 BlackBox（对应 R3）。
- 拔电（ac_online=0）时 L3 强制：`a2 ≤ 25W，a0 ≤ 3800MHz，a3 = a2`（拔电回退，阈值见 t4）。

---

## 5. Reward 权重（v1.0 锁定）

### 5.1 主公式（1s 步奖励）

```
R = w_perf * P_norm  - w_power * W_norm  - w_temp * T_viol
    - w_smooth * S_viol - w_noise * N_norm - w_burst * B_viol + w_batt * B_save
```

- `P_norm`：子模相关性能分（§5.2），0–1。
- `W_norm = pkg_power / gear_pl1_cap`，0–~1.5（clip 1.5）。
- `T_viol = max(0, cpu_temp_pkg - (gear_temp_ceiling - 5)) / 10`（提前 5K 起罚，clip 0–2）。
- `S_viol = clip(stutter_events_10s / 5, 0, 2)`（卡顿 5 次封顶起算）。
- `N_norm`：风扇噪声代理（rpm 归一化；不可读时用 `pkg_power/65` 代理并降权）。
- `B_save`：拔电时省电奖励 `= (1 - pkg_power/25)`，插电时恒 0。

### 5.2 权重表（按 8 子模分组，加和为 1；B_save 为拔电附加项不计入归一）

| 子模 | w_perf | w_power | w_temp | w_smooth | w_noise | 说明 |
|------|--------|---------|--------|----------|---------|------|
| W0 Idle 待机 | 0.05 | 0.45 | 0.20 | 0.05 | 0.25 | 省电静音优先 |
| W1 Office 办公 | 0.25 | 0.25 | 0.20 | 0.15 | 0.15 | 均衡偏静 |
| W2 Web 浏览 | 0.25 | 0.25 | 0.20 | 0.15 | 0.15 | 同办公 |
| W3 Build 编译 | 0.45 | 0.20 | 0.20 | 0.05 | 0.10 | 吞吐优先 |
| W4 Game-Eco 网游/轻载游戏 | 0.40 | 0.15 | 0.15 | 0.20 | 0.10 | 帧稳优先于极限帧 |
| W5 Game-Full 3A/满载游戏 | 0.45 | 0.10 | 0.15 | 0.25 | 0.05 | 流畅权重最高，噪声让路 |
| W6 Create 渲染/转码 | 0.50 | 0.15 | 0.20 | 0.05 | 0.10 | 吞吐+温度并重 |
| W7 Stress 压测 | 0.20 | 0.10 | 0.50 | 0.05 | 0.15 | 温度约束主导 |

- `B_viol`：burst 违规计数（超 Tmax 未降回 / 空桶请求，按步 clip 0–2；t4 §3.3 语义）；`w_burst = 0.5` 初值（与 shield 附加罚同量级，影子期调参；P1-2 增补）。
- 拔电附加：`w_batt = 0.30`，`R += w_batt * B_save`（仅 ac_online=0）。
- `P_norm` 定义：游戏类子模用 `clip(fps/目标帧, 0, 1)`（目标帧：W4=120，W5=90，以 1% Low 打 7 折混合）；非游戏用 `clip(1 - c0_residency_idle_excess, 0, 1)`，即“不堆空转功耗前提下的响应性”（细化由 thesis 验证矩阵量化）。
- 安全事件（shield 触发步）：该步 `R -= 1.0` 附加罚（记 `SHIELD_PENALTY`），防止策略学出“贴线蹭 shield”。

### 5.3 回合计分（供开题验证矩阵用）

`Return = mean(R) - 0.5 * std(R) - 2.0 * shield_rate - 1.0 * clamp_rate`，
其中 shield_rate / clamp_rate 为回合内步占比。要求：相对 B2 基线（`legion-legacy-b2` tag）Return 提升 ≥10% 且 shield_rate 不上升（t2 验证矩阵入口）。

---

## 6. 5 档 8 子模包络 + 地板 + Burst

### 6.1 5 档包络表（上限；RL 输出钳位于此）

现网 4 档值原样继承并加 G0 超静音档（待机/电池场景，t3 环境标定后可调 ±5%）。

| 档 G | 名称 | Fn+Q 对应 | 频墙上限 | PL1 上限 | PL2 上限 | UV 基准 | EPP/计划缺省 | 温度天花板 |
|------|------|-----------|----------|----------|----------|---------|--------------|------------|
| G0 | DeepQuiet 超静 | —（RL/电池自动） | 2800MHz | 15W | 25W | -40mV | Efficient/150/Balanced | 75°C |
| G1 | Quiet 安静 | 档位1/mode=1 | 3800MHz | 25W | 35W | -50mV | Efficient/150/Balanced | 80°C |
| G2 | Balance 均衡 | 档位2/mode=2 | 4800MHz | 40W | 55W | -65mV | Efficient/128/Balanced | 88°C |
| G3 | Beast 野兽 | 档位3/mode=3 | 5000MHz | 65W | 80W | -55mV | Aggressive/30/HighPerf | 93°C |
| G4 | Extreme 超能 | 档位4/mode=224 | 5200MHz | 65W | 95W | -45mV | Aggressive/0/Ultimate(→HighPerf fallback) | 95°C（P0-3定案：原98撞t4-L2线，降3K；TJMax见§8） |

档位切换=包络切换（L2 事务），档内 RL 连续调 a0–a5 不得超本行。

### 6.2 8 子模定义（负载路由器输出；置信度 <0.5 时保持上一子模）

| 子模 | 名称 | 典型前台 | 允许档位范围 | 缺省档 |
|------|------|----------|--------------|--------|
| W0 | Idle 待机 | 无/锁屏/纯桌面 | G0–G1 | G0 |
| W1 | Office 办公 | 文档/IM/邮件 | G1–G2 | G1 |
| W2 | Web 浏览 | 浏览器视频/多标签 | G1–G2 | G1 |
| W3 | Build 编译 | gcc/msbuild/rustc | G2–G4 | G2 |
| W4 | Game-Eco 轻载游戏 | 网游/2D/模拟器 | G2–G3 | G2 |
| W5 | Game-Full 满载游戏 | 3A/光追 | G3–G4 | G3 |
| W6 | Create 渲染 | blender/转码 | G2–G4 | G3 |
| W7 | Stress 压测 | prime95/手动 | G1–G4（温度 shield 主导） | 按当前档 |

判定信号：前台进程分类（主）+ gpu_util/cpu_util 联合门限（辅）+ fps 探针（游戏类确认）。误判兜底：连续 3s `T_viol>0` 或卡顿超限则升一档（经 L3，不经策略）。

### 6.3 地板（Floor：任何优化不得击穿的下限保证）

| 地板项 | 值 | 适用 | 说明 |
|--------|-----|------|------|
| F1 响应地板 | 切档事务 ≤15s；档内动作生效 ≤3s | 全档 | 超时回滚上一快照并记 BlackBox |
| F2 游戏流畅地板 | W4/W5 在允许档内 `fps_p1_low ≥ 45` 否则允许升档/放 burst | W4,W5 | 由流畅 shield 执行（阈值 t4 可 ±10%） |
| F3 温度地板（反向） | 任何档 `cpu_temp_pkg ≤ gear_temp_ceiling`，`≥ ceiling-5K` 起罚，`≥ ceiling` L3 强制降频降 PL1 | 全档 | 天花板以 TJMax（§8）为基准向下偏移，严于 EC/BIOS 硬保护 |
| F4 拔电地板 | 拔电强制 G0/G1 包络 + a2≤25W + burst 冻结 | 电池 | 恢复插电后 10s 内回原档（防抖） |
| F5 注入诚实地板 | `ts_inject_ok=0` 时冻结 a4 加深且 UI/日志必须显式报错（禁止记 done） | 全档 | 根治 R3“静默 FIVR 失败仍报 done” |

### 6.4 Burst 规格（短时加速预算桶）

- 模型：token bucket，能量单位，持续包络以上部分按实际功耗积分扣费。
  **本草案通用初值（C=120 W·s / r=8 W·s/s）作废（P1-1），以 t4 分档表为准**：
  Quiet 0.15kJ / Balance 0.70kJ / Beast 0.60kJ / Extreme 0.675kJ（见围栏 §3.2）。
  refill 仅当 `temp_headroom > 8K` 且 `shield_active=0` 时回充。
- 触发：仅 W3/W5/W6 且 `submode_conf ≥ 0.6` 且 `burst_tokens > 0.2` 时允许 `a3 > a2`。
- 上限：`a3 ≤ min(档位PL2上限, a2 + 30W)`；单次 burst ≤10s，结束后强制冷却 20s（期间 `a3 = a2`）。
- 熔断：burst 期间 `cpu_temp_pkg ≥ ceiling - 3K` 立即清零输出（`a3 = a2`，桶不停充）；桶空时 L3 否决码 `BURST_EMPTY`。
- 可观测：`burst_tokens` 进 State48（s33），每次 burst 记 BlackBox（起止/耗桶/温度峰值）。

---

## 7. 与 t2/t3/t4 的接口（供 t5 汇总）

- → t2（开题/验证）：State48/Action7/Reward §5.3 为验证矩阵输入；要求双机 × 8 子模 ×（静态基线 vs 本规格）对照。
- → t3（环境）：需标定项——NVML 可用性、MSR/RAPL 读可用性、风扇转速可读性（否则 s23 用代理）、Ultimate 计划存在性、G0 档 15W/2800MHz 稳定性。
- → t4（安全）：本草案输出阈值初值（温度天花板/Burst 桶/拔电回退/F1–F5 地板），t4 可收紧不可放宽；否决码与 BlackBox 字段两边对齐。
- 已知风险承接：P1（HKCU 跨账户）→ §2.2；P2/R2/R5（竞态/双触发）→ L2 互斥 + L5 单一仲裁；R3（静默 FIVR 失败）→ s46 + F5；R6（SYSTEM 重启 LLT 回退）→ 权限分离；P3（虚假成功日志）→ L2 返回值必检 + BlackBox。

---

## 8. 版本与确认事项

- 版本：**v1.0 冻结**（P0 E1 已验收；P0-1/P0-2/P0-3/P1-1/P1-2 已落盘）；HAL_MAP v1.0；Reward v1.0。
- **TJMax（P0-3 关联输入，用户确认）**：A机 255HX **TJMax=105°C**；B机 14900HX 未知，E2 开机探测为准。
  重构实现要求：**禁止硬编码温度阈值**——HAL 启动时读 MSR `IA32_TEMPERATURE_TARGET (0x1A2[22:16])` 得 TJMax，
  t4 四级线按 `WARN=TJMax-15 / L1=TJMax-10 / L2=TJMax-7 / L3=TJMax-5` 相对偏移生成；
  本表 G0–G4 天花板为 105 基准下的绝对值，B机按其 TJMax 等比平移后影子校准。
- **P0-3 定案**：采用推荐a——G4 天花板 98→**95°C**（=L1线，距L2留3K余量）。
  98°C 碰的是 **CPU域 Package/最热P-core 的 t4-L2 跳闸线**（GPU域另表 L2=88°C，无关；EC/BIOS硬保护≈105°C级，不动）。
  DC 模式 L1/L2 各−2°C 规则不变；G4 真实下发仍最后放行。
- **单例锁教训（2026-09-15 清理实证）**：旧 `watcher.lock` 被未知 Session-0 进程长期持有，
  `FileShare::None` 抢锁失败静默 `exit 0` 导致新实例永不启动。新实现必须：
  ①换锁文件名（如 `hal-actuation.lock`，禁用旧名）；②抢锁失败时读 PID 文件做存活校验，
  持锁进程已死则破锁接管并告警，禁止静默退出；③锁状态进 BlackBox。
- 待 t3/t4 确认后可锁 v1.0 的项：G0 包络精确值、s23 风扇源、W4/W5 目标帧、F2 地板帧数、Burst 桶 C/r。
- 变更规则：包络/Reward 权重/天花板任一改动必须发版（v0.x→v1.0）并同步 thesis 验证矩阵基线。

*— spec-architect，t1 交付 —*
