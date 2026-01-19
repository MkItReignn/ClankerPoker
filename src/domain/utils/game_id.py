"""Game ID generation utility."""

import uuid


def generate_game_id() -> str:
    """Generate a unique game ID.

    Returns:
        Game ID in format: game-{8 hex chars}
        Example: game-a1b2c3d4
    """
    return f"game-{uuid.uuid4().hex[:8]}"
