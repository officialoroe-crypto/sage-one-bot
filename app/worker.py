import socket
import threading
import time
import uuid

from app.orchestrator import orchestrator
from execution.parallel import parallel_mission_executor
from missions.planner import planner
from research.persistence import research_persistence
from sales.service import sales_engine
from research.synthesis import research_synthesis_engine
from tasks.engine import tasks
from world_intelligence.engine import world_intelligence
from notifications.service import create_task_notification
from database.connection import SessionLocal
from database.repository import repository
from database.models import Task
from identity.memory_learning import learn_memory_candidates
from identity.profile import SessionLocal as ProfileSessionLocal, UserProfile
from workflows.repository import repository as workflow_repository
from economy.models import PremiumSparkTransaction
from economy.service import reserve_premium_work, settle_premium_sparks, refund_premium_sparks
from sqlalchemy import select


class SageWorker:
    def __init__(self, worker_id=None, lease_seconds=120, heartbeat_interval=30, retry_base_seconds=10):
        self.name = 'SAGE WORKER'
        self.worker_id = worker_id or self._default_worker_id()
        self.lease_seconds = max(30, int(lease_seconds))
        self.heartbeat_interval = max(5, int(heartbeat_interval))
        self.retry_base_seconds = max(1, int(retry_base_seconds))

    @staticmethod
    def _default_worker_id():
        host = socket.gethostname()
        return f'{host}-{uuid.uuid4().hex[:8]}'

    def run_goal(self, goal, session_id=None, priority=3):
        try:
            result = orchestrator.execute_goal(
                goal=goal,
                session_id=session_id,
                priority=priority,
            )
            return {'success': True, 'result': result}
        except Exception as error:
            return {'success': False, 'error': str(error)}

    def recover_expired_tasks(self):
        return tasks.recover_expired()

    @staticmethod
    def _premium_operation_key(task_id):
        return f"task:{task_id}"

    def _reserve_premium_for_task(self, task):
        work_key = task.get("premium_work_key")
        owner_key = task.get("owner_key")
        if not work_key:
            return
        if not owner_key:
            raise RuntimeError("Premium task is missing its trusted owner identity.")
        with SessionLocal() as db:
            reserve_premium_work(db, owner_key, self._premium_operation_key(task["id"]),
                                 work_key, metadata={"task_id": task["id"]})

    def _persist_task_outcome(self, task, result):
        """Index completed work in the selected project and memory when consent allows."""
        project_id = task.get("project_id")
        profile_id = task.get("profile_id")

        if task.get("session_id"):
            try:
                with SessionLocal() as db:
                    repository.add_message(
                        db,
                        task["session_id"],
                        "assistant",
                        str(result.get("final") if isinstance(result, dict) and result.get("final") else result),
                    )
            except Exception:
                pass

        if project_id and profile_id:
            try:
                with SessionLocal() as db:
                    project = workflow_repository.get_project(db, profile_id, project_id)
                    if project is not None:
                        research_id = result.get("research_id") if isinstance(result, dict) else None
                        workflow_repository.create_asset(
                            db,
                            project,
                            name=f"Research result: {task['title'][:160]}" if research_id else f"Task result: {task['title'][:160]}",
                            asset_type="research" if research_id else "text",
                            status="completed",
                            metadata={
                                "task_id": task["id"],
                                "source": "durable_task",
                                "research_id": research_id,
                                "result": str(result)[:12000],
                            },
                        )
            except Exception:
                # Execution durability wins; project indexing is additive.
                pass

        if profile_id:
            try:
                with ProfileSessionLocal() as db:
                    row = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
                    memory_consent = bool(row.memory_consent) if row else False

                if memory_consent:
                    learn_memory_candidates(
                        profile_id=profile_id,
                        memory_consent=True,
                        candidates=[{
                            "memory_type": "experience",
                            "content": f"Completed SAGE task: {task['title'][:240]}",
                            "importance": 0.35,
                            "confidence": 1.0,
                        }],
                    )
            except Exception:
                # Memory learning is consent-gated and must never break task settlement.
                pass

    def _finalize_premium_for_task(self, task, success):
        if not task or not task.get("premium_work_key") or not task.get("owner_key"):
            return
        with SessionLocal() as db:
            operation_key = self._premium_operation_key(task["id"])
            if success:
                settle_premium_sparks(db, task["owner_key"], operation_key)
            else:
                refund_premium_sparks(db, task["owner_key"], operation_key,
                                      reason=f"Premium task {task['id']} failed")

    def reconcile_premium_transactions(self):
        """Repair crash window between terminal task state and Spark finalization."""
        with SessionLocal() as db:
            rows = db.execute(
                select(Task.id, Task.owner_key, Task.status).where(
                    Task.premium_work_key.is_not(None),
                    Task.owner_key.is_not(None),
                    Task.status.in_(("completed", "failed", "cancelled")),
                )
            ).all()
            for task_id, owner_key, status in rows:
                operation_key = self._premium_operation_key(task_id)
                transaction = db.scalar(select(PremiumSparkTransaction).where(
                    PremiumSparkTransaction.owner_key == owner_key,
                    PremiumSparkTransaction.operation_key == operation_key,
                ))
                if transaction is None or transaction.status != "reserved":
                    continue
                if status == "completed":
                    settle_premium_sparks(db, owner_key, operation_key)
                else:
                    refund_premium_sparks(db, owner_key, operation_key,
                                          reason=f"Premium task {task_id} ended as {status}")

    def _local_execution_allowed(self):
        """Do not block cloud-backed durable work on local CPU pressure.

        Provider routing owns local-resource protection. Medium/heavy work is
        cloud-first, and light work can fall back to cloud when local Ollama
        is not allowed. Blocking the queue here would stall both paths.
        """
        return True, None

    def claim(self):
        allowed, protection = self._local_execution_allowed()
        if not allowed:
            return protection

        # Only top-level tasks belong to the global durable worker queue.
        # Mission child tasks are owned by their mission execution loop.
        return tasks.claim_next_root(
            worker_id=self.worker_id,
            lease_seconds=self.lease_seconds,
        )

    def _heartbeat_loop(self, task_id, stop_event, state):
        while not stop_event.wait(self.heartbeat_interval):
            heartbeat = tasks.heartbeat(
                task_id=task_id,
                worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
            )
            if heartbeat is None:
                state['lost'] = True
                stop_event.set()
                return

    def _start_heartbeat(self, task_id):
        stop_event = threading.Event()
        state = {'lost': False}
        thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(task_id, stop_event, state),
            name=f'sage-heartbeat-{task_id}',
            daemon=True,
        )
        thread.start()
        return stop_event, thread, state

    def _execute_task_payload(self, task):
        description = task['description']
        agent = task.get('agent', 'general')
        session_id = task.get('session_id')
        priority = task.get('priority', 3)

        # World Intelligence refreshes are durable background work. The worker
        # owns the task lease while the bounded public-world refresh executes.
        if agent == 'world':
            prefix = 'Refresh SAGE World Intelligence:'
            requested = description.removeprefix(prefix).strip()
            topics = [item.strip() for item in requested.split('|') if item.strip()]
            return world_intelligence.refresh(topics or None)

        # Sales audits are durable, structured business workflows. They run under the same
        # task lease and return an approval-gated outreach draft; they never send messages.
        if agent == 'sales':
            return sales_engine.run_from_task(
                description=description,
                task_id=task['id'],
                owner_key=task.get('owner_key'),
                project_id=task.get('project_id'),
                profile_id=task.get('profile_id'),
            )

        # Research remains a first-class durable workload because its
        # specialized pipeline persists a citation/evidence graph separately
        # from the task row.
        if agent == 'research':
            result = research_synthesis_engine.synthesize(
                question=description.removeprefix('Research:').strip(),
            )
            if result.get('success'):
                persisted = research_persistence.save(
                    result,
                    task_id=task['id'],
                    session_id=session_id,
                    **({'owner_key': task['owner_key']} if task.get('owner_key') else {}),
                )
                result = {
                    **result,
                    'research_id': persisted['research_id'],
                }
            return result

        # All other durable goals use the mission planner + dependency-aware
        # execution engine. Independent child tasks may execute concurrently;
        # dependent tasks are held until the next ready-task wave.
        plan = planner.plan(
            goal=description,
            session_id=session_id,
            priority=priority,
        )

        mission = plan.get('mission', {})
        mission_id = mission.get('id') if isinstance(mission, dict) else None
        if not mission_id:
            raise RuntimeError('Mission planner returned no mission ID.')

        execution_kwargs = {
            "mission_id": mission_id,
            "max_steps": 20,
        }
        if task.get("owner_key"):
            execution_kwargs["owner_authorized"] = True

        execution = parallel_mission_executor.execute_mission(
            **execution_kwargs,
        )

        return {
            'success': execution.get('success', False),
            'mission_id': mission_id,
            'plan': plan,
            'execution': execution,
        }

    def execute_task(self, task):
        task_id = task['id']
        stop_event, heartbeat_thread, heartbeat_state = self._start_heartbeat(task_id)

        try:
            if heartbeat_state['lost']:
                raise RuntimeError('Worker lost task ownership before execution started.')

            result = self._execute_task_payload(task)

            if heartbeat_state['lost']:
                raise RuntimeError('Worker lost task ownership during execution.')

            if isinstance(result, dict) and result.get('success') is False:
                raise RuntimeError(
                    result.get('error')
                    or result.get('execution', {}).get('status', 'Mission execution failed.')
                )

            return result
        finally:
            stop_event.set()
            heartbeat_thread.join(timeout=max(1, self.heartbeat_interval + 1))

    def run_once(self):
        self.reconcile_premium_transactions()
        self.recover_expired_tasks()
        try:
            from automation.service import automation
            automation.dispatch_due(limit=10)
        except Exception:
            pass
        task = self.claim()

        if not task:
            return None

        if task.get('status') == 'deferred':
            return {
                'success': True,
                'task': None,
                **task,
            }

        task_id = task['id']

        try:
            self._reserve_premium_for_task(task)
            result = self.execute_task(task)
            completed = tasks.complete_claim(
                task_id=task_id,
                worker_id=self.worker_id,
                result=str(result),
            )

            if completed is not None:
                self._persist_task_outcome(task, result)
                self._finalize_premium_for_task(task, success=True)
                try:
                    create_task_notification(completed, success=True)
                except Exception:
                    # Notification delivery must never turn a completed task into a failure.
                    pass

            if completed is None:
                return {
                    'success': False,
                    'task': None,
                    'error': 'Worker lost task ownership before completion.',
                }

            return {'success': True, 'task': completed}

        except Exception as error:
            delay = self.retry_base_seconds * (2 ** max(0, task.get('retries', 0)))
            failed = tasks.fail_claim(
                task_id=task_id,
                worker_id=self.worker_id,
                error=str(error),
                retry_delay_seconds=delay,
            )
            if failed is not None and failed.get('status') in {'failed', 'cancelled'}:
                self._finalize_premium_for_task(task, success=False)
                try:
                    create_task_notification(
                        failed,
                        success=False,
                        body=f"{failed.get('title', 'Background task')} failed: {str(error)}",
                    )
                except Exception:
                    # Notification delivery must never mask the terminal task failure.
                    pass
            return {
                'success': False,
                'task': failed,
                'error': str(error),
            }

    def run_forever(self, poll_interval=2.0):
        while True:
            result = self.run_once()
            if result is None or result.get('status') == 'deferred':
                time.sleep(max(0.1, poll_interval))


worker = SageWorker()
