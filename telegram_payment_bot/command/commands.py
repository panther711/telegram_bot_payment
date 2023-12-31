# Copyright (c) 2021 Emanuele Bellocchia
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

#
# Imports
#
from typing import Any, Callable

from telegram_payment_bot._version import __version__
from telegram_payment_bot.auth_user.authorized_users_list import AuthorizedUsersList
from telegram_payment_bot.bot.bot_config_types import BotConfigTypes
from telegram_payment_bot.command.command_base import CommandBase
from telegram_payment_bot.command.command_data import CommandParameterError
from telegram_payment_bot.email.smtp_emailer import SmtpEmailerError
from telegram_payment_bot.member.members_kicker import MembersKicker
from telegram_payment_bot.member.members_payment_getter import MembersPaymentGetter
from telegram_payment_bot.member.members_username_getter import MembersUsernameGetter
from telegram_payment_bot.misc.chat_members import ChatMembersGetter, ChatMembersList
from telegram_payment_bot.misc.helpers import ChatHelper, UserHelper
from telegram_payment_bot.payment.payments_check_scheduler import (
    PaymentsCheckJobAlreadyRunningError, PaymentsCheckJobChatAlreadyPresentError, PaymentsCheckJobChatNotPresentError,
    PaymentsCheckJobInvalidPeriodError, PaymentsCheckJobNotRunningError
)
from telegram_payment_bot.payment.payments_data import PaymentErrorTypes
from telegram_payment_bot.payment.payments_emailer import PaymentsEmailer
from telegram_payment_bot.payment.payments_loader_factory import PaymentsLoaderFactory


#
# Decorators
#

# Decorator for group-only commands
def GroupChatOnly(exec_cmd_fct: Callable[..., None]) -> Callable[..., None]:
    def decorated(self,
                  **kwargs: Any):
        # Check if private chat
        if self._IsPrivateChat():
            self._SendMessage(self.translator.GetSentence("GROUP_ONLY_ERR_MSG"))
        else:
            exec_cmd_fct(self, **kwargs)

    return decorated


#
# Classes
#

#
# Command for getting help
#
class HelpCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        self._SendMessage(
            self.translator.GetSentence("HELP_CMD",
                                        name=UserHelper.GetName(self.cmd_data.User()))
        )


#
# Command for checking if bot is alive
#
class AliveCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        self._SendMessage(self.translator.GetSentence("ALIVE_CMD"))


#
# Command for setting test mode
#
class SetTestModeCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        try:
            # Get parameters
            flag = self.cmd_data.Params().GetAsBool(0)
        except CommandParameterError:
            self._SendMessage(self.translator.GetSentence("PARAM_ERR_MSG"))
        else:
            # Set test mode
            self.config.SetValue(BotConfigTypes.APP_TEST_MODE, flag)

            # Send message
            if self.config.GetValue(BotConfigTypes.APP_TEST_MODE):
                self._SendMessage(self.translator.GetSentence("SET_TEST_MODE_EN_CMD"))
            else:
                self._SendMessage(self.translator.GetSentence("SET_TEST_MODE_DIS_CMD"))


#
# Command for checking if test mode
#
class IsTestModeCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        if self.config.GetValue(BotConfigTypes.APP_TEST_MODE):
            self._SendMessage(self.translator.GetSentence("IS_TEST_MODE_EN_CMD"))
        else:
            self._SendMessage(self.translator.GetSentence("IS_TEST_MODE_DIS_CMD"))


#
# Command for getting authorized users
#
class AuthUsersCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        self._SendMessage(
            self.translator.GetSentence("AUTH_USERS_CMD",
                                        auth_users_list=str(AuthorizedUsersList(self.config)))
        )


#
# Command for getting chat information
#
class ChatInfoCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        self._SendMessage(
            self.translator.GetSentence("CHAT_INFO_CMD",
                                        chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()),
                                        chat_type=self.cmd_data.Chat().type,
                                        chat_id=self.cmd_data.Chat().id)
        )


