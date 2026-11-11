"""Private no-clobber journal for one two-part ciphertext transfer attempt.

Local fsync is not independent offsite custody. Keep this metadata private and
retain it across failures together with both original ciphertexts. No secrets,
source rows, account/bucket identifiers or generic arbitrary fields are accepted.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import stat

from b2_target_contract import require_version_id
from b2_versioned_transfer import KEY, MAX_STAGE_BYTES, Receipt


class JournalRejected(ValueError):
    """Generic, non-echoing private journal failure."""


class PrivatePackageJournal:
    def __init__(self, path: Path):
        self._fd = None; self._plan = None; self._verified = set(); self._broken = False
        try:
            parent = path.parent.lstat()
            if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
                    or parent.st_mode & 0o077):
                raise JournalRejected('private journal parent required')
            self._fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.fsync(self._fd)
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except (OSError, ValueError):
            self.close()
            raise JournalRejected('new private journal could not be created') from None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self._fd is not None:
            os.close(self._fd); self._fd = None

    def __call__(self, event: dict) -> None:
        if self._fd is None or self._broken:
            raise JournalRejected('journal unavailable')
        try:
            if type(event) is not dict:
                raise JournalRejected('invalid journal event')
            if event.get('event') == 'planned':
                if self._plan is not None or set(event) != {'event','parts'}:
                    raise JournalRejected('one exact package plan required')
                parts = event['parts']
                if type(parts) is not dict or set(parts) != {'database','roles'}:
                    raise JournalRejected('both encrypted parts required')
                for part in parts.values():
                    if (type(part) is not dict or set(part) != {'key','sha256','size_bytes'}
                            or type(part['key']) is not str or not KEY.fullmatch(part['key'])
                            or type(part['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',part['sha256'])
                            or type(part['size_bytes']) is not int or not 100 < part['size_bytes'] <= MAX_STAGE_BYTES):
                        raise JournalRejected('invalid encrypted part identity')
                if (parts['database']['key'] == parts['roles']['key']
                        or sum(p['size_bytes'] for p in parts.values()) > MAX_STAGE_BYTES):
                    raise JournalRejected('distinct bounded part identities required')
                # Deep copy to prevent caller mutation after persistence.
                normalized = json.loads(json.dumps(event))
            elif event.get('event') == 'verified':
                if (self._plan is None or set(event) != {'event','part','receipt'}
                        or type(event['part']) is not str or event['part'] not in self._plan
                        or event['part'] in self._verified or type(event['receipt']) is not Receipt):
                    raise JournalRejected('unbound or duplicate part receipt')
                receipt = event['receipt']; expected = self._plan[event['part']]
                require_version_id(receipt.version_id)
                if (receipt.key != expected['key'] or receipt.sha256 != expected['sha256']
                        or type(receipt.size_bytes) is not int or receipt.size_bytes != expected['size_bytes']):
                    raise JournalRejected('receipt does not match package plan')
                normalized = {'event':'verified','part':event['part'],'receipt':asdict(receipt)}
            else:
                raise JournalRejected('unsupported journal event')
            payload=(json.dumps(normalized,sort_keys=True,separators=(',',':'))+'\n').encode()
            view=memoryview(payload)
            while view:
                written=os.write(self._fd,view)
                if written <= 0:
                    raise OSError('write failed')
                view=view[written:]
            os.fsync(self._fd)
            if normalized['event']=='planned':
                self._plan=normalized['parts']
            else:
                self._verified.add(normalized['part'])
        except (OSError, ValueError, TypeError, KeyError):
            # Failed/partial writes must not permit any later network step.
            self._broken=True
            raise JournalRejected('private package journal event rejected') from None
