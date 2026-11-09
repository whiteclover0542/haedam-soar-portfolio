#!/usr/local/bin/python3.11
"""Restricted EasyRule adapter for the isolated S10 source, not an HTTP server.

CLI: haedam-pf-response ACTION TARGET REQUEST_ID OWNER_ID
Can be an SSH forced command: SSH_ORIGINAL_COMMAND is parsed, never executed.
Default owner journal is persistent/root-only; no automatic retry or lock expiry.
"""
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

TARGETS = frozenset({'203.0.113.22'})
TABLE = 'EasyRuleBlockHostsWAN'
STATE_DIR = Path('/cf/conf/haedam-pf-response')
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}\Z')


class Refused(Exception):
    pass


class BackendError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def parse_request(args):
    if len(args) != 4:
        raise Refused('four_arguments_required')
    action, target, request_id, owner_id = args
    if action not in ('status', 'block', 'unblock'):
        raise Refused('invalid_action')
    if target not in TARGETS or str(ipaddress.IPv4Address(target)) != target:
        raise Refused('target_not_approved')
    if not IDENTIFIER.fullmatch(request_id) or not IDENTIFIER.fullmatch(owner_id):
        raise Refused('invalid_identifier')
    return dict(action=action, target=target, request_id=request_id, owner_id=owner_id)


def command_arguments(argv, original=None):
    if original is None:
        return argv
    if len(original) > 1024:
        raise Refused('invalid_ssh_command')
    try:
        args = shlex.split(original)
    except ValueError:
        raise Refused('invalid_ssh_command') from None
    if not args or args[0] != 'haedam-pf-response':
        raise Refused('invalid_ssh_command')
    return args[1:]


@dataclass(frozen=True)
class Snapshot:
    ready: bool
    configured: bool
    table_present: bool
    rule_present: bool
    covered_by_network: bool = False
    other_config: tuple = ()
    other_table: tuple = ()

    @property
    def applied(self):
        return self.configured and self.table_present and self.rule_present

    @property
    def absent(self):
        return not self.configured and not self.table_present and not self.covered_by_network

    def public(self):
        return {k: v for k, v in asdict(self).items() if not k.startswith('other_')}


class PfSenseBackend:
    def __init__(self, config_path='/cf/conf/config.xml', version_path='/etc/version'):
        self.config_path = Path(config_path)
        self.version_path = Path(version_path)

    def run(self, args, timeout=20):
        try:
            return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise BackendError('command_unavailable_or_timeout') from None

    def read(self, args):
        p = self.run(args)
        if p.returncode != 0:
            raise BackendError('read_failed')
        return p.stdout

    def snapshot(self, target):
        root = ET.parse(self.config_path).getroot()
        ready = (self.version_path.read_text().strip() == '2.7.2-RELEASE'
                 and root.findtext('./interfaces/wan/if') == 'em0'
                 and root.findtext('./interfaces/wan/ipaddr') == '203.0.113.1')
        aliases = [a for a in root.findall('./aliases/alias') if a.findtext('name') == TABLE]
        if len(aliases) > 1 or any(a.findtext('type') != 'network' for a in aliases):
            raise BackendError('unexpected_alias_definition')
        configured = (aliases[0].findtext('address') or '').split() if aliases else []
        tables = self.read(['/sbin/pfctl', '-s', 'Tables']).split()
        runtime = self.read(['/sbin/pfctl', '-t', TABLE, '-T', 'show']).split() if TABLE in tables else []
        try:
            config_nets = {str(ipaddress.ip_network(v, strict=False)) for v in configured}
            table_nets = {str(ipaddress.ip_network(v, strict=False)) for v in runtime}
        except ValueError:
            raise BackendError('unexpected_alias_address') from None
        exact = target + '/32'
        ip = ipaddress.ip_address(target)
        covered = any(ip in ipaddress.ip_network(v) for v in config_nets | table_nets
                      if ipaddress.ip_network(v).version == 4 and v != exact)
        rules = self.read(['/sbin/pfctl', '-sr']).splitlines()
        candidates = [i for i, line in enumerate(rules) if line.startswith('block ')
                      and ' on em0 inet ' in line and 'in' in line.split(' on em0 inet ')[0].split()
                      and 'quick' in line.split(' on em0 inet ')[0].split()
                      and f'from <{TABLE}> to any' in line]
        passes = [i for i, line in enumerate(rules) if line.startswith('pass ') and ' on em0 ' in line]
        rule_present = len(candidates) == 1 and (not passes or candidates[0] < min(passes))
        return Snapshot(ready, exact in config_nets, exact in table_nets, rule_present, covered,
                        tuple(sorted(config_nets - {exact})), tuple(sorted(table_nets - {exact})))

    def change(self, action, target):
        # easyrule may exit zero with a failure message. Controller must read back.
        p = self.run(['/usr/local/bin/easyrule', action, 'wan', target], timeout=30)
        if p.returncode != 0:
            raise BackendError('easyrule_exit_failed')

    def kill_states(self, target):
        p = self.run(['/sbin/pfctl', '-k', target])
        if p.returncode != 0:
            raise BackendError('target_state_kill_failed')
        states = self.read(['/sbin/pfctl', '-ss'])
        if re.search(r'(?<![\d.])' + re.escape(target) + r'(?=[:\s)])', states):
            raise BackendError('target_states_remain')


