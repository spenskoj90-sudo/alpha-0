"""Strict aapt2 merged-APK service contract for the non-Play observer.

Only checks the signed_feed captured APK. This grants no captured-game identity,
knowledge advice, physical approval or permission to publish a release.
"""
import re

SERVICE_NAMES = {'com.alpha0.app.game.GameObservationService',
                 '.game.GameObservationService'}


def require_capture_service_manifest(xmltree: str) -> None:
    services = []
    lines = xmltree.splitlines()
    for index, line in enumerate(lines):
        if not re.match(r'^\s*E: service(?:\s|$)', line):
            continue
        attrs = {}
        for child in lines[index + 1:]:
            if re.match(r'^\s*E: ', child):
                break
            attr = re.match(
                r'^\s*A: android:([a-zA-Z][a-zA-Z0-9]*)(?:\(0x[0-9a-fA-F]+\))?=(.*)$',
                child,
            )
            if attr:
                name, value = attr.groups()
                if name in attrs:
                    raise ValueError('duplicate binary service attribute')
                attrs[name] = value.strip()
        name = re.match(r'^"([^"\n]+)"', attrs.get('name', ''))
        if name and name.group(1) in SERVICE_NAMES:
            services.append(attrs)
    if len(services) != 1:
        raise ValueError('exactly one signed_feed capture service required')

    def binary_number(field):
        match = re.fullmatch(r'\(type 0x[0-9a-fA-F]+\)(0x[0-9a-fA-F]+)',
                             services[0].get(field, ''))
        if match is None:
            raise ValueError('missing binary capture service attribute: ' + field)
        return int(match[1], 16)

    if binary_number('enabled') not in (1, 0xffffffff):
        raise ValueError('signed_feed capture service disabled')
    if binary_number('exported') != 0:
        raise ValueError('capture service exported')
    if binary_number('stopWithTask') not in (1, 0xffffffff):
        raise ValueError('capture service must stop with task')
    if binary_number('foregroundServiceType') != 0x20:
        raise ValueError('capture service must use only mediaProjection FGS type')
