from os import environ

SESSION_CONFIGS = [
    dict(
        name="public_goods_game",
        display_name="Public goods game",
        num_demo_participants=6,
        app_sequence=["public_goods_game"],
        num_rounds=7,
    ),
    dict(
        name='DropOutTest', 
        num_demo_participants=3, 
        app_sequence=['Game', 'EndGame'])
    ]
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.01,
    participation_fee=0.00,
    doc="",
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

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

SECRET_KEY = "7790715217501"
