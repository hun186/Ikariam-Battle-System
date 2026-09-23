import os
from pathlib import Path
import subprocess
import sys

import build_backend


def test_wheel_installs_and_loads_resources_outside_checkout(tmp_path):
    wheel_dir=tmp_path/'wheel'; wheel_dir.mkdir()
    wheel=wheel_dir/build_backend.build_wheel(str(wheel_dir))
    venv=tmp_path/'venv'
    subprocess.run([sys.executable,'-m','venv',str(venv)],check=True)
    python=venv/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    subprocess.run([str(python),'-m','pip','install','--no-deps',str(wheel)],check=True,capture_output=True)
    outside=tmp_path/'outside'; outside.mkdir()
    code="""from ikariam_battle import UnitRegistry,simulate
from ikariam_battle.profiles import WorkshopProfile,ForgeProfile,SupportProfile
assert UnitRegistry.load().get('hoplite').hit_points==1120
assert WorkshopProfile.load().bonus('land',12)==60
assert str(ForgeProfile.load().effect(5).damage_multiplier)=='1.15'
assert SupportProfile.load().derived_capacity==4000
s={'policy':'strict','battlefield':'land-mini','attacker':{'units':[{'unit_id':'hoplite','quantity':1}]},'defender':{'units':[{'unit_id':'hoplite','quantity':1}]}}
assert simulate(s)['status']=='inconclusive'
"""
    subprocess.run([str(python),'-c',code],cwd=outside,check=True)
