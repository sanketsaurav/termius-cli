# -*- coding: utf-8 -*-
"""Module with info command."""
from operator import attrgetter
from cliff.show import ShowOne
from ..core.commands import AbstractCommand
from ..core.commands.mixins import GetRelationMixin, SshConfigMergerMixin
from ..core.storage.strategies import RelatedGetStrategy
from ..core.models.terminal import Group, Host, SshConfig


class InfoCommand(SshConfigMergerMixin, GetRelationMixin,
                  ShowOne, AbstractCommand):
    """Show info about host or group."""

    get_strategy = RelatedGetStrategy
    model_class = SshConfig

    @property
    def formatter_namespace(self):
        """Return entrypoint with cliff formatters."""
        return 'serverauditor.info.formatters'

    def get_parser(self, prog_name):
        """Create command line argument parser.

        Use it to add extra options to argument parser.
        """
        parser = super(InfoCommand, self).get_parser(prog_name)
        parser.add_argument(
            '-G', '--group', dest='entry_type',
            action='store_const', const=Group, default=Host,
            help='Show info about group.'
        )
        parser.add_argument(
            '-H', '--host', dest='entry_type',
            action='store_const', const=Host, default=Host,
            help='Show info about host.'
        )
        parser.add_argument(
            '-M', '--no-merge', action='store_true',
            help='Do not merge configs.'
        )
        parser.add_argument(
            '--ssh', action='store_true',
            help='Show info in ssh_config format'
        )
        parser.add_argument('id_or_name', metavar='ID or NAME')
        return parser

    # pylint: disable=unused-argument
    def take_action(self, parsed_args):
        """Process CLI call."""
        instance = self.get_relation(
            parsed_args.entry_type, parsed_args.id_or_name
        )
        ssh_config = self.get_merged_ssh_confi(instance)

        return self.prepare_fields(ssh_config, instance)

    # pylint: disable=no-self-use
    def prepare_fields(self, ssh_config, instance):
        """Generate 2size tuple with ssh_config fields.

        Warning there is one additional field - 'address'.
        """
        ssh_config_fields = ssh_config.allowed_fields()
        keys = tuple(ssh_config_fields) + ('address',)
        values = (
            attrgetter(*ssh_config_fields)(ssh_config) +
            (getattr(instance, 'address', ''),)
        )
        return (keys, values)