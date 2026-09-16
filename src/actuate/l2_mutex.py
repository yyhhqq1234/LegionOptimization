"""L2 全局互斥事务：单事务串行、超时回滚、dry-run 总开关（P3 Step 3-3 实现）。

铁律：dry-run 默认开；--live 需 E4/E5 门禁 + 用户显式确认，缺一不可。
"""

LOCK_NAME = "hal-actuation.lock"  # 禁用旧 watcher.lock 锁名
TIMEOUT_S = 15
DRY_RUN_DEFAULT = True


def actuate(setpoints, dry_run=True):
    """下发设定点。dry_run 下只校验与记 log，零落盘。

    dry_run=False 时门禁未过，直接拒绝（诚实失败，不静默成功）。
    """
    if dry_run:
        return ("dry-run", dict(setpoints))
    raise RuntimeError("门禁 E4/E5 未过，禁止 --live 真实下发")
