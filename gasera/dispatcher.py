from .commands import GASERA_COMMANDS
from buzzer.buzzer_facade import buzzer

class GaseraCommandDispatcher:
    def __init__(self, gasera):
        self.gasera = gasera

    def handle(self, command: str, args=None) -> dict:
        args = args or []
        if command not in GASERA_COMMANDS:
            buzzer.play("warning")
            return {"error": f"Unknown command: {command}"}
        try:
            buzzer.play("ok")
            handler = GASERA_COMMANDS[command]["handler"]
            result = handler(self.gasera, args)
            return self._wrap(result)
        except Exception as e:
            buzzer.play("warning")
            return {"error": f"Exception while executing '{command}': {str(e)}"}

    def _wrap(self, result):
        return {
            "structured": result.__dict__ if hasattr(result, '__dict__') else str(result),
            "string": result.as_string() if hasattr(result, 'as_string') else str(result)
        }
