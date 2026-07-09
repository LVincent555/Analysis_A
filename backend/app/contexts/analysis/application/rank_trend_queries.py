"""Rank and trend analysis query use cases."""

from __future__ import annotations

from typing import Any

from .ports import RankJumpAnalysisPort, SteadyRiseAnalysisPort
from .queries import AnalyzeRankJumpQuery, AnalyzeSteadyRiseQuery


class AnalyzeRankJumpUseCase:
    def __init__(self, analysis_port: RankJumpAnalysisPort) -> None:
        self.analysis_port = analysis_port

    def execute(self, query: AnalyzeRankJumpQuery) -> Any:
        return self.analysis_port.analyze_rank_jump(query)


class AnalyzeSteadyRiseUseCase:
    def __init__(self, analysis_port: SteadyRiseAnalysisPort) -> None:
        self.analysis_port = analysis_port

    def execute(self, query: AnalyzeSteadyRiseQuery) -> Any:
        return self.analysis_port.analyze_steady_rise(query)