#
# Command for getting the users list
#
class UsersListCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        # Get chat members
        chat_members = ChatMembersGetter(self.client).GetAll(self.cmd_data.Chat())
        # Send message
        self._SendMessage(
            self.translator.GetSentence("USERS_LIST_CMD",
                                        chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()),
                                        members_count=chat_members.Count(),
                                        members_list=str(chat_members))
        )


#
# Command for generating a new invite link
#
class InviteLinkCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        self._NewInviteLink()


#
# Command for showing bot version
#
class VersionCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        self._SendMessage(
            self.translator.GetSentence("VERSION_CMD",
                                        version=__version__)
        )


#
# Command for checking users with no username
#
class CheckNoUsernameCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        # Get chat members
        chat_members = MembersUsernameGetter(self.client, self.config).GetAllWithNoUsername(self.cmd_data.Chat())

        # Build message
        if chat_members.Any():
            # Get parameter
            left_hours = self.cmd_data.Params().GetAsInt(0, 0)

            msg = self.translator.GetSentence("CHECK_NO_USERNAME_NOTICE_CMD",
                                              chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()),
                                              members_count=chat_members.Count(),
                                              members_list=str(chat_members),
                                              hours_left=self.__HoursToStr(left_hours))

            # Add contact information if any
            support_email = self.config.GetValue(BotConfigTypes.SUPPORT_EMAIL)
            support_tg = self.config.GetValue(BotConfigTypes.SUPPORT_TELEGRAM)
            if support_email != "" and support_tg != "":
                msg += self.translator.GetSentence("CHECK_NO_USERNAME_EMAIL_TG_CMD",
                                                   support_email=support_email,
                                                   support_telegram=support_tg)
            elif support_email != "":
                msg += self.translator.GetSentence("CHECK_NO_USERNAME_ONLY_EMAIL_CMD",
                                                   support_email=support_email)
            elif support_tg != "":
                msg += self.translator.GetSentence("CHECK_NO_USERNAME_ONLY_TG_CMD",
                                                   support_telegram=support_tg)
        else:
            msg = self.translator.GetSentence("CHECK_NO_USERNAME_ALL_OK_CMD",
                                              chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()))

        # Send message
        self._SendMessage(msg)

    # Get time string
    def __HoursToStr(self,
                     hours: int) -> str:
        if hours > 47:
            hours_str = self.translator.GetSentence("WITHIN_DAYS_MSG",
                                                    days=hours // 24)
        elif hours > 1:
            hours_str = self.translator.GetSentence("WITHIN_HOURS_MSG",
                                                    hours=hours)
        else:
            hours_str = self.translator.GetSentence("ASAP_MSG")
        return hours_str


#
# Command for removing users with no username
#
class RemoveNoUsernameCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        # Notice before removing
        self._SendMessage(
            self.translator.GetSentence("REMOVE_NO_USERNAME_NOTICE_CMD",
                                        chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()))
        )

        finished = False
        kicked_members = ChatMembersList()
        # Continue until all members have been kicked
        # Useful in channels when at maximum 200 members can be kicked at once
        while not finished:
            curr_kicked_members = MembersKicker(self.client,
                                                self.config,
                                                self.logger).KickAllWithNoUsername(self.cmd_data.Chat())
            if curr_kicked_members.Any():
                kicked_members.AddMultiple(curr_kicked_members)
                # Stop if test mode to avoid infinite looping (members are not really kicked in test mode)
                finished = self.config.GetValue(BotConfigTypes.APP_TEST_MODE)
            else:
                finished = True

        # Build message
        msg = self.translator.GetSentence("REMOVE_NO_USERNAME_COMPLETED_CMD",
                                          members_count=kicked_members.Count())
        if kicked_members.Any():
            msg += self.translator.GetSentence("REMOVE_NO_USERNAME_LIST_CMD",
                                               members_list=str(kicked_members))

        # Send message
        self._SendMessage(msg)
        # Generate new invite link if necessary
        if kicked_members.Any():
            self._NewInviteLink()


