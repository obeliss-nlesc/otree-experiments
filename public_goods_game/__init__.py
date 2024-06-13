from otree.api import *


class Constants(BaseConstants):
    name_in_url = "public_goods_punishment"
    players_per_group = 4
    num_rounds = 2
    num_recent_rounds_to_display = 3
    endowment = 20
    efficiency_factor = 0.375
    punishment_costs = [0, 1, 2, 4, 6, 9, 12, 16, 20, 25, 30]
    min_players_per_group = 2
    introduction_timeout_seconds = 900  # 15 minutes
    other_pages_timeout_seconds = 120  # 2 minutes
    return_from_timeout_seconds = 10


class Subsession(BaseSubsession):
    pass


def creating_session(subsession):
    if subsession.round_number == 1:
        players = subsession.get_players()
        for player in players:
            player.participant.is_dropout = False


class Group(BaseGroup):
    total_group_investment = models.CurrencyField(initial=0)
    punishment_condition = models.BooleanField()
    number_of_inactive = models.IntegerField(initial=0)
    inactive_players = models.IntegerField(initial=0)
    failed = models.BooleanField(initial=False)

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
        initial=0,
        verbose_name="How much would you like to invest in the public account?",
        widget=widgets.RadioSelect,
        choices=[i for i in range(0, Constants.endowment + 1)],
    )

    received_punishment = models.CurrencyField(initial=0)
    total_punishment_cost = models.CurrencyField(initial=0)

    def set_punishment_and_final_payoffs(self):
        # Iterate over each group member once, assigning punishment and calculating costs
        for other_player in self.get_others_in_group():
            # Assign punishment points from this player to the other player
            punishment_points = int(getattr(self, f"punishment_sent_to_player_{other_player.id_in_group}"))
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
        models.CurrencyField(
            initial=0,
            verbose_name=f"Choose a punishment for player #{i}:",
            widget=widgets.RadioSelect,
            choices=[0, 5, 10],
        ),
    )


def timeout_check(player, timeout_happened):
    participant = player.participant

    if timeout_happened and not participant.is_dropout:
        player.group.inactive_players += 1
        participant.is_dropout = True

    if player.group.inactive_players == Constants.players_per_group - Constants.min_players_per_group:
        player.group.failed = True


def timeout_time(player, timeout_seconds):
    participant = player.participant

    if participant.is_dropout or player.group.failed:
        return 1  # instant timeout, 1 second
    else:
        return timeout_seconds


class IntroductionPage(Page):
    def vars_for_template(player):
        return dict(
            punishment_condition=player.session.config.get("punishment_condition"),
        )

    def is_displayed(player):
        # Show this page only on the first round
        return player.round_number == 1

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.introduction_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)


class Contribution(Page):
    form_model = "player"
    form_fields = ["public_investment"]

    def vars_for_template(player):
        return dict(
            round_number=player.round_number,
            endowment=Constants.endowment,
        )

    def error_message(player, values):
        if sum(values.values()) > Constants.endowment:
            return "The sum of your investments cannot exceed your endowment."

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)

    def is_displayed(player):
        return not player.group.failed and not player.participant.is_dropout


class GroupWaitPage(WaitPage):
    def after_all_players_arrive(group):
        group.set_first_stage_earnings()

    def is_displayed(player):
        return not player.group.failed and not player.participant.is_dropout


class FirstStageResults(Page):

    def vars_for_template(player):
        return dict(
            round_number=player.round_number,
        )

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)

    def is_displayed(player):
        return not player.group.failed and not player.participant.is_dropout


