
from otree.api import *
c = cu

doc = ''
class C(BaseConstants):
    NAME_IN_URL = 'Game'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 10
    MIN_PLAYERS_PER_GROUP = 2
    ENDOWMENT = 100
class Subsession(BaseSubsession):
    pass
def regroup(subsession: Subsession):
    pass
class Group(BaseGroup):
    aantal_inactief = models.IntegerField(initial=0)
def end_round(group: Group):
    # I run this function at the end of each round after all the players arrived on the DecisionWait page.
    
    # Retrieve all active contributions & players
    contributions = [p.contribution for p in group.get_players() if not p.participant.has_dropped_out]
    active_players = [p for p in group.get_players() if not p.participant.has_dropped_out]
    
    # Calculate total contribution for the group
    total_contribution = round(sum(contributions) * 1.1, 2)
    
    # Set the payoff for each participant
    for p in active_players:
        payoff = (total_contribution / len(active_players)) - p.contribution
        if payoff > 0:
            # This way of assigning payoffs is redundant, as player.payoff is automatically summed each round.
            p.participant.payoff += payoff
    
        # I wanted players to be able to keep on playing, even when their budget = 0. So i give them 10. 
        if p.participant.payoff <= 0:
            p.participant.payoff += 10
    
    
    
    
class Player(BasePlayer):
    contribution = models.IntegerField()
def contribution_error_message(player: Player, value):
    participant = player.participant
    # You can ignore this, just some playing around with error messages.
    if value > participant.payoff:
        return f"Budget insufficient, your budget is {participant.payoff}"
    elif value < 0:
        return "Not allowed to enter less then 0"
    
class StartRound(Page):
    form_model = 'player'
    @staticmethod
    def is_displayed(player: Player):
        session = player.session
        subsession = player.subsession
        if subsession.round_number == 1:
            return True
    @staticmethod
    def vars_for_template(player: Player):
        session = player.session
        subsession = player.subsession
        return dict(round_number = subsession.round_number)
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        session = player.session
        subsession = player.subsession
        group = player.group
        participant = player.participant
        # Set the initial values for has_dropped_out and too_many_inactive_in_group
        participant.has_dropped_out = False
        participant.too_many_inactive_in_group = False
        
        # Give initial endowment
        if subsession.round_number == 1:
            participant.payoff = C.ENDOWMENT
class Reshuffle(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = regroup
    @staticmethod
    def is_displayed(player: Player):
        session = player.session
        subsession = player.subsession
        group = player.group
        participant = player.participant
        # I wanted to test regrouping participants, you can ignore this page and functions.
        if subsession.round_number > 1:
            return True
class Decision(Page):
    form_model = 'player'
    form_fields = ['contribution']
    timeout_seconds = 15
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        session = player.session
        subsession = player.subsession
        group = player.group
        participant = player.participant
        # Not sure if this piece of code is required, but i was worried the group value for aantal_inactief was reset after starting a new round.
        if subsession.round_number > 1:
            prev_group = group.in_round(subsession.round_number - 1)
            group.aantal_inactief  = prev_group.aantal_inactief
        
        # Set has_dropped_out value if someone times out, and add one to aantal_inactief
        if timeout_happened:
            participant.has_dropped_out = True
            group.aantal_inactief += 1
        
        
        
        
        
        
    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        group = player.group
        participant = player.participant
        # Important function: sends participants that have dropped out to the last app in the sequence.
        if participant.has_dropped_out:
            return upcoming_apps[-1] 
        
        # Sends participants that have a group below minimum group size to last app.
        elif group.aantal_inactief > (C.PLAYERS_PER_GROUP - C.MIN_PLAYERS_PER_GROUP):
            participant.too_many_inactive_in_group = True
            return upcoming_apps[-1] 
class DecisionWait(WaitPage):
    after_all_players_arrive = end_round
    title_text = 'Moment geduld'
    body_text = 'We wachten even op de rest.'

class WaitForStart(WaitPage):
    pass



class ResultsPage(Page):
    form_model = 'player'
    @staticmethod
    def is_displayed(player: Player):
        group = player.group
        participant = player.participant
        # Don't think this actually does something, as participant.too_many_inactive_in_group is set after this page.
        if not participant.too_many_inactive_in_group:
            return True
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        participant = player.participant
        return dict(contribution = cu(player.contribution), 
                    total_contributions = cu(sum([p.contribution for p in group.get_players() if not p.participant.has_dropped_out]) * 1.1),
                    total_payoff = participant.payoff)
    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        group = player.group
        participant = player.participant
        # I repeated this function here for some reason, not sure if it's required.
        if participant.has_dropped_out:
            return upcoming_apps[-1] 
        elif group.aantal_inactief > (C.PLAYERS_PER_GROUP - C.MIN_PLAYERS_PER_GROUP):
            participant.too_many_inactive_in_group = True
            return upcoming_apps[-1] 
page_sequence = [StartRound, WaitForStart, Reshuffle, Decision, DecisionWait, ResultsPage]