#
# Command for setting payment check on joined members
#
class SetCheckPaymentsOnJoinCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        try:
            # Get parameters
            flag = self.cmd_data.Params().GetAsBool(0)
        except CommandParameterError:
            self._SendMessage(self.translator.GetSentence("PARAM_ERR_MSG"))
        else:
            # Set test mode
            self.config.SetValue(BotConfigTypes.PAYMENT_CHECK_ON_JOIN, flag)

            # Send message
            if self.config.GetValue(BotConfigTypes.PAYMENT_CHECK_ON_JOIN):
                self._SendMessage(self.translator.GetSentence("SET_CHECK_PAYMENT_ON_JOIN_EN_CMD"))
            else:
                self._SendMessage(self.translator.GetSentence("SET_CHECK_PAYMENT_ON_JOIN_DIS_CMD"))


#
# Command for checking if payment check on joined members
#
class IsCheckPaymentsOnJoinCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        if self.config.GetValue(BotConfigTypes.PAYMENT_CHECK_ON_JOIN):
            self._SendMessage(self.translator.GetSentence("IS_CHECK_PAYMENT_ON_JOIN_EN_CMD"))
        else:
            self._SendMessage(self.translator.GetSentence("IS_CHECK_PAYMENT_ON_JOIN_DIS_CMD"))


#
# Command for checking payments data for errors
#
class CheckPaymentsDataCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        self._SendMessage(self.translator.GetSentence("CHECK_PAYMENTS_DATA_NOTICE_CMD"))

        # Check payments data
        payments_loader = PaymentsLoaderFactory(self.config, self.logger).CreateLoader()
        payments_data_err = payments_loader.CheckForErrors()

        # Check results
        if payments_data_err.Any():
            msg = self.translator.GetSentence("CHECK_PAYMENTS_DATA_COMPLETED_CMD",
                                              errors_count=payments_data_err.Count())

            for payment_err in payments_data_err:
                if payment_err.Type() == PaymentErrorTypes.DUPLICATED_DATA_ERR:
                    msg += self.translator.GetSentence("CHECK_PAYMENTS_DATA_DUPLICATED_ERR_CMD",
                                                       row_index=payment_err.Row())
                elif payment_err.Type() == PaymentErrorTypes.INVALID_DATE_ERR:
                    msg += self.translator.GetSentence("CHECK_PAYMENTS_DATA_DATE_ERR_CMD",
                                                       user=payment_err.User(),
                                                       row_index=payment_err.Row(),
                                                       expiration_date=payment_err.ExpirationDate())
        else:
            msg = self.translator.GetSentence("CHECK_PAYMENTS_DATA_ALL_OK_CMD")

        # Send message
        self._SendMessage(msg)


#
# Command for sending email to users with no payment
#
class EmailNoPaymentCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        if not self.config.GetValue(BotConfigTypes.EMAIL_ENABLED):
            msg = self.translator.GetSentence("EMAIL_NO_PAYMENT_DISABLED_CMD")
        else:
            # Get parameter
            days_left = self.cmd_data.Params().GetAsInt(0, 0)

            # Notice before notifying
            self._SendMessage(
                self.translator.GetSentence("EMAIL_NO_PAYMENT_NOTICE_CMD",
                                            chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()))
            )

            try:
                # Get expired payments
                expired_payments = PaymentsEmailer(self.client,
                                                   self.config,
                                                   self.logger).EmailAllWithExpiringPayment(days_left)

                # Build message
                if expired_payments.Any():
                    # Build strings for easier reading
                    days_left_str = (self.translator.GetSentence("IN_DAYS_MSG", days=days_left)
                                     if days_left > 1 else
                                     (self.translator.GetSentence("TOMORROW_MSG")
                                      if days_left == 1 else
                                      self.translator.GetSentence("TODAY_MSG")))

                    msg = self.translator.GetSentence("EMAIL_NO_PAYMENT_COMPLETED_CMD",
                                                      days_left=days_left_str,
                                                      members_count=expired_payments.Count(),
                                                      members_list=str(expired_payments))
                else:
                    msg = self.translator.GetSentence("EMAIL_NO_PAYMENT_ALL_OK_CMD")
            except SmtpEmailerError:
                self.logger.GetLogger().exception("Error while sending email to no payment members")
                msg = self.translator.GetSentence("EMAIL_NO_PAYMENT_ERR_CMD")

        # Send message
        self._SendMessage(msg)


