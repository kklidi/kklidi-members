"""Compile the plugin's simple gettext PO catalog without an external msgfmt binary."""
import ast
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]

def read_po(path):
    messages = {}
    msgid = None
    msgstr = None
    field = None
    def commit():
        nonlocal msgid, msgstr
        if msgid is not None and msgstr is not None:
            messages[msgid] = msgstr
        msgid = msgstr = None
    for raw in path.read_text(encoding='utf-8').splitlines() + ['']:
        line = raw.strip()
        if not line or line.startswith('#'):
            if not line:
                commit()
                field = None
            continue
        if line.startswith('msgid '):
            commit()
            msgid = ast.literal_eval(line[5:].strip())
            msgstr = None
            field = 'msgid'
        elif line.startswith('msgstr '):
            msgstr = ast.literal_eval(line[6:].strip())
            field = 'msgstr'
        elif line.startswith('"'):
            value = ast.literal_eval(line)
            if field == 'msgid':
                msgid += value
            elif field == 'msgstr':
                msgstr += value
        else:
            raise ValueError('Unsupported PO syntax: ' + line)
    return messages

def compile_mo(messages, destination):
    keys = sorted(messages)
    originals = [key.encode('utf-8') for key in keys]
    translations = [messages[key].encode('utf-8') for key in keys]
    count = len(keys)
    original_table = 7 * 4
    translation_table = original_table + count * 8
    string_offset = translation_table + count * 8
    original_blob = b'\0'.join(originals) + b'\0'
    translation_offset = string_offset + len(original_blob)
    translation_blob = b'\0'.join(translations) + b'\0'
    original_entries = []
    offset = string_offset
    for value in originals:
        original_entries.append((len(value), offset))
        offset += len(value) + 1
    translation_entries = []
    offset = translation_offset
    for value in translations:
        translation_entries.append((len(value), offset))
        offset += len(value) + 1
    data = struct.pack('<7I', 0x950412de, 0, count, original_table,
        translation_table, 0, 0)
    data += b''.join(struct.pack('<2I', *entry) for entry in original_entries)
    data += b''.join(struct.pack('<2I', *entry) for entry in translation_entries)
    destination.write_bytes(data + original_blob + translation_blob)

def main():
    source = ROOT / 'languages/kklidi-members-ko_KR.po'
    destination = ROOT / 'languages/kklidi-members-ko_KR.mo'
    messages = read_po(source)
    compile_mo(messages, destination)
    print('Compiled ' + str(len(messages)) + ' messages.')

if __name__ == '__main__':
    main()
