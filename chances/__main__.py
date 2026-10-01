"""The Python protocol surface exposed as a JSON CLI for researchers and agents."""

from __future__ import annotations

import argparse
import json
import sys

from . import ChancesError, catalog, generate, inspect, replay, verify


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='chances', description='Declare, generate, verify, and replay scientific randomness.'
    )
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('catalog', help='Print operation contracts as JSON.')
    for name in ('inspect', 'generate'):
        command = commands.add_parser(name)
        command.add_argument('spec', help='Local JSON specification.')
        command.add_argument('--source', help='Optional local NPY source; pickle is forbidden.')
        if name == 'generate':
            command.add_argument('--output', required=True, help='New bundle directory.')
    for name in ('verify', 'replay'):
        command = commands.add_parser(name)
        command.add_argument('bundle', help='Saved bundle directory.')
        if name == 'replay':
            command.add_argument('--output', help='Optional new bundle directory.')
    args = parser.parse_args(argv)
    try:
        if args.command == 'catalog':
            value = catalog()
        elif args.command == 'inspect':
            value = inspect(args.spec, source=args.source)
        elif args.command == 'generate':
            result = generate(args.spec, source=args.source, output=args.output)
            value = {'output': args.output, 'receipt': result.receipt}
        else:
            result = (
                verify(args.bundle)
                if args.command == 'verify'
                else replay(args.bundle, output=args.output)
            )
            value = {'verified': True, 'receipt': result.receipt}
        sys.stdout.write(
            json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n'
        )
        return 0
    except ChancesError as error:
        sys.stderr.write(json.dumps({'error': error.to_dict()}, sort_keys=True) + '\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
