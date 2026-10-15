"""Dependency-aware parallel mission execution.

Mission child tasks are not placed on the global durable worker queue. This
executor owns a mission's ready-task waves and runs independent tasks in
parallel while respecting mission-level pause/cancel controls and recovery.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from execution.engine import ExecutionEngine
from execution.progress import MissionProgress
from missions.engine import mission_engine
from missions.intelligence import mission_intelligence


class ParallelMissionExecutor:
    """Execute independent mission tasks concurrently in dependency waves."""

    def __init__(self, max_parallel: int = 2, engine_factory=ExecutionEngine):
        self.max_parallel = max(1, int(max_parallel))
        self.engine_factory = engine_factory

    def _execute_task(self, task_id: str, owner_authorized: bool = False):
        engine = self.engine_factory()
        if owner_authorized:
            return engine.execute_task(task_id, owner_authorized=True)
        return engine.execute_task(task_id)

    @staticmethod
    def _summary(mission_id: str, history: list[dict]) -> dict:
        tasks = mission_engine.get_tasks(mission_id)
        total = len(tasks)
        verified = sum(
            1
            for task in tasks
            if task.get("status") == "completed"
            and task.get("verification_status") == "verified"
        )
        running = sum(1 for task in tasks if task.get("status") == "running")
        failed = sum(1 for task in tasks if task.get("status") == "failed")
        pending = sum(1 for task in tasks if task.get("status") == "pending")

        return {
            "total_tasks": total,
            "verified_tasks": verified,
            "running_tasks": running,
            "failed_tasks": failed,
            "pending_tasks": pending,
            "progress_percent": round((verified / total) * 100, 2) if total else 0,
            "completed_task_ids": [
                task["id"]
                for task in tasks
                if task.get("status") == "completed"
                and task.get("verification_status") == "verified"
            ],
            "failed_task_ids": [
                task["id"] for task in tasks if task.get("status") == "failed"
            ],
            "history_count": len(history),
        }

    @classmethod
    def _response(
        cls,
        status: str,
        success: bool,
        mission_id: str,
        history: list[dict],
        waves: int,
        events: list[dict] | None = None,
        **extra,
    ) -> dict:
        mission = (
            mission_engine.get_mission(mission_id)
            if hasattr(mission_engine, "get_mission")
            else {"id": mission_id, "status": status}
        )
        payload = {
            "success": success,
            "status": status,
            "mission": mission,
            "summary": cls._summary(mission_id, history),
            "history": history,
            "waves": waves,
            "events": events or [],
        }
        payload.update(extra)
        return payload

    @staticmethod
    def _control_status(mission_id: str):
        try:
            return mission_intelligence.get_status(mission_id)
        except Exception:
            return None

    @staticmethod
    def _synthesize(mission_id: str):
        try:
            return mission_intelligence.synthesize(mission_id)
        except Exception:
            return None

    def execute_mission(self, mission_id: str, max_steps: int = 20, owner_authorized: bool = False) -> dict:
        history: list[dict] = []
        waves = 0
        progress = MissionProgress(mission_id)
        progress.emit(
            "mission_started",
            "executing",
            "Mission execution started.",
        )

        while len(history) < max_steps:
            control_status = self._control_status(mission_id)
            if control_status == "paused":
                progress.emit("mission_paused", "paused", "Mission paused; no new task wave will start.", wave=waves)
                return self._response("paused", True, mission_id, history, waves, progress.snapshot())
            if control_status == "cancelled":
                progress.emit("mission_cancelled", "cancelled", "Mission cancelled; no new task wave will start.", wave=waves)
                return self._response("cancelled", False, mission_id, history, waves, progress.snapshot())

            mission = mission_engine.refresh_mission_status(mission_id)

            if mission["status"] == "completed":
                progress.emit(
                    "mission_completed",
                    "completed",
                    "All mission tasks are verified.",
                    wave=waves,
                    progress_percent=100,
                )
                synthesis = self._synthesize(mission_id)
                extra = {"synthesis": synthesis} if synthesis is not None else {}
                return self._response("completed", True, mission_id, history, waves, progress.snapshot(), **extra)

            if mission["status"] == "failed":
                progress.emit("mission_failed", "failed", "Mission reached a failed state.", wave=waves)
                return self._response("failed", False, mission_id, history, waves, progress.snapshot())

            ready = mission_engine.get_ready_tasks(mission_id)
            if not ready:
                mission = mission_engine.refresh_mission_status(mission_id)
                progress.emit("mission_blocked", "blocked", "No executable task is currently ready.", wave=waves)
                return self._response("blocked", False, mission_id, history, waves, progress.snapshot())

            remaining = max_steps - len(history)
            batch = ready[: min(self.max_parallel, remaining)]
            waves += 1
            task_ids = [task["id"] for task in batch]
            progress.emit(
                "wave_started",
                "executing",
                f"Starting execution wave {waves}.",
                wave=waves,
                task_ids=task_ids,
                progress_percent=self._summary(mission_id, history)["progress_percent"],
            )

            with ThreadPoolExecutor(
                max_workers=len(batch),
                thread_name_prefix="sage-mission",
            ) as executor:
                futures = {
                    (
                        executor.submit(
                            self._execute_task,
                            task["id"],
                            True,
                        )
                        if owner_authorized
                        else executor.submit(self._execute_task, task["id"])
                    ): task["id"]
                    for task in batch
                }

                wave_results = []
                for future in as_completed(futures):
                    task_id = futures[future]
                    try:
                        task_result = future.result()
                    except Exception as error:
                        task_result = {
                            "success": False,
                            "task_id": task_id,
                            "status": "exception",
                            "error": str(error),
                        }
                    wave_results.append(task_result)

            wave_results.sort(key=lambda item: item.get("task_id", ""))
            history.extend(wave_results)
            summary = self._summary(mission_id, history)
            progress.emit(
                "wave_completed",
                "executing",
                f"Execution wave {waves} completed.",
                wave=waves,
                task_ids=task_ids,
                progress_percent=summary["progress_percent"],
            )

            failed_results = [
                result for result in wave_results if not result.get("success", False)
            ]
            if failed_results:
                unrecoverable = []
                for result in failed_results:
                    task_id = result.get("task_id")
                    if not task_id:
                        continue
                    task = next(
                        (item for item in mission_engine.get_tasks(mission_id) if item["id"] == task_id),
                        None,
                    )
                    if task is None:
                        continue
                    error = result.get("error", result.get("status", "task failure"))
                    strategy = mission_intelligence.recovery_strategy(task, error)
                    mission_intelligence.create_recovery_record(task, strategy)
                    progress.emit(
                        "task_recovery_planned",
                        "recovering",
                        f"Recovery strategy selected for task {task_id}: {strategy['strategy']}.",
                        wave=waves,
                        task_ids=[task_id],
                        progress_percent=summary["progress_percent"],
                    )

                    if strategy["retryable"]:
                        try:
                            mission_intelligence.prepare_retry(task_id, error)
                            progress.emit(
                                "task_retry_scheduled",
                                "recovering",
                                f"Task {task_id} reset for another execution attempt.",
                                wave=waves,
                                task_ids=[task_id],
                                progress_percent=summary["progress_percent"],
                            )
                            continue
                        except Exception as retry_error:
                            unrecoverable.append(
                                {"task_id": task_id, "error": str(retry_error)}
                            )
                    else:
                        unrecoverable.append(
                            {"task_id": task_id, "error": str(error)}
                        )

                if unrecoverable:
                    mission_engine.refresh_mission_status(mission_id)
                    progress.emit(
                        "mission_failed",
                        "failed",
                        "At least one failed task could not be recovered.",
                        wave=waves,
                        task_ids=[item["task_id"] for item in unrecoverable],
                        progress_percent=summary["progress_percent"],
                    )
                    return self._response(
                        "task_failed",
                        False,
                        mission_id,
                        history,
                        waves,
                        progress.snapshot(),
                        recovery=unrecoverable,
                    )

                continue

            control_status = self._control_status(mission_id)
            if control_status == "paused":
                progress.emit("mission_paused", "paused", "Mission paused after the active wave finished.", wave=waves, progress_percent=summary["progress_percent"])
                return self._response("paused", True, mission_id, history, waves, progress.snapshot())
            if control_status == "cancelled":
                progress.emit("mission_cancelled", "cancelled", "Mission cancelled after the active wave finished.", wave=waves, progress_percent=summary["progress_percent"])
                return self._response("cancelled", False, mission_id, history, waves, progress.snapshot())

        mission_engine.refresh_mission_status(mission_id)
        progress.emit("max_steps_reached", "blocked", "Mission execution reached its step budget.", wave=waves)
        return self._response("max_steps_reached", False, mission_id, history, waves, progress.snapshot())


parallel_mission_executor = ParallelMissionExecutor()
