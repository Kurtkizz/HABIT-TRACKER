import os
import sys

import loader


def go():
    d = loader.updates_dir()
    live = loader._live_ok(["service_main.py", "engine.py"])
    if live:
        sys.path.insert(0, d)
    try:
        import service_main
        service_main.main()
    except Exception:
        if not live:
            raise
        if d in sys.path:
            sys.path.remove(d)
        for m in ("service_main", "engine", "notifier", "runtrack"):
            sys.modules.pop(m, None)
        import service_main
        service_main.main()


go()