#
# Command for checking users with no payment
#
class CheckNoPaymentCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        # Get parameters
        days_left = self.cmd_data.Params().GetAsInt(0, 0)
        last_day = self.cmd_data.Params().GetAsInt(1, 0)

        # Notice before checking
        self._SendMessage(
            self.translator.GetSentence("CHECK_NO_PAYMENT_NOTICE_CMD",
                                        chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()))
        )

        # Get expired members
        expired_members = MembersPaymentGetter(self.client,
                                               self.config,
                                               self.logger).GetAllMembersWithExpiringPayment(self.cmd_data.Chat(),
                                                                                             days_left)

        # Build message
        if expired_members.Any():
            # Build strings for easier reading
            days_left_str = (self.translator.GetSentence("IN_DAYS_MSG", days=days_left)
                             if days_left > 1 else
                             (self.translator.GetSentence("TOMORROW_MSG")
                              if days_left == 1 else
                              self.translator.GetSentence("TODAY_MSG")))
            last_day_str = (self.translator.GetSentence("DAY_OF_MONTH_MSG", day_of_month=last_day)
                            if 1 <= last_day <= 31
                            else self.translator.GetSentence("FEW_DAYS_MSG"))

            # Build message
            msg = self.translator.GetSentence("CHECK_NO_PAYMENT_COMPLETED_CMD",
                                              days_left=days_left_str,
                                              members_count=expired_members.Count(),
                                              members_list=str(expired_members),
                                              last_day=last_day_str)

            # Add website if any
            website = self.config.GetValue(BotConfigTypes.PAYMENT_WEBSITE)
            if website != "":
                msg += self.translator.GetSentence("CHECK_NO_PAYMENT_WEBSITE_CMD",
                                                   website=website)

            # Add contact information if any
            support_email = self.config.GetValue(BotConfigTypes.SUPPORT_EMAIL)
            support_tg = self.config.GetValue(BotConfigTypes.SUPPORT_TELEGRAM)
            if support_email != "" and support_tg != "":
                msg += self.translator.GetSentence("CHECK_NO_PAYMENT_EMAIL_TG_CMD",
                                                   support_email=support_email,
                                                   support_telegram=support_tg)
            elif support_email != "":
                msg += self.translator.GetSentence("CHECK_NO_PAYMENT_ONLY_EMAIL_CMD",
                                                   support_email=support_email)
            elif support_tg != "":
                msg += self.translator.GetSentence("CHECK_NO_PAYMENT_ONLY_TG_CMD",
                                                   support_telegram=support_tg)
        else:
            msg = self.translator.GetSentence("CHECK_NO_PAYMENT_ALL_OK_CMD",
                                              chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()))

        # Send message
        self._SendMessage(msg)


#
# Command for removing users with no payment
#
class RemoveNoPaymentCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        # Notice before removing
        self._SendMessage(
            self.translator.GetSentence("REMOVE_NO_PAYMENT_NOTICE_CMD",
                                        chat_title=ChatHelper.GetTitle(self.cmd_data.Chat()))
        )

        finished = False
        kicked_members = ChatMembersList()
        # Continue until all members have been kicked
        # Useful in channels when at maximum 200 members can be kicked at once
        while not finished:
            curr_kicked_members = MembersKicker(self.client,
                                                self.config,
                                                self.logger).KickAllWithExpiredPayment(self.cmd_data.Chat())
            if curr_kicked_members.Any():
                kicked_members.AddMultiple(curr_kicked_members)
                # Stop if test mode to avoid infinite looping (members are not really kicked in test mode)
                finished = self.config.GetValue(BotConfigTypes.APP_TEST_MODE)
            else:
                finished = True

        # Build message
        msg = self.translator.GetSentence("REMOVE_NO_PAYMENT_COMPLETED_CMD",
                                          members_count=kicked_members.Count())
        if kicked_members.Any():
            msg += self.translator.GetSentence("REMOVE_NO_PAYMENT_LIST_CMD",
                                               members_list=str(kicked_members))

        # Send message
        self._SendMessage(msg)
        # Generate new invite link if necessary
        if kicked_members.Any():
            self._NewInviteLink()


