from otree.api import *

class Constants(BaseConstants):
    """
    This class defines the constants used in the game.
    """
    name_in_url = "public_goods_game"
    title = "Test experiment"
    players_per_group = None
    num_rounds = 3
    num_recent_rounds_to_display = num_rounds
    endowment = 20
    min_payout = 5
    efficiency_factor = 0.375
    real_world_currency_per_point = 0.01
    punishment_costs = [0, 1, 2, 4, 6, 9, 12, 16, 20, 25, 30]
    min_group_participation = 0.63
    introduction_timeout_seconds = 600
    other_pages_timeout_seconds = 90

class Subsession(BaseSubsession):
    """
    This class represents a subsession of the game.
    """
    pass

def creating_session(subsession):
    """
    This function is called when creating a new session.
    It sets the 'is_dropout' attribute of each participant to False.
    """
    if subsession.round_number == 1:
        players = subsession.get_players()
        for player in players:
            player.participant.is_dropout = False

class Group(BaseGroup):
    total_group_investment = models.CurrencyField(initial=0)
    punishment_condition = models.BooleanField()
    inactive_players = models.IntegerField(initial=0)
    failed = models.BooleanField(initial=False)

    def set_first_stage_earnings(self):
        """
        This function calculates the first stage earnings for each player in the group.
        It calculates the total group investment and assigns the payoff from private and public accounts to each player.
        """
        players = self.get_players()
        self.total_group_investment = sum([p.public_investment for p in players])
        for p in players:
            p.payoff_from_private = p.endowment - p.public_investment
            p.payoff_from_public = Constants.efficiency_factor * self.total_group_investment
            p.gross_profit = p.payoff_from_private + p.payoff_from_public

    def update_accumulated_earnings(self):
        """
        This function updates players' accumulated earnings after first stage earnings are calculated.
        It retrieves the accumulated earnings of the previous round, and then adds the (gross) payoff
        of the current round.
        """
        players = self.get_players()
        for player in players:
            # Check if it's not the first round
            if player.round_number > 1:
                previous_round = player.in_round(player.round_number - 1)
                previous_accumulation = previous_round.accumulated_earnings
            # If it's the first round, start with zero
            else:
                previous_accumulation = 0
            player.accumulated_earnings = previous_accumulation + player.gross_profit

class Player(BasePlayer):
    accumulated_earnings = models.CurrencyField(initial=0)
    payoff_from_private = models.CurrencyField()
    payoff_from_public = models.CurrencyField()
    endowment = models.CurrencyField(initial=Constants.endowment)
    gross_profit = models.CurrencyField(initial=0)
    public_investment = models.CurrencyField(
        min=0,
        max=Constants.endowment,
        initial=0,
        verbose_name="Hoe veel wil je inleggen in het fonds?",
        widget=widgets.RadioSelect,
        choices=[i for i in range(0, Constants.endowment + 1)],
    )
    received_punishment = models.CurrencyField(initial=0)
    total_punishment_cost = models.CurrencyField(initial=0)
    inactive = models.BooleanField(initial=False)

    def set_punishment_and_final_payoffs(self):
        """
        This function calculates the final payoffs for the player (self) this round.
        It retrieves all punishment points received, computes the total cost of giving punishments, and
        calculates the proportion of gross payoff reduction due to incurred punishment.
        Final (net) earnings are determined by subtracting the punishment reduction proportion from the gross payoff,
        ensuring that the result is non-negative.
        """
        self.received_punishment = sum(
            getattr(other_player, f"punishment_sent_to_player_{self.id_in_group}", 0)
            for other_player in self.get_others_in_group()
        )
        for other_player in self.get_others_in_group():
            punishment_points = getattr(self, f"punishment_sent_to_player_{other_player.id_in_group}")
            self.total_punishment_cost += Constants.punishment_costs[int(punishment_points)]
        punishment_reduction_proportion = min(1, int(str(self.received_punishment).split()[0]) / 10)
        final_earnings = self.gross_profit * (1 - punishment_reduction_proportion)
        self.payoff = max(0, final_earnings)

    def update_accumulated_earnings_after_punishment_expenses(self):
        """
        This function updates the player's accumulated earnings considering the net earnings
        (i.e., gross profit minus incurred punishment) and punishment given. Again, accumulated earnings
        cannot be negative.
        """
        self.accumulated_earnings -= self.gross_profit
        self.accumulated_earnings += self.payoff
        self.accumulated_earnings -= self.total_punishment_cost
        self.accumulated_earnings = max(0, self.accumulated_earnings)

