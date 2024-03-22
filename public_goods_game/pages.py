from otree.api import *
from .models import Constants


class IntroductionPage(Page):
    def vars_for_template(self):
        return dict(
            punishment_condition=self.player.participant.vars.get("punishment_condition"),
        )

    def is_displayed(self):
        # Show this page only on the first round
        return self.round_number == 1


class Contribution(Page):
    form_model = "player"
    form_fields = ["public_investment"]

    def before_next_page(self):
        pass

    def vars_for_template(self):
        return dict(
            round_number=self.round_number,
            endowment=Constants.endowment,
        )

    def error_message(self, values):
        if sum(values.values()) > Constants.endowment:
            return "The sum of your investments cannot exceed your endowment."


class GroupWaitPage(WaitPage):
    def after_all_players_arrive(self):
        self.group.set_first_stage_earnings()


class FirstStageResults(Page):
    def vars_for_template(self):
        return dict(
            round_number=self.round_number,
        )


class ObservationPage(Page):
    def vars_for_template(self):
        players_in_all_rounds = [player.in_all_rounds() for player in self.group.get_players()]
        current_round = self.subsession.round_number

        # Compute the first round to display (cannot be less than 1)
        first_round_to_display = max(1, current_round - Constants.num_recent_rounds_to_display + 1)
        # Construct the data structure for the table
        table_data = []
        for round_number in range(first_round_to_display, current_round + 1):
            round_data = []
            for player in players_in_all_rounds:
                public_investment = player[round_number - 1].public_investment
                private_investment = player[round_number - 1].payoff_from_private
                payoff = player[round_number - 1].gross_profit
                round_data.append([public_investment, private_investment, payoff])
            table_data.append((round_number, round_data))

        return dict(
            round_number=current_round,
            table_data=table_data,
            player_id=self.player.id_in_group,
        )

    def is_displayed(self):
        return not self.player.participant.vars.get("punishment_condition")


class PunishmentPage(Page):
    form_model = "player"

    def get_form_fields(self):
        self.other_players = [f"punishment_sent_to_player_{i.id_in_group}" for i in self.player.get_others_in_group()]

        return self.other_players

    def vars_for_template(self):
        players_in_all_rounds = [player.in_all_rounds() for player in self.group.get_players()]
        current_round = self.subsession.round_number

        # Compute the first round to display (cannot be less than 1)
        first_round_to_display = max(1, current_round - Constants.num_recent_rounds_to_display + 1)
        # Construct the data structure for the table
        table_data = []
        for round_number in range(first_round_to_display, current_round + 1):
            round_data = []
            for player in players_in_all_rounds:
                public_investment = player[round_number - 1].public_investment
                private_investment = player[round_number - 1].payoff_from_private
                payoff = player[round_number - 1].gross_profit
                round_data.append([public_investment, private_investment, payoff])
            table_data.append((round_number, round_data))

        return dict(
            round_number=current_round,
            table_data=table_data,
            player_id=self.player.id_in_group,
            players=self.other_players,
            punishment_costs=Constants.punishment_costs,
        )

    def is_displayed(self):
        return self.player.participant.vars.get("punishment_condition")

    def error_message(self, values):
        cost = sum([Constants.punishment_costs[value] for value in values.values()])

        if cost > self.player.gross_profit:  # gross_profit
            return "The total punishment cost cannot exceed your earnings."


class PunishmentWaitPage(WaitPage):
    def after_all_players_arrive(self):
        for player in self.group.get_players():
            player.set_punishment_and_final_payoffs()

    def is_displayed(self):
        return self.player.participant.vars.get("punishment_condition")


class FinalRoundResults(Page):
    def is_displayed(self):
        return self.player.participant.vars.get("punishment_condition")

    def vars_for_template(self):
        accumulated_payoff = sum(player.payoff for player in self.player.in_all_rounds())
        return dict(
            punishment_reduction_percentage=min(1, int(self.player.received_punishment) / 10) * 100,
            round_number=self.round_number,
            accumulated_payoff=accumulated_payoff,
        )


class FinalGameResults(Page):
    def is_displayed(self):
        return self.round_number == Constants.num_rounds

    def vars_for_template(self):
        player_accumulated_payoff = sum(
            (player.payoff if self.player.participant.vars.get("punishment_condition") else player.gross_profit)
            for player in self.player.in_all_rounds()
        )
        return dict(player_accumulated_payoff=player_accumulated_payoff)


page_sequence = [
    IntroductionPage,
    Contribution,
    GroupWaitPage,
    FirstStageResults,
    ObservationPage,
    PunishmentPage,
    PunishmentWaitPage,
    FinalRoundResults,
    FinalGameResults,
]
