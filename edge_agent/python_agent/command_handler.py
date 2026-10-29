"""
Edge node command execution module.
Handles remote state transitions, service resets, and throttling.
"""
from sre_engine.schemas import CommandPayload, CommandAction, CommandResponse, NodeStatus


class EdgeCommandHandler:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.current_status = NodeStatus.HEALTHY
        self.throttled = False
        self.running_services = ["telemetry_worker", "stream_buffer", "watchdog"]

    def execute_command(self, cmd: CommandPayload) -> CommandResponse:
        """Processes and applies a remote command issued by the central backend."""
        if cmd.target_node_id != self.node_id:
            return CommandResponse(
                command_id=cmd.command_id,
                node_id=self.node_id,
                success=False,
                message=f"Target node mismatch: command intended for {cmd.target_node_id}"
            )

        if cmd.action == CommandAction.SET_STATE:
            new_state = cmd.parameters.get("new_state")
            if new_state in NodeStatus.__members__:
                self.current_status = NodeStatus(new_state)
                return CommandResponse(
                    command_id=cmd.command_id,
                    node_id=self.node_id,
                    success=True,
                    message=f"Node status successfully updated to {self.current_status.value}"
                )
            return CommandResponse(
                command_id=cmd.command_id,
                node_id=self.node_id,
                success=False,
                message=f"Invalid target state: {new_state}"
            )

        elif cmd.action == CommandAction.THROTTLE:
            enable_throttle = cmd.parameters.get("enable", True)
            self.throttled = enable_throttle
            state_msg = "enabled" if self.throttled else "disabled"
            return CommandResponse(
                command_id=cmd.command_id,
                node_id=self.node_id,
                success=True,
                message=f"Telemetry rate-limiting {state_msg}"
            )

        elif cmd.action == CommandAction.RESTART_SERVICE:
            service = cmd.parameters.get("service_name")
            if service in self.running_services:
                return CommandResponse(
                    command_id=cmd.command_id,
                    node_id=self.node_id,
                    success=True,
                    message=f"Service '{service}' gracefully cycled and running"
                )
            return CommandResponse(
                command_id=cmd.command_id,
                node_id=self.node_id,
                success=False,
                message=f"Service '{service}' not recognized in active process table"
            )

        elif cmd.action == CommandAction.PING:
            return CommandResponse(
                command_id=cmd.command_id,
                node_id=self.node_id,
                success=True,
                message="PONG"
            )

        return CommandResponse(
            command_id=cmd.command_id,
            node_id=self.node_id,
            success=False,
            message=f"Unsupported action: {cmd.action}"
        )