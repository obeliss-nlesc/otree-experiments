from os import environ

SESSION_CONFIGS = [
    dict(
        name="public_goods_game_1",
        display_name="Public goods game: with punishment condition",
        num_demo_participants=4,
        app_sequence=["public_goods_game"],
        num_rounds=2,
        punishment_condition=True,
    ),
    dict(
        name="public_goods_game_2",
        display_name="Public goods game: without punishment condition",
        num_demo_participants=4,
        app_sequence=["public_goods_game"],
        num_rounds=2,
        punishment_condition=False,
    ),
    dict(
        name='DropOutTest', 
        num_demo_participants=3, 
        app_sequence=['Game', 'EndGame']
        )
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.01,
    participation_fee=0.00,
    doc="",
)

PARTICIPANT_FIELDS = ["is_dropout", 'has_dropped_out', 'too_many_inactive_in_group', 'guesses', 'choices', 'lobby_id']

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = "en"

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = "USD"
USE_POINTS = True

ADMIN_USERNAME = "admin"
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get("OTREE_ADMIN_PASSWORD")

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = "blablaa"

