"""Strict aapt2 binary AndroidManifest service contract for non-Play observer.

Only the compiled APK is inspected. No selected-game identity or action
authority is conferred by a successfully parsed manifest.
"""
import re

SERVICE_NAMES = frozenset(('com.alpha0.app.game.GameObservationService', '.game.GameObservationService'))
ANDROID_ATTR_IDS = {
    'name': '01010003',
    'enabled': '0101000e',
    'exported': '01010010',
    'stopWithTask': '0101036a',
    'foregroundServiceType': '01010599',
}
# Modern aapt2 uses the full Android framework URI, older output uses android:.
ANDROID_ATTR = re.compile(
    r'^\s*A:\s+(?:android:|http://schemas\.android\.com/apk/res/android:)'
    r'([A-Za-z][A-Za-z0-9]*)\(0x([0-9a-fA-F]{8})\)\s*=\s*(.*)$',
)
HEX = re.compile(r'0x[0-9a-fA-F]+')
DECIMAL = re.compile(r'(?:0|[1-9][0-9]*)')
TYPED = re.compile(r'\(type 0x([0-9a-fA-F]+)\)(0x[0-9a-fA-F]+)')


def _value(raw: str, *, boolean: bool) -> int:
    if boolean and raw in ('true', 'false'):
        return 1 if raw == 'true' else 0
    typed = TYPED.fullmatch(raw)
    if typed:
        type_id = int(typed[1], 16)
        if type_id not in ((0x12,) if boolean else (0x10, 0x11)):
            raise ValueError('unexpected binary attribute type')
        return int(typed[2], 16)
    if HEX.fullmatch(raw):
        return int(raw, 16)
    if DECIMAL.fullmatch(raw):
        return int(raw, 10)
    raise ValueError('unsupported binary attribute value')


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
            parsed = ANDROID_ATTR.fullmatch(child)
            if not parsed:
                continue
            name, attr_id, value = parsed.groups()
            if name not in ANDROID_ATTR_IDS:
                continue
            if attr_id.lower() != ANDROID_ATTR_IDS[name]:
                raise ValueError('incorrect Android service attribute resource ID')
            if name in attrs:
                raise ValueError('duplicate binary service attribute')
            attrs[name] = value.strip()
        name = re.match(r'^"([^"\n]+)"', attrs.get('name', ''))
        if name and name[1] in SERVICE_NAMES:
            services.append(attrs)
    if len(services) != 1:
        raise ValueError('exactly one signed_feed capture service required')
    attrs = services[0]

    def number(name: str, *, boolean: bool = False) -> int:
        if name not in attrs:
            raise ValueError('missing binary capture service attribute: ' + name)
        return _value(attrs[name], boolean=boolean)

    if number('enabled', boolean=True) not in (1, 0xffffffff):
        raise ValueError('signed_feed capture service disabled')
    if number('exported', boolean=True) != 0:
        raise ValueError('capture service exported')
    if number('stopWithTask', boolean=True) not in (1, 0xffffffff):
        raise ValueError('capture service must stop with task')
    if number('foregroundServiceType') != 0x20:
        raise ValueError('capture service must use only mediaProjection FGS type')
