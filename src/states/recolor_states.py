from aiogram.fsm.state import State, StatesGroup


class RecolorStates(StatesGroup):
    """FSM состояния процесса настройки и перекраски."""

    # Ввод пользовательского HEX
    entering_custom_hex = State()

    # Ввод текста для замены в анимированном стикере
    entering_custom_text = State()

    # Ввод названия для стикерпака
    entering_pack_title = State()

    # Ввод short_name для стикерпака
    entering_pack_shortname = State()
