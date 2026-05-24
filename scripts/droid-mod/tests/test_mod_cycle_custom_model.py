import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "mods" / "mod_cycle_custom_model.py"
STATUS = ROOT / "status.py"


# 真实 0.103.0 二进制里 mT1 (basic ModelSelector) 的 list builder 工厂区原文
MT1_ORIGINAL = (
    b'JH.push({type:"header",label:K("common:modelSelector.factoryModelsHeader")});'
    b'let PH=p.map((UH)=>{let QH=fF(UH,M);return{type:"model",id:UH,disabled:!QH.allowed}}),'
    b'MH=n.map((UH)=>{let QH=fF(UH,M);return{type:"model",id:UH,disabled:!QH.allowed}}),'
    b'CH=g.map((UH)=>{let QH=fF(UH.id,M,UH);return{type:"model",id:UH.id,disabled:!QH.allowed}});'
    b'if(JH.push(...PH),n.length>0)JH.push({type:"toggle-builtins",expanded:N,hiddenCount:n.length});'
    b'if(N)JH.push(...MH);'
    b'if(CH.length>0)JH.push({type:"sep"}),'
    b'JH.push({type:"header",label:K("common:modelSelector.customModelsHeader")}),'
    b'JH.push(...CH);'
)

# 真实 0.103.0 里 iT1 (tabbed/mission ModelSelector) 的 list builder 工厂区原文
IT1_ORIGINAL = (
    b'JT.push({type:"header",label:bH?t("common:missionModelPicker.recommendedHeader"):'
    b't("common:modelSelector.factoryModelsHeader")});'
    b'let GR=sH.map((ER)=>{let WR=fF(ER,YH);return{type:"model",id:ER,disabled:!WR.allowed}}),'
    b'uR=rH.map((ER)=>{let WR=fF(ER,YH);return{type:"model",id:ER,disabled:!WR.allowed}}),'
    b'eT=xH.map((ER)=>{let WR=fF(ER.id,YH,ER);return{type:"model",id:ER.id,disabled:!WR.allowed}});'
    b'if(JT.push(...GR),rH.length>0)JT.push({type:"sep"}),'
    b'JT.push({type:"toggle-builtins",expanded:kH,hiddenCount:rH.length});'
    b'if(kH)JT.push(...uR);'
    b'if(eT.length>0)JT.push({type:"sep"}),'
    b'JT.push({type:"header",label:t("common:modelSelector.customModelsHeader")}),'
    b'JT.push(...eT);'
)

MT1_CORE = (
    b'JH.push(...g.map((UH)=>{let QH=fF(UH.id,M,UH);'
    b'return{type:"model",id:UH.id,disabled:!QH.allowed}}));'
)
IT1_CORE = (
    b'JT.push(...xH.map((ER)=>{let WR=fF(ER.id,YH,ER);'
    b'return{type:"model",id:ER.id,disabled:!WR.allowed}}));'
)

# 真实 0.103.0 里 tw=Yd() 所在的唯一 anchor
TW_ANCHOR_ORIGINAL = (
    b',tw=Yd(),$_=!wR().hasAnyAvailableModel(tw),'
)
TW_ANCHOR_PATCHED = (
    b',tw=wR().getCustomModels().map(m=>m.id),$_=!wR().hasAnyAvailableModel(tw),'
)
TW_CORE = b'tw=wR().getCustomModels().map(m=>m.id)'