class Journal:
    def __init__(self, directory):
        self.directory = Path(directory)

    @contextmanager
    def locked(self):
        if self.directory.is_symlink():
            raise Refused('unsafe_journal_path')
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        lock = self.directory / 'operation.lock'
        try:
            lock.mkdir(mode=0o700)
        except FileExistsError:
            raise Refused('busy_or_stale_lock_requires_review') from None
        try:
            yield
        finally:
            lock.rmdir()

    def load(self):
        path = self.directory / 'state.json'
        if path.is_symlink():
            raise Refused('unsafe_journal_path')
        if not path.exists():
            return {'version': 1, 'claim': None, 'pending': None, 'receipts': {}}
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('version') != 1 or not isinstance(data.get('receipts'), dict):
            raise Refused('invalid_journal_requires_review')
        return data

    def save(self, data):
        fd, name = tempfile.mkstemp(prefix='state.', dir=self.directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, sort_keys=True)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(name, 0o600)
            os.replace(name, self.directory / 'state.json')
            if os.name == 'posix':
                fd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        finally:
            if os.path.exists(name):
                os.unlink(name)


def response(req, started, *, ok, result, reason, state=None, changed=False, replayed=False):
    return {**req, 'schema_version': '1.0', 'via': 'pfsense', 'ok': ok, 'result': result,
            'reason': reason, 'changed': changed, 'replayed': replayed,
            'applied_verified': state.applied if state else None, 'effect_verified': None,
            'state': state.public() if state else None, 'requested_at': started, 'finished_at': now()}