#
# Command for starting payment task
#
class PaymentTaskStartCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        try:
            # Get parameters
            period_hours = self.cmd_data.Params().GetAsInt(0)
        except CommandParameterError:
            self._SendMessage(self.translator.GetSentence("PARAM_ERR_MSG"))
        else:
            try:
                kwargs["payments_check_scheduler"].Start(period_hours)
                self._SendMessage(self.translator.GetSentence("PAYMENT_TASK_START_OK_CMD", period=period_hours))
            except PaymentsCheckJobAlreadyRunningError:
                self._SendMessage(self.translator.GetSentence("TASK_EXISTENT_ERR_MSG"))
            except PaymentsCheckJobInvalidPeriodError:
                self._SendMessage(self.translator.GetSentence("TASK_PERIOD_ERR_MSG"))


#
# Command for stopping payment task
#
class PaymentTaskStopCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        try:
            kwargs["payments_check_scheduler"].Stop()
            self._SendMessage(self.translator.GetSentence("PAYMENT_TASK_STOP_OK_CMD"))
        except PaymentsCheckJobNotRunningError:
            self._SendMessage(self.translator.GetSentence("TASK_NOT_EXISTENT_ERR_MSG"))


#
# Command for adding current chat to payment task
#
class PaymentTaskAddChatCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        try:
            kwargs["payments_check_scheduler"].AddChat(self.cmd_data.Chat())
            self._SendMessage(self.translator.GetSentence("PAYMENT_TASK_ADD_CHAT_OK_CMD"))
        except PaymentsCheckJobChatAlreadyPresentError:
            self._SendMessage(self.translator.GetSentence("PAYMENT_TASK_ADD_CHAT_ERR_CMD"))


#
# Command for removing current chat to payment task
#
class PaymentTaskRemoveChatCmd(CommandBase):
    # Execute command
    @GroupChatOnly
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        try:
            kwargs["payments_check_scheduler"].RemoveChat(self.cmd_data.Chat())
            self._SendMessage(self.translator.GetSentence("PAYMENT_TASK_REMOVE_CHAT_OK_CMD"))
        except PaymentsCheckJobChatNotPresentError:
            self._SendMessage(self.translator.GetSentence("PAYMENT_TASK_REMOVE_CHAT_ERR_CMD"))


#
# Command for removing all chats to payment task
#
class PaymentTaskRemoveAllChatsCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        kwargs["payments_check_scheduler"].RemoveAllChats()
        self._SendMessage(self.translator.GetSentence("PAYMENT_TASK_REMOVE_ALL_CHATS_CMD"))


#
# Payment task info command
#
class PaymentTaskInfoCmd(CommandBase):
    # Execute command
    def _ExecuteCommand(self,
                        **kwargs: Any) -> None:
        is_running = kwargs["payments_check_scheduler"].IsRunning()
        period = kwargs["payments_check_scheduler"].GetPeriod()
        chats = kwargs["payments_check_scheduler"].GetChats()

        state = (self.translator.GetSentence("TASK_RUNNING_MSG")
                 if is_running
                 else self.translator.GetSentence("TASK_STOPPED_MSG"))

        # Build message
        msg = self.translator.GetSentence("PAYMENT_TASK_INFO_STATE_CMD",
                                          state=state)
        if is_running:
            msg += self.translator.GetSentence("PAYMENT_TASK_INFO_PERIOD_CMD",
                                               period=period)
        if chats.Any():
            msg += self.translator.GetSentence("PAYMENT_TASK_INFO_GROUPS_CMD",
                                               chats_count=chats.Count(),
                                               chats_list=str(chats))

        self._SendMessage(msg)
