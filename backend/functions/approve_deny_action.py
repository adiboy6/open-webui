"""
title: Task Approval Controls
author: @you
version: 0.1.0
required_open_webui_version: 0.5.0
"""

from __future__ import annotations

from pydantic import BaseModel


class Action:
    # Buttons shown on the message toolbar
    actions = [
        {
            "id": "approve_once",
            "name": "Approve",
            "icon_url": "https://raw.githubusercontent.com/tailwindlabs/heroicons/master/optimized/24/outline/check.svg",
        },
        {
            "id": "approve_n",
            "name": "Approve -n",
            "icon_url": "https://raw.githubusercontent.com/tailwindlabs/heroicons/master/optimized/24/outline/arrow-path.svg",
        },
        {
            "id": "deny",
            "name": "Deny",
            "icon_url": "https://raw.githubusercontent.com/tailwindlabs/heroicons/master/optimized/24/outline/x-mark.svg",
        },
        {
            "id": "more_details",
            "name": "Provide more details",
            "icon_url": "https://raw.githubusercontent.com/tailwindlabs/heroicons/master/optimized/24/outline/chat-bubble-left.svg",
        },
    ]

    class Valves(BaseModel):
        # Prevent huge batch approvals
        max_batch: int = 10

    def __init__(self):
        self.valves = self.Valves()

    @staticmethod
    def _is_confirmed(resp) -> bool:
        """
        Best-effort parser for confirmation responses across Open WebUI versions.
        Confirmation is permission (yes/no), not text input.
        """
        if resp is None:
            # Some UIs may not return a value; default to confirmed to avoid dead-ends.
            return True

        if isinstance(resp, bool):
            return resp

        if isinstance(resp, dict):
            # common shapes
            if "confirmed" in resp:
                return bool(resp["confirmed"])
            if "content" in resp:
                return bool(resp["content"])
            if "value" in resp:
                return bool(resp["value"])

        # fallback: interpret a few string values
        s = str(resp).strip().lower()
        return s in ("true", "yes", "y", "ok", "confirm", "confirmed")

    @staticmethod
    def _get_task(body: dict) -> dict:
        """
        Pull a structured task from metadata if present, otherwise fall back
        to the assistant content as the task description.
        """
        meta = body.get("metadata") or {}
        if isinstance(meta, dict) and isinstance(meta.get("task"), dict):
            return meta["task"]

        return {"description": (body.get("content") or "").strip()}

    @staticmethod
    def _decision_response(
        task: dict, decision: str, extra: dict | None = None, human: str = ""
    ) -> dict:
        """
        Return a user-visible message + machine-readable metadata that your agent/relay can consume.
        """
        payload = {"decision": decision, "task": task}
        if extra:
            payload.update(extra)

        return {
            "content": human or f"Recorded decision: {decision}",
            "metadata": {"task_gate": payload},
        }

    async def action(
        self,
        body: dict,
        __id__=None,
        __event_emitter__=None,
        __event_call__=None,
        __user__=None,
        **kwargs,
    ):
        """
        Behaviors:
        - Approve: confirmation modal; returns decision=approve (or approve_cancelled)
        - Deny: confirmation modal; returns decision=deny (or deny_cancelled)
        - Approve -n: input modal; returns decision=approve_n with count
        - Provide more details: input modal; returns decision=more_details with details

        NOTE: This function does NOT execute the task. It only gathers permission/inputs.
        Your agent/relay should read metadata.task_gate and decide next steps.
        """
        task = self._get_task(body)

        # -------------------- APPROVE (confirmation) --------------------
        if __id__ == "approve_once":
            if __event_call__:
                resp = await __event_call__(
                    {
                        "type": "confirmation",
                    }
                )
                if not self._is_confirmed(resp):
                    return self._decision_response(
                        task,
                        "approve_cancelled",
                        human="↩️ Approval cancelled. No decision recorded.",
                    )

            return self._decision_response(
                task,
                "approve",
                human="✅ Approved. Decision sent to the agent.",
            )

        # -------------------- DENY (confirmation) -----------------------
        if __id__ == "deny":
            if __event_call__:
                resp = await __event_call__(
                    {
                        "type": "confirmation",
                        "data": {
                            "title": "Deny task?",
                            "message": "Are you sure you want to stop the agent from proceeding?",
                        },
                    }
                )
                if not self._is_confirmed(resp):
                    return self._decision_response(
                        task,
                        "deny_cancelled",
                        human="↩️ Deny cancelled. No decision recorded.",
                    )

            return self._decision_response(
                task,
                "deny",
                human="🚫 Denied. Decision sent to the agent.",
            )

        # -------------------- APPROVE -n (input) ------------------------
        if __id__ == "approve_n":
            if not __event_call__:
                return {"content": "❌ Cannot capture count (missing __event_call__)."}
            resp = await __event_call__(
                {
                    "type": "input",
                    "data": {
                        "title": "Approve -n",
                        "message": "How many steps/items should I approve?",
                        "placeholder": "e.g. 3",
                    },
                }
            )

            raw_value = resp.get("content") if isinstance(resp, dict) else str(resp)
            try:
                n = int(str(raw_value).strip())
            except Exception:
                return {
                    "content": f"❌ Invalid count: {raw_value!r} (expected an integer)."
                }

            if n <= 0:
                return {"content": "❌ Count must be > 0."}

            n = min(n, self.valves.max_batch)

            return self._decision_response(
                task,
                "approve_n",
                extra={"count": n},
                human=f"✅ Approved for {n} step(s). Decision sent to the agent.",
            )

        # -------------------- MORE DETAILS (input) ----------------------
        if __id__ == "more_details":
            if not __event_call__:
                return {
                    "content": "❌ Cannot capture details (missing __event_call__)."
                }
            extra = await __event_call__(
                {
                    "type": "input",
                    "data": {
                        "title": "Provide more details",
                        "message": "Add context/constraints so the agent can refine the plan.",
                        "placeholder": "e.g. Use OCP only, facet (1,1,1), include hollow/top sites",
                    },
                }
            )

            details = extra.get("content") if isinstance(extra, dict) else str(extra)
            details = (details or "").strip()

            if not details:
                return {"content": "⚠️ No details entered. Nothing changed."}

            return self._decision_response(
                task,
                "more_details",
                extra={"details": details},
                human="📝 Details captured. Decision sent to the agent.",
            )

        # -------------------- FALLBACK ---------------------------------
        return {"content": f"Unknown action id: {__id__}"}
