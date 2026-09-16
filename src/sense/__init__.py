"""L0 传感层（只读）：WMI 事件 / nvidia-smi 轮询 / OS 计数器 / 前台与帧率探针。

只读层永不落盘调优参数；WMI 事件只写 gear_desired（L5 单一仲裁）。
"""
