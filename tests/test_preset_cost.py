"""Exercise real preset preview and save bodies on the guarded build host."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def build_host_guard():
    roots = [ROOT, *ROOT.parents]
    if os.environ.get('WOW_PROJECT_ROOT'):
        roots.insert(0, Path(os.environ['WOW_PROJECT_ROOT']))
    for root in roots:
        guard = root / 'scripts/wow-build-host-guard'
        if guard.is_file():
            subprocess.run([str(guard)], check=True)
            return
    raise RuntimeError('WoW build-host guard not found; set WOW_PROJECT_ROOT to the WoW project root')


class PresetCostTest(unittest.TestCase):
    def test_missing_guard_fails_closed(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch(__name__ + '.ROOT', Path('/nonexistent-wow-checkout')):
            with self.assertRaisesRegex(RuntimeError, 'guard not found'):
                build_host_guard()

    def test_preview_and_save(self):
        build_host_guard()
        source = (ROOT / 'src/transmog_scripts.cpp').read_text()
        start = source.index('static bool GetPresetCost(')
        helper = source[start:source.index('\n#endif', start)]
        preview = source.split('case EQUIPMENT_SLOT_END + 8: // Save preset', 1)[1]
        preview = preview[preview.index('uint64 itemCost = 0;'):preview.index('                AddGossipItemFor(player, GOSSIP_ICON_MONEY_BAG, "|TInterface/PaperDollInfoFrame/UI-GearManager-Undo')]
        save_body = source.split('bool OnGossipSelectCode(', 1)[1]
        save = save_body[save_body.index('uint64 itemCost = 0;'):save_body.index('                std::ostringstream ss;')]
        charge = save_body[save_body.index('                if (cost)\n                    player->ModifyMoney(-cost);'):]
        charge = charge[:charge.index('\n                break;')]
        template = (ROOT / 'tests/preset_preview_fixture.cpp.in').read_text()
        program = template.replace('@HELPER@', helper).replace('@PREVIEW@', preview).replace('@SAVE@', save).replace('@CHARGE@', charge)
        with tempfile.TemporaryDirectory() as directory:
            cpp = Path(directory) / 'preset.cpp'
            cpp.write_text(program)
            binary = Path(directory) / 'preset'
            subprocess.run(['g++', '-std=c++17', '-fsanitize=undefined', str(cpp), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
