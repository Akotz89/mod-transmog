"""Exercise portable access and its SQL update on the project's guarded WSL host."""
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PortableAccessTest(unittest.TestCase):
    def test_command(self):
        subprocess.run(['/home/aaron/Documents/ChatGPT/wow private server/scripts/wow-build-host-guard'], check=True)
        text = (ROOT / 'src/cs_transmog.cpp').read_text()
        start = text.index('    static bool HandleTransmogPortableCommand(')
        end = text.index('\n    enum class ClaimResult', start)
        source = r'''
using uint32=unsigned int;
struct Unit {};
struct Player { int casts=0; int GetGUID(){return 1;} void CastSpell(Unit*,uint32,bool){++casts;} };
struct ChatHandler { Player* player; int errors=0; void SendErrorMessage(char const*){++errors;} };
struct PlayerIdentifier { Player* player; static PlayerIdentifier value; static PlayerIdentifier* FromSelf(ChatHandler* h){value.player=h->player;return &value;} Player* GetConnectedPlayer(){return player;} };
PlayerIdentifier PlayerIdentifier::value{nullptr};
constexpr int PLUS_FEATURE_PET=1;
struct Transmog { bool IsPortableNPCEnabled=true, IsTransmogPlusEnabled=false, eligible=false; uint32 PetSpellId=200100; bool IsPlusFeatureEligible(int,int){return eligible;} } transmog;
Transmog* sTransmogrification=&transmog;
struct SpellMgr { bool available=true; bool GetSpellInfo(uint32){return available;} } spells; SpellMgr* sSpellMgr=&spells;
''' + text[start:end] + r'''
int main(){
 Player p;ChatHandler h{&p};
 transmog.IsPortableNPCEnabled=false;HandleTransmogPortableCommand(&h);if(p.casts!=0 || h.errors!=1)return 1;
 transmog.IsPortableNPCEnabled=true;HandleTransmogPortableCommand(&h);if(p.casts!=1)return 2;
 transmog.IsTransmogPlusEnabled=true;HandleTransmogPortableCommand(&h);if(p.casts!=1 || h.errors!=2)return 3;
 transmog.eligible=true;HandleTransmogPortableCommand(&h);if(p.casts!=2)return 4;
 spells.available=false;HandleTransmogPortableCommand(&h);if(p.casts!=2 || h.errors!=3)return 5;
 return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            cpp = Path(directory) / 'portable.cpp'
            cpp.write_text(source)
            binary = Path(directory) / 'portable'
            subprocess.run(['g++', '-std=c++17', str(cpp), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_sql_and_default(self):
        sql = (ROOT / 'data/sql/db-world/2026_10_12_mod_transmog_portable_player_access.sql').read_text()
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE command(name TEXT, security INTEGER)')
            db.executemany('INSERT INTO command VALUES (?, ?)', [('transmog portable', 1), ('transmog portable', 2), ('other', 1)])
            db.executescript(sql)
            db.executescript(sql)
            self.assertEqual(db.execute('SELECT name, security FROM command ORDER BY rowid').fetchall(), [('transmog portable', 0), ('transmog portable', 2), ('other', 1)])
        self.assertIn('"Transmogrification.PetSpellId", 200100', (ROOT / 'src/Transmogrification.cpp').read_text())
        self.assertIn('Transmogrification.PetSpellId = 200100', (ROOT / 'conf/transmog.conf.dist').read_text())
        self.assertIn('DELETE FROM `spell_dbc` WHERE `ID` = 200100', (ROOT / 'data/sql/db-world/2016_11_17_transmog_npc.sql').read_text())

if __name__ == '__main__':
    unittest.main()