# Setting punishment_fields in the Player class.
max_group_size = 30 # Adjust such that it matches the group size of the large group condition
for i in range(1, max_group_size + 1):
    setattr(
        Player,
        f"punishment_sent_to_player_{i}",
        models.CurrencyField(
            initial=0,
            verbose_name=f"Kies een straf voor speler #{i}:",
            choices=[(value, f"{value} strafpunten") for value in range(11)],
        ),
    )

def timeout_check(player, timeout_happened):
    """
    This function checks if a timeout has occurred for a player.
    If a timeout has occurred and the participant is not a dropout, it marks the player as inactive and sets the
    participant as a dropout. If the number of inactive players reaches the minimum required number
    (i.e., proportion of group size), it marks the group as failed.
    """
    participant = player.participant
    groupsize = len(player.get_others_in_group()) + 1

    if timeout_happened and not participant.is_dropout:
        player.group.inactive_players += 1
        player.inactive = True # in order to check the status of players over rounds
        participant.is_dropout = True

    if groupsize - player.group.inactive_players < round(groupsize * Constants.min_group_participation):
        player.group.failed = True

def timeout_time(player, timeout_seconds):
    """
    This function calculates the timeout time for a player.
    If the participant is a dropout or the group has failed, it returns an instant timeout of 1 second.
    Otherwise, it returns the specified timeout_seconds.

    Args:
        player (Player): The player for whom to calculate the timeout time.
        timeout_seconds (int): The timeout duration in seconds.

    Returns:
        int: The calculated timeout time in seconds.
    """
    participant = player.participant
    if participant.is_dropout or player.group.failed:
        return 1  # instant timeout, 1 second
    else:
        return timeout_seconds

class IntroductionPage(Page):
    """
    This class represents the introduction page of the game.
    """
    def vars_for_template(player):
        """
        This function provides the template variables for the introduction page.
        It returns the punishment condition from the session configuration.

        Args:
            player (Player): The player for whom to provide the template variables.

        Returns:
            dict: The template variables.
        """
        return dict(
            punishment_condition=player.session.config.get("punishment_condition"),
            groupsize=player.session.config.get("num_demo_participants")
        )

    def is_displayed(player):
        """
        This function determines whether the introduction page should be displayed.
        It returns True if it is the first round, False otherwise.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        # Show this page only on the first round
        return player.round_number == 1

    def get_timeout_seconds(player):
        """
        This function calculates the timeout time for the introduction page.
        If the participant is a dropout or the group has failed, it returns an instant timeout of 1 second.
        Otherwise, it returns the specified introduction timeout seconds.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.introduction_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        This function is called before moving to the next page.
        It checks if a timeout has occurred and updates the player's status accordingly.

        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)

class Contribution(Page):
    """
    This class represents the contribution page of the game.
    """
    form_model = "player"
    form_fields = ["public_investment"]

    def vars_for_template(player):
        """
        This function provides the template variables for the contribution page.
        It returns the round number and the endowment from the Constants class.

        Args:
            player (Player): The player for whom to provide the template variables.

        Returns:
            dict: The template variables.
        """
        return dict(
            round_number=player.round_number,
            endowment=Constants.endowment,
        )

    def error_message(player, values):
        """
        This function checks if there is an error in the submitted form values.
        It returns an error message if the sum of the investments exceeds the endowment.

        Args:
            player (Player): The player for whom to check the form values.
            values (dict): The submitted form values.

        Returns:
            str: The error message, or None if there is no error.
        """
        if sum(values.values()) > Constants.endowment:
            return "Je totale inleg kan niet groter zijn dan je startkapitaal."

    def get_timeout_seconds(player):
        """
        This function calculates the timeout time for the contribution page.
        If the participant is a dropout or the group has failed, it returns an instant timeout of 1 second.
        Otherwise, it returns the specified other pages timeout seconds.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        This function is called before moving to the next page.
        It checks if a timeout has occurred and updates the player's status accordingly.

        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)

    def is_displayed(player):
        """
        This function determines whether the contribution page should be displayed.
        It returns True if the group has not failed and the participant is not a dropout, False otherwise.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        return not player.group.failed and not player.participant.is_dropout