SELECTOR_104_ORIGINAL = (
    b'_T.push({type:"header",label:oH?HH("common:missionModelPicker.recommendedHeader"): '
    b'HH("common:modelSelector.factoryModelsHeader")});'
    b'let TR=tH.map((cR)=>{let QR=If(cR,yH);return{type:"model",id:cR,disabled:!QR.allowed}}),'
    b'VR=bH.map((cR)=>{let QR=If(cR,yH);return{type:"model",id:cR,disabled:!QR.allowed}}),'
    b'oT=vH.map((cR)=>{let QR=If(cR.id,yH,cR);return{type:"model",id:cR.id,disabled:!QR.allowed}});'
    b'if(_T.push(...TR),bH.length>0)_T.push({type:"sep"}),'
    b'_T.push({type:"toggle-builtins",expanded:fH,hiddenCount:bH.length});'
    b'if(fH)_T.push(...VR);'
    b'if(oT.length>0)_T.push({type:"sep"}),'
    b'_T.push({type:"header",label:HH("common:modelSelector.customModelsHeader")}),'
    b'_T.push(...oT);'
)
SELECTOR_104_CORE = (
    b'_T.push(...vH.map((cR)=>{let QR=If(cR.id,yH,cR);'
    b'return{type:"model",id:cR.id,disabled:!QR.allowed}}));'
)
TW_104_ORIGINAL = b',fJ=ye(),sw=!UR().hasAnyAvailableModel(fJ),'
TW_104_PATCHED = b',fJ=UR().getCustomModels().map(m=>m.id),sw=!UR().hasAnyAvailableModel(fJ),'
TW_104_CORE = b'fJ=UR().getCustomModels().map(m=>m.id)'
CYCLE_130_ORIGINAL = (
    b'getModelCycleCandidates(H){let T=new Set([...H,...this.customModels.map((B)=>B.id)]),'
    b'R=this.getAllowedCycleModelIds(this.getModelFavorites().filter((B)=>T.has(B)));'
    b'if(R.length>0)return{modelIds:R,source:"favorites"};'
    b'let A=[...H,...this.customModels.map((B)=>B.id)];'
    b'return{modelIds:this.getAllowedCycleModelIds(A),source:"all"}}'
)
CYCLE_130_CORE = (
    b'getModelCycleCandidates(H){let T=new Set(this.customModels.map((B)=>B.id)),'
    b'R=this.getAllowedCycleModelIds(this.getModelFavorites().filter((B)=>T.has(B)));'
    b'if(R.length>0)return{modelIds:R,source:"favorites"};'
    b'let A=this.customModels.map((B)=>B.id);'
    b'return{modelIds:this.getAllowedCycleModelIds(A),source:"all"}}'
)


def _write_droid(home: Path, data: bytes) -> Path:
    droid = home / ".local/bin/droid"
    droid.parent.mkdir(parents=True, exist_ok=True)
    droid.write_bytes(data)
    return droid


