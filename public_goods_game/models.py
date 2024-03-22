from otree.api import *
import random
import itertools


class Constants(BaseConstants):
    name_in_url = "public_goods_punishment"
    players_per_group = 3
    num_rounds = 7
    num_recent_rounds_to_display = 3
    endowment = 20
    efficiency_factor = 0.375
    punishment_costs = [0, 1, 2, 4, 6, 9, 12, 16, 20, 25, 30]


class Subsession(BaseSubsession):
    def creating_session(self):
        if self.round_number == 1:
            punishment_conditions = itertools.cycle([True, False])
            for group in self.get_groups():
                # Assign the punishment condition to the group and save it in each participant's vars
                punishment_condition = next(punishment_conditions)
                print(f"Group {group.id} has{'' if punishment_condition else ' no'} punishment condition ")
                for player in group.get_players():
                    player.participant.vars["punishment_condition"] = punishment_condition


class Group(BaseGroup):
    total_group_investment = models.CurrencyField(initial=0)
    punishment_condition = models.BooleanField()

    def set_first_stage_earnings(self):
        players = self.get_players()
        self.total_group_investment = sum([p.public_investment for p in players])

        for p in players:
            p.payoff_from_private = p.endowment - p.public_investment

            p.payoff_from_public = Constants.efficiency_factor * self.total_group_investment
            p.gross_profit = p.payoff_from_private + p.payoff_from_public


class Player(BasePlayer):
    # Existing investment field
    payoff_from_private = models.CurrencyField()
    payoff_from_public = models.CurrencyField()
    endowment = models.CurrencyField(initial=Constants.endowment)
    gross_profit = models.CurrencyField(initial=0)

    public_investment = models.CurrencyField(
        min=0,
        max=Constants.endowment,
        initial=None,
        verbose_name="How much would you like to invest in the public account?",
        # Specify to use a slider widget
        widget=widgets.RadioSelect,
        choices=[i for i in range(0, Constants.endowment + 1)],
    )

    received_punishment = models.CurrencyField(initial=0)
    total_punishment_cost = models.CurrencyField(initial=0)

    def set_punishment_and_final_payoffs(self):
        # Iterate over each group member once, assigning punishment and calculating costs
        for other_player in self.get_others_in_group():
            # Assign punishment points from this player to the other player
            punishment_points = getattr(self, f"punishment_sent_to_player_{other_player.id_in_group}")
            other_player.received_punishment += punishment_points

            # Add up the cost incurred for the punishment given
            self.total_punishment_cost += Constants.punishment_costs[punishment_points]

        punishment_reduction_proportion = min(1, self.received_punishment / 10)

        final_earnings = self.gross_profit * (1 - punishment_reduction_proportion)

        final_earnings -= self.total_punishment_cost

        self.payoff = max(0, final_earnings)


for i in range(1, Constants.players_per_group + 1):
    setattr(
        Player,
        f"punishment_sent_to_player_{i}",
        models.IntegerField(min=0, max=10, initial=0, label=f"Choose punishment for player #{i}"),
    )