class GroupWaitPage(WaitPage):
    def after_all_players_arrive(group):
        """
        This function is called after all players in the group have arrived.
        It sets the first stage earnings for the group.
        And it updates players' accumulated earnings.

        Args:
            group (Group): The group for which to call the functions.
        """
        group.set_first_stage_earnings()
        group.update_accumulated_earnings()

    def is_displayed(player):
        """
        This function determines whether the group wait page should be displayed.
        It returns True if the group has not failed and the participant is not a dropout, False otherwise.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        return not player.group.failed and not player.participant.is_dropout

class FirstStageResults(Page):
    """
    This class represents the first stage results page of the game.
    """
    def vars_for_template(player):
        """
        This function provides the template variables for the first stage results page.

        Args:
            player (Player): The player for whom to provide the template variables.

        Returns:
            dict: The template variables.
        """
        return dict(
            round_number=player.round_number,
        )

    def get_timeout_seconds(player):
        """
        This function calculates the timeout time for the first stage results page.
        If the participant is a dropout or the group has failed, it returns an instant timeout of 1 second.
        Otherwise, it returns the specified other pages timeout seconds.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        This function is called before moving to the next page.
        It checks if a timeout has occurred and updates the player's status accordingly.

        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)

    def is_displayed(player):
        """
        This function determines whether the first stage results page should be displayed.
        It returns True if the group has not failed and the participant is not a dropout, False otherwise.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        return not player.group.failed and not player.participant.is_dropout

class ObservationPage(Page):
    """
    This class represents the observation page of the game.
    """
    def vars_for_template(player):
        """
        This function provides the variables needed for rendering the template of the observation page.

        Args:
            player (Player): The player for whom to provide the variables.

        Returns:
            dict: A dictionary containing the variables needed for rendering the template.
        """
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
                dropout = players[round_number - 1].participant.is_dropout
                round_data.append([public_investment, private_investment, payoff, dropout])
            table_data.append((round_number, round_data))

            # Also in descending order; for the table generator script on the observation/punishment page template
            reversed_table_data = list(reversed(table_data))

        return dict(
            round_number=current_round,
            table_data=table_data,
            reversed_table_data=reversed_table_data,
            player_id=player.id_in_group,
        )

    def is_displayed(player):
        """
        This function determines whether the observation page should be displayed.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        return (
            not player.session.config.get("punishment_condition")
            and not player.group.failed
            and not player.participant.is_dropout
        )

    def get_timeout_seconds(player):
        """
        This function calculates the timeout time for the observation page.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        This function is called before moving to the next page.
        It checks if a timeout has occurred and updates the player's status accordingly.

        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)

class PunishmentPage(Page):
    """
    This class represents the punishment page of the game.
    """
    form_model = "player"

    def get_form_fields(player):
        """
        This function returns the form fields for the punishment page.
        It dynamically generates the form fields based on the number of other players in the group.

        Args:
            player (Player): The player for whom to generate the form fields.

        Returns:
            list: The list of form fields for the punishment page.
        """
        other_players = [f"punishment_sent_to_player_{i.id_in_group}" for i in player.get_others_in_group()]
        return other_players

    def vars_for_template(player):
        """
        This function returns the variables for the punishment page template.
        It computes the data structure for the table displaying previous rounds' data.

        Args:
            player (Player): The player for whom to compute the variables.

        Returns:
            dict: The variables for the punishment page template.
        """
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
                dropout = players[round_number - 1].participant.is_dropout
                round_data.append([public_investment, private_investment, payoff, dropout])
            table_data.append((round_number, round_data))

        other_players = [f"punishment_sent_to_player_{i.id_in_group}" for i in player.get_others_in_group()]
        most_recent_round = table_data[-1][0] if table_data else None #punishment column for most recent round

        other_rounds = [data for data in table_data if data[0] != most_recent_round]
        other_rounds.reverse() # Order of previous rounds in descending order.

        return dict(
            round_number=current_round,
            table_data=table_data,
            player_id=player.id_in_group,
            players=other_players,
            punishment_costs=Constants.punishment_costs,
            most_recent_round=most_recent_round,
            other_rounds=other_rounds,
            accumulated_earnings=player.accumulated_earnings,
        )

    def is_displayed(player):
        """
        This function determines whether the punishment page should be displayed for a player.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the punishment page should be displayed, False otherwise.
        """
        return (
            player.session.config.get("punishment_condition")
            and not player.group.failed
            and not player.participant.is_dropout
        )

    def error_message(player, values):
        """
        This function returns an error message if the total punishment cost exceeds the
        **accumulated** player's earnings.

        Args:
            player (Player): The player for whom to check the punishment cost.
            values (dict): The values of the punishment form fields.

        Returns:
            str: The error message if the punishment cost exceeds the earnings, None otherwise.
        """
        cost = sum([Constants.punishment_costs[int(value)] for value in values.values()])

        if cost > player.accumulated_earnings:
            return "De totale kosten voor het geven van strafpunten kunnen niet hoger zijn dan je opgebouwde winst."

    def get_timeout_seconds(player):
        """
        This function calculates the timeout time for the punishment page.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        This function is called before moving to the next page.
        It checks if a timeout has occurred and updates the player's status accordingly.

        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)