def _run(script: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class ModCycleCustomModelTests(unittest.TestCase):
    def test_patches_all_three_sites_mt1_it1_and_tw(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            original = (
                MT1_ORIGINAL + b"...filler..." + IT1_ORIGINAL + b"...filler..." + TW_ANCHOR_ORIGINAL
            )
            droid = _write_droid(home, original)

            result = _run(SCRIPT, home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched = droid.read_bytes()

            # mT1+iT1 是 +0 byte（通过 padding）；tw 是 +31 byte
            self.assertEqual(len(patched) - len(original), 31)

            # 三处都注入了 core 标记
            self.assertIn(MT1_CORE, patched)
            self.assertIn(IT1_CORE, patched)
            self.assertIn(TW_CORE, patched)

            # 工厂区 header / toggle-builtins / 原 tw=Yd() 已不再出现
            self.assertNotIn(b'common:modelSelector.factoryModelsHeader', patched)
            self.assertNotIn(b'common:modelSelector.customModelsHeader', patched)
            self.assertNotIn(b'common:missionModelPicker.recommendedHeader', patched)
            self.assertNotIn(b'toggle-builtins', patched)
            self.assertNotIn(b',tw=Yd(),', patched)
            self.assertIn(TW_ANCHOR_PATCHED, patched)

            # 留下了至少两段较长的 /* spaces */ padding 供 comp_universal 消费
            import re as _re
            paddings = sorted(
                len(m.group(1)) for m in _re.finditer(rb'/\*( +)\*/', patched)
            )
            self.assertGreaterEqual(len(paddings), 2)
            self.assertGreaterEqual(paddings[-1], 400, f'padding sizes={paddings}')

            # status 报告 modified
            status = _run(STATUS, home)
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            self.assertIn("mod-cycle-custom-model: 已修改", status.stdout)

    def test_idempotent_on_already_patched_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            droid = _write_droid(home, MT1_ORIGINAL + IT1_ORIGINAL + TW_ANCHOR_ORIGINAL)

            first = _run(SCRIPT, home)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            after_first = droid.read_bytes()

            second = _run(SCRIPT, home)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("已应用", second.stdout)
            self.assertEqual(droid.read_bytes(), after_first)

    def test_incremental_apply_tw_only_when_mt1_it1_already_patched(self) -> None:
        """真实场景：mT1/iT1 已 patch（旧版本），tw 新增。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            # 构造一个“mT1/iT1 已替换成 core + padding, tw 仍是原样”的半成品
            mt1_applied = MT1_CORE + b'/*' + b' ' * 20 + b'*/'
            it1_applied = IT1_CORE + b'/*' + b' ' * 20 + b'*/'
            original = (
                mt1_applied + b"...filler..." + it1_applied + b"...filler..." + TW_ANCHOR_ORIGINAL
            )
            droid = _write_droid(home, original)

            result = _run(SCRIPT, home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched = droid.read_bytes()
            # mT1/iT1 未被二次修改；tw 已切换
            self.assertIn(mt1_applied, patched)
            self.assertIn(it1_applied, patched)
            self.assertIn(TW_CORE, patched)
            self.assertNotIn(b',tw=Yd(),', patched)

    def test_patches_remaining_selector_when_tw_already_patched(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            mt1_applied = MT1_CORE + b'/*' + b' ' * 20 + b'*/'
            original = mt1_applied + b"...filler..." + IT1_ORIGINAL + b"...filler..." + TW_ANCHOR_PATCHED
            droid = _write_droid(home, original)

            result = _run(SCRIPT, home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched = droid.read_bytes()
            self.assertIn(mt1_applied, patched)
            self.assertIn(IT1_CORE, patched)
            self.assertNotIn(b'common:missionModelPicker.recommendedHeader', patched)
            self.assertNotIn(b'toggle-builtins', patched)

    def test_status_reports_partial_when_only_one_selector_is_patched(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            mt1_applied = MT1_CORE + b'/*' + b' ' * 20 + b'*/'
            droid = _write_droid(home, mt1_applied + b"...filler..." + IT1_ORIGINAL + b"...filler..." + TW_ANCHOR_PATCHED)

            status = _run(STATUS, home)
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            self.assertIn("mod-cycle-custom-model: 部分修改", status.stdout)

    def test_patches_v104_style_selector_and_tw(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            original = SELECTOR_104_ORIGINAL + b"...filler..." + TW_104_ORIGINAL
            droid = _write_droid(home, original)

            result = _run(SCRIPT, home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched = droid.read_bytes()
            self.assertEqual(len(patched) - len(original), len(TW_104_PATCHED) - len(TW_104_ORIGINAL))
            self.assertIn(SELECTOR_104_CORE, patched)
            self.assertIn(TW_104_CORE, patched)
            self.assertNotIn(b'common:modelSelector.factoryModelsHeader', patched)
            self.assertNotIn(b'toggle-builtins', patched)
            self.assertIn(TW_104_PATCHED, patched)

            status = _run(STATUS, home)
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            self.assertIn("mod-cycle-custom-model: 已修改", status.stdout)

    def test_patches_duplicate_tw_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            original = (
                MT1_ORIGINAL + b"...filler..." + IT1_ORIGINAL + b"...filler..."
                + TW_ANCHOR_ORIGINAL + b"...duplicate..." + TW_ANCHOR_ORIGINAL
            )
            droid = _write_droid(home, original)

            result = _run(SCRIPT, home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched = droid.read_bytes()
            self.assertEqual(patched.count(TW_CORE), 2)
            self.assertNotIn(TW_ANCHOR_ORIGINAL, patched)

            status = _run(STATUS, home)
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            self.assertIn("mod-cycle-custom-model: 已修改", status.stdout)

    def test_patches_v130_cycle_candidates_without_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            original = b"prefix" + CYCLE_130_ORIGINAL + b"updateSettings(H){suffix"
            droid = _write_droid(home, original)

            result = _run(SCRIPT, home)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            patched = droid.read_bytes()
            self.assertEqual(len(patched), len(original))
            self.assertIn(CYCLE_130_CORE, patched)
            self.assertNotIn(CYCLE_130_ORIGINAL, patched)

            status = _run(STATUS, home)
            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            self.assertIn("mod-cycle-custom-model: 已修改", status.stdout)

    def test_status_detects_v130_cycle_candidates_as_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            _write_droid(home, CYCLE_130_ORIGINAL)

            status = _run(STATUS, home)

            self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
            self.assertIn("mod-cycle-custom-model: 原版", status.stdout)

    def test_fails_loudly_when_pattern_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            _write_droid(home, b"random bytes with no selector pattern at all")

            result = _run(SCRIPT, home)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("pattern not found", result.stdout)


if __name__ == "__main__":
    unittest.main()
