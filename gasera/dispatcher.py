from .commands import GASERA_COMMANDS
from .controller import gasera
import system.log_utils as log

class GaseraCommandDispatcher:
    def handle(self, command: str, args=None) -> dict:
        args = args or []
        if command not in GASERA_COMMANDS:
            msg = f"Unknown command: {command}"
            log.warn(msg)
            return {"error": msg}
        try:
            handler = GASERA_COMMANDS[command]["handler"]
            result = handler(gasera, args)
            log.verbose(f"Executed command '{command}', result: {result}", sound = "ok")
            return self._wrap(result)
        except Exception as e:
            msg = f"Exception while executing '{command}': {str(e)}"
            log.error(msg)
            return {"error": msg}

    def _wrap(self, result):
        return {
            "structured": result.__dict__ if hasattr(result, '__dict__') else str(result),
            "string": result.as_string() if hasattr(result, 'as_string') else str(result)
        }

# Instantiate a global dispatcher
dispatcher = GaseraCommandDispatcher()
