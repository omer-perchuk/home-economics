user_states = {}


def set_user_state(user_id: str, state: dict):
    user_states[user_id] = state


def get_user_state(user_id: str):
    return user_states.get(user_id)


def clear_user_state(user_id: str):
    if user_id in user_states:
        del user_states[user_id]