def operate(req, backend, journal):
    started = now()
    fingerprint = hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()
    with journal.locked():
        data = journal.load()
        before = backend.snapshot(req['target'])
        if not before.ready or before.covered_by_network:
            return response(req, started, ok=False, result='rejected', reason='preflight_failed', state=before)
        if req['action'] == 'status':
            if data.get('pending'):
                return response(req, started, ok=False, result='failed', reason='pending_needs_reconciliation', state=before)
            return response(req, started, ok=True, result='status', reason='read_only_snapshot', state=before)
        seen = data['receipts'].get(req['request_id'])
        if seen:
            if seen['fingerprint'] != fingerprint:
                return response(req, started, ok=False, result='rejected', reason='request_id_conflict', state=before)
            expected = seen['response']['result'] in ('applied', 'already_applied')
            owned = data.get('claim') and data['claim']['owner_id'] == req['owner_id']
            if seen['response']['ok'] and (before.applied and owned if expected else before.absent):
                return {**seen['response'], 'replayed': True}
            return response(req, started, ok=False, result='rejected', reason='replay_needs_reconciliation',
                            replayed=True, state=before)
        claim = data.get('claim')
        if (data.get('pending') and data['pending']['request']['request_id'] == req['request_id']
                and data['pending']['fingerprint'] != fingerprint):
            return response(req, started, ok=False, result='rejected', reason='request_id_conflict', state=before)
        if claim and claim['owner_id'] != req['owner_id']:
            return response(req, started, ok=False, result='rejected', reason='another_owner', state=before)
        if data.get('pending') and req['action'] != 'unblock':
            return response(req, started, ok=False, result='rejected', reason='pending_needs_reconciliation', state=before)
        if not claim and not before.absent:
            return response(req, started, ok=False, result='rejected', reason='unmanaged_existing_block', state=before)
        if len(data['receipts']) >= 4096:
            return response(req, started, ok=False, result='rejected', reason='journal_full', state=before)
        if req['action'] == 'block' and not (before.absent or before.applied):
            return response(req, started, ok=False, result='rejected', reason='inconsistent_state', state=before)
        # Persist ownership and intent BEFORE a possible side effect. A crash cannot erase intent.
        if req['action'] == 'block':
            data['claim'] = {'owner_id': req['owner_id'], 'target': req['target']}
        data['pending'] = {'request': req, 'fingerprint': fingerprint}
        journal.save(data)
        after = None
        changed = False
        try:
            if req['action'] == 'block':
                if before.absent:
                    backend.change('block', req['target'])
                    changed = True
                after = backend.snapshot(req['target'])
                if not after.ready or not after.applied or after.covered_by_network:
                    raise BackendError('block_readback_failed')
                backend.kill_states(req['target'])
                after = backend.snapshot(req['target'])
                if not after.applied or not after.ready or after.covered_by_network:
                    raise BackendError('block_changed_during_verification')
                result = 'applied' if changed else 'already_applied'
            else:
                if not before.absent:
                    backend.change('unblock', req['target'])
                    changed = True
                after = backend.snapshot(req['target'])
                if not after.ready or not after.absent:
                    raise BackendError('unblock_readback_failed')
                result = 'released'
            if (before.other_config, before.other_table) != (after.other_config, after.other_table):
                raise BackendError('unrelated_alias_entries_changed')
        except Exception:
            # May have changed the firewall. Keep claim/pending; never retry or claim no-change.
            failed = response(req, started, ok=False, result='failed', reason='outcome_needs_reconciliation',
                              state=after, changed=None)
            data['receipts'][req['request_id']] = {'fingerprint': fingerprint, 'response': failed}
            journal.save(data)
            return failed
        result_body = response(req, started, ok=True, result=result, reason='verified_managed_state',
                               state=after, changed=changed)
        if req['action'] == 'unblock':
            data['claim'] = None
        data['pending'] = None
        data['receipts'][req['request_id']] = {'fingerprint': fingerprint, 'response': result_body}
        journal.save(data)
        return result_body


def main():
    try:
        req = parse_request(command_arguments(sys.argv[1:], os.environ.get('SSH_ORIGINAL_COMMAND')))
        if not hasattr(os, 'geteuid') or os.geteuid() != 0:
            raise Refused('root_required')
        result = operate(req, PfSenseBackend(), Journal(STATE_DIR))
    except (Refused, ValueError) as exc:
        # Only fixed validation messages; raw original command and credentials are never logged.
        reason = str(exc) if isinstance(exc, Refused) else 'invalid_input'
        result = {'ok': False, 'result': 'rejected', 'reason': reason}
    except Exception:
        result = {'ok': False, 'result': 'failed', 'reason': 'backend_or_journal_unavailable'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