class ObservationPage(Page):

    def vars_for_template(player):
        players_in_all_rounds = [players.in_all_rounds() for players in player.group.get_players()]
        current_round = player.round_number

        # Compute the first round to display (cannot be less than 1)
        first_round_to_display = max(1, current_round - Constants.num_recent_rounds_to_display + 1)
        # Construct the data structure for the table
        table_data = []
        for round_number in range(first_round_to_display, current_round + 1):
            round_data = []
            for players in players_in_all_rounds:
                public_investment = players[round_number - 1].public_investment
                private_investment = players[round_number - 1].payoff_from_private
                payoff = players[round_number - 1].gross_profit
                round_data.append([public_investment, private_investment, payoff])
            table_data.append((round_number, round_data))

        return dict(
            round_number=current_round,
            table_data=table_data,
            player_id=player.id_in_group,
        )

    def is_displayed(player):
        return (
            not player.session.config.get("punishment_condition")
            and not player.group.failed
            and not player.participant.is_dropout
        )

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)


class PunishmentPage(Page):
    form_model = "player"

    def get_form_fields(player):
        other_players = [f"punishment_sent_to_player_{i.id_in_group}" for i in player.get_others_in_group()]

        return other_players

    def vars_for_template(player):
        players_in_all_rounds = [player.in_all_rounds() for player in player.group.get_players()]
        current_round = player.round_number

        # Compute the first round to display (cannot be less than 1)
        first_round_to_display = max(1, current_round - Constants.num_recent_rounds_to_display + 1)
        # Construct the data structure for the table
        table_data = []
        for round_number in range(first_round_to_display, current_round + 1):
            round_data = []
            for players in players_in_all_rounds:
                public_investment = players[round_number - 1].public_investment
                private_investment = players[round_number - 1].payoff_from_private
                payoff = players[round_number - 1].gross_profit
                round_data.append([public_investment, private_investment, payoff])
            table_data.append((round_number, round_data))
        other_players = [f"punishment_sent_to_player_{i.id_in_group}" for i in player.get_others_in_group()]
        return dict(
            round_number=current_round,
            table_data=table_data,
            player_id=player.id_in_group,
            players=other_players,
            punishment_costs=Constants.punishment_costs,
        )

    def is_displayed(player):
        return (
            player.session.config.get("punishment_condition")
            and not player.group.failed
            and not player.participant.is_dropout
        )

    def error_message(player, values):
        cost = sum([Constants.punishment_costs[int(value)] for value in values.values()])

        if cost > player.gross_profit:  # gross_profit
            return "The total punishment cost cannot exceed your earnings."

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)


class PunishmentWaitPage(WaitPage):
    def after_all_players_arrive(group):
        for player in group.get_players():
            player.set_punishment_and_final_payoffs()

    def is_displayed(player):
        return (
            player.session.config.get("punishment_condition")
            and not player.group.failed
            and not player.participant.is_dropout
        )


class FinalRoundResults(Page):

    def is_displayed(player):
        return (
            player.session.config.get("punishment_condition")
            and not player.group.failed
            and not player.participant.is_dropout
        )

    def vars_for_template(player):
        accumulated_payoff = sum(players.payoff for players in player.in_all_rounds())
        return dict(
            punishment_reduction_percentage=min(1, int(player.received_punishment) / 10) * 100,
            round_number=player.round_number,
            accumulated_payoff=accumulated_payoff,
        )

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)


class FinalGameResults(Page):
    def is_displayed(player):
        return (
            player.round_number == Constants.num_rounds
            and not player.group.failed
            and not player.participant.is_dropout
        )

    def vars_for_template(player):
        player_accumulated_payoff = sum(
            (players.payoff if player.session.config.get("punishment_condition") else players.gross_profit)
            for players in player.in_all_rounds()
        )
        return dict(player_accumulated_payoff=player_accumulated_payoff)


class TimeoutPlayerPage(Page):

    def is_displayed(player):
        return player.participant.is_dropout and not player.group.failed

    def before_next_page(player, timeout_happened):
        if not timeout_happened:
            player.participant.is_dropout = False

    def get_timeout_seconds(player):
        return Constants.return_from_timeout_seconds


class FailedGamePage(Page):
    def vars_for_template(player):
        return dict(one_dropout=player.participant.is_dropout and player.round_number == Constants.num_rounds)

    def is_displayed(player):
        return player.group.failed or (player.participant.is_dropout and player.round_number == Constants.num_rounds)


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
    TimeoutPlayerPage,
    FailedGamePage,
]