class PunishmentWaitPage(WaitPage):
    def after_all_players_arrive(group):
        """
        This function is called after all players in the group have arrived.
        It sets the punishment and final payoffs for each player in the group.
        """
        for player in group.get_players():
            player.set_punishment_and_final_payoffs()
            player.update_accumulated_earnings_after_punishment_expenses()

    def is_displayed(player):
        """
        This function determines whether the punishment wait page should be displayed for a player.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the punishment wait page should be displayed, False otherwise.
        """
        return (
                player.session.config.get("punishment_condition")
                and not player.group.failed
                and not player.participant.is_dropout
        )

class FinalRoundResults(Page):
    """
    This class represents the final round results page of the game.
    """
    def is_displayed(player):
        """
        Determines whether the final round results page should be displayed for a player.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the final round results page should be displayed, False otherwise.
        """
        return (
                player.session.config.get("punishment_condition")
                and not player.group.failed
                and not player.participant.is_dropout
        )

    def vars_for_template(player):
        """
        Provides the variables for the template of the final round results page.

        Args:
            player (Player): The player for whom to provide the variables.

        Returns:
            dict: The variables for the template.players.payoff for players
        """

        return dict(
            punishment_reduction_percentage=min(1, int(player.received_punishment) / 10) * 100,
            round_number=player.round_number,
            accumulated_payoff=player.accumulated_earnings
        )

    def get_timeout_seconds(player):
        """
        Calculates the timeout time for the final round results page.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        Performs actions before moving to the next page.

        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)

class FinalGameResults(Page):
    """
    This class represents the final game results page of the game.
    """
    def is_displayed(player):
        """
        Determines whether the final game results page should be displayed for a player.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the final game results page should be displayed, False otherwise.
        """
        return (
            player.round_number == Constants.num_rounds
            and not player.group.failed
            and not player.participant.is_dropout
        )

    def vars_for_template(player):
        """
        Provides the variables for the template of the final game results page.

        Args:
            player (Player): The player for whom to provide the variables.

        Returns:
            dict: The variables for the template.
        """

        final_result = player.accumulated_earnings
        return dict(player_accumulated_payoff=final_result)

class FailedGamePage(Page):
    """
    This class represents the failed game page of the game.
    """
    def vars_for_template(player):
        """
        Provides the variables for the template of the failed game page.

        Args:
            player (Player): The player for whom to provide the variables.

        Returns:
            dict: The variables for the template.
        """
        return dict(one_dropout=player.participant.is_dropout and player.round_number == Constants.num_rounds)

    def is_displayed(player):
        """
        Determines whether the failed game page should be displayed for a player.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the failed game page should be displayed, False otherwise.
        """
        return player.group.failed or (player.participant.is_dropout and player.round_number == Constants.num_rounds)

# Page sequence
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
    FailedGamePage,
]