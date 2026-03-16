"""Application lifecycle — startup and shutdown hooks.

All heavy initialisation happens here, not at import time.
"""

from __future__ import annotations

from dotenv import load_dotenv


def startup() -> None:
    """Run once when the application starts.

    Order matters:
    1. Load .env (must happen before google-adk / google-genai imports)
    2. Setup logging
    3. Load config & validate
    4. Create agent + KB
    5. Initialise agent service
    """
    # 1. Environment
    load_dotenv(override=True)

    # 2. Logging
    from app.core.logging import setup_logging
    setup_logging()

    # 3. Config validation
    from app.core.config import settings
    settings.validate_live_audio()

    # 4. Agent
    from app.agents.patient_agent import create_agent
    agent, _kb = create_agent()

    # 5. Agent service
    from app.services.agent_service import init as init_agent_service
    init_agent_service(agent)
