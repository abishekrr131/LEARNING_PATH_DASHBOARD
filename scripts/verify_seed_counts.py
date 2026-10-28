import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.seed.data.it_ml_engineer import TARGET as ML_ENG
from database.seed.data.it_full_stack import TARGET as FULL_STACK
from database.seed.data.it_cyber_security import TARGET as CYBER_SEC
from database.seed.data.it_genai import TARGET as GENAI
from database.seed.data.govt_upsc import TARGET as UPSC
from database.seed.data.govt_ssc_cgl import TARGET as SSC_CGL
from database.seed.data.govt_banking import TARGET as BANKING

targets = [ML_ENG, FULL_STACK, CYBER_SEC, GENAI, UPSC, SSC_CGL, BANKING]
tot = 0
for t in targets:
    q_len = len(t["questions"])
    tot += q_len
    print(f"{t['target']['name']}: {q_len} curated seed questions")
print(f"Total seed questions in Python source: {tot}")
