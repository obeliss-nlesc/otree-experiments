
from otree.api import *
c = cu

doc = ''
class C(BaseConstants):
    NAME_IN_URL = 'EndGame'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
class Subsession(BaseSubsession):
    pass
class Group(BaseGroup):
    pass
class Player(BasePlayer):
    pass
class EndGame(Page):
    form_model = 'player'
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        participant = player.participant
        return dict(dropout = participant.has_dropped_out, group_fail = participant.too_many_inactive_in_group)


class Redirect(Page):
    pass

page_sequence = [EndGame, Redirect]