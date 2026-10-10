"""統一職位資料模型。

不同平台 CLI 的輸出欄位不一致，這裡定義一個共同結構，
各 provider 負責把自家格式正規化成 Job，報告層只認 Job。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Job:
    """一筆職位（已正規化）。欄位缺失時以空字串表示，方便直接渲染。"""

    source: str = ""          # 來源平台，如 "boss" / "liepin"
    title: str = ""           # 職位名稱
    company: str = ""         # 公司名稱
    salary: str = ""          # 薪資（原樣字串）
    city: str = ""            # 城市 / 地點
    experience: str = ""      # 經驗要求
    education: str = ""       # 學歷要求
    skills: list[str] = field(default_factory=list)  # 技能標籤
    url: str = ""             # 職位連結（若有）
    raw: dict[str, Any] = field(default_factory=dict)  # 原始資料，供除錯

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
