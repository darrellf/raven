"""Legal commands for a CommunicationMod state message.

Commands follow the mod's syntax: card indexes are 1-based, target and
potion slot indexes are 0-based, choice indexes are 0-based into
game_state.choice_list. Starting a run isn't listed here; the runner
handles START itself.
"""

EMPTY_POTION_ID = "Potion Slot"

# CommunicationMod accepts these aliases, so treat them as available too.
PROCEED_NAMES = {"proceed", "confirm"}
RETURN_NAMES = {"return", "skip", "cancel", "leave"}


def live_monster_indexes(game_state):
    """Indexes of monsters that can be targeted."""
    monsters = (game_state.get("combat_state") or {}).get("monsters", [])
    return [
        i
        for i, monster in enumerate(monsters)
        if not monster.get("is_gone")
        and not monster.get("half_dead")
        and monster.get("current_hp", 0) > 0
    ]


def has_empty_potion_slot(game_state):
    return any(p.get("id") == EMPTY_POTION_ID for p in game_state.get("potions", []))


def _card_commands(game_state):
    hand = (game_state.get("combat_state") or {}).get("hand", [])
    targets = live_monster_indexes(game_state)
    commands = []
    for i, card in enumerate(hand, start=1):
        if not card.get("is_playable"):
            continue
        if card.get("has_target"):
            commands.extend(f"PLAY {i} {t}" for t in targets)
        else:
            commands.append(f"PLAY {i}")
    return commands


def _potion_commands(game_state):
    in_combat = game_state.get("combat_state") is not None
    targets = live_monster_indexes(game_state)
    commands = []
    for slot, potion in enumerate(game_state.get("potions", [])):
        if potion.get("id") == EMPTY_POTION_ID or not potion.get("can_use"):
            continue
        if potion.get("requires_target"):
            if in_combat:
                commands.extend(f"POTION Use {slot} {t}" for t in targets)
        else:
            commands.append(f"POTION Use {slot}")
    return commands


def _choose_commands(game_state):
    commands = []
    for i, choice in enumerate(game_state.get("choice_list", [])):
        # Taking a potion with full slots silently does nothing.
        if (
            game_state.get("screen_type") == "COMBAT_REWARD"
            and str(choice).lower() == "potion"
            and not has_empty_potion_slot(game_state)
        ):
            continue
        commands.append(f"CHOOSE {i}")
    return commands


def is_grid(message):
    return (message.get("game_state") or {}).get("screen_type") == "GRID"


def is_stuck_grid_confirm(message):
    """A card grid's confirm step that the game reports as not ready.

    After a card is picked for upgrade, the confirm step comes up but
    CommunicationMod doesn't notice and keeps saying it isn't ready.
    """
    if message.get("ready_for_command") or not message.get("in_game"):
        return False
    available = {c.lower() for c in message.get("available_commands", [])}
    screen = (message.get("game_state") or {}).get("screen_state") or {}
    return is_grid(message) and bool(screen.get("confirm_up")) and bool(available & PROCEED_NAMES)


def legal_commands(message):
    """Every legal command for a state message, as strings ready to send."""
    if not message.get("in_game") or not message.get("ready_for_command"):
        return []
    available = {c.lower() for c in message.get("available_commands", [])}
    game_state = message.get("game_state") or {}

    commands = []
    if "play" in available:
        commands.extend(_card_commands(game_state))
    if "potion" in available:
        commands.extend(_potion_commands(game_state))
    if "end" in available:
        commands.append("END")
    if "choose" in available:
        commands.extend(_choose_commands(game_state))
    if available & PROCEED_NAMES:
        commands.append("PROCEED")
    # Cancelling a card grid's confirm step leaves the game stuck, never
    # ready for another command, so only confirm there.
    grid_confirm = is_grid(message) and (game_state.get("screen_state") or {}).get(
        "confirm_up"
    )
    if available & RETURN_NAMES and not grid_confirm:
        commands.append("RETURN")
    return commands


def is_legal(message, command):
    """Whether `command` is legal for `message`, ignoring case and spacing."""
    wanted = " ".join(command.split()).upper()
    return any(c.upper() == wanted for c in legal_commands(message))
