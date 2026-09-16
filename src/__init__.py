"""LegionOptimization 业务代码包（P3 脚手架）。

HAL L0-L4 + 双侧车，契约见 specs/SYSTEM_SPEC_DRAFT_v1.0.md 与
docs/safety-fence-spec.md（v1.0 冻结）。

铁律：默认 dry-run；门禁通过前零真实写入；G0–G4 唯一档位维度，
DC 正交（禁 G5）；温度阈值一律相对 TJMax 偏移，禁止硬编码。
"""
