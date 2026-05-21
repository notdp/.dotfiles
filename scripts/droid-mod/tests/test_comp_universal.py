import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path("/Users/zhenninglang/.dotfiles/scripts/droid-mod/compensations/comp_universal.py")

spec = importlib.util.spec_from_file_location("comp_universal", SCRIPT)
comp_universal = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(comp_universal)


SAMPLE_BYTES = (
    b'if(!0||!D)return{text:H,isTruncated:!1}'
    + b'x' * 86
    + b'isTruncated:!0}'
    + b'substring(0,2000)'
    + b'),!0}if(wH)return      !1}return!1'
    + b'"dim-bold":{color:"#FFA500"/*    */,'
    + b'logo:{color:"#FFA500"    ,'
)
CALLBACK_RETURN_BYTES = (
    b'if(BH&&hR.downArrow&&lR){let GR=BH.navigateNext();return!0}}'
    b'if(hR.downArrow&&lR&&kH)return !!kH() ;return!1}return!1}'
)


class CompUniversalTests(unittest.TestCase):
    def test_find_regions_includes_all_known_padding_sources(self) -> None:
        regions = comp_universal.find_regions(SAMPLE_BYTES)
        capacities = {
            name: len(old_bytes) - min_size
            for name, _offset, old_bytes, min_size, _rtype in regions
        }

        self.assertEqual(capacities["截断函数死代码"], 100)
        self.assertEqual(capacities["substring 长度"], 3)
        self.assertEqual(capacities["多行历史空白填充"], 6)
        self.assertEqual(capacities["dim-bold 颜色填充"], 8)
        self.assertEqual(capacities["logo 颜色填充"], 4)
        self.assertEqual(sum(capacities.values()), 121)

    def test_compensate_can_consume_padding_regions(self) -> None:
        patched, actual = comp_universal.compensate(SAMPLE_BYTES, 121)

        self.assertEqual(actual, -121)
        self.assertIn(b"substring(0,2)", patched)
        self.assertNotIn(b"return      !1", patched)
        self.assertNotIn(b'/*    */', patched)
        self.assertNotIn(b'"#FFA500"    ,', patched)

    def test_find_regions_includes_callback_return_padding(self) -> None:
        regions = comp_universal.find_regions(CALLBACK_RETURN_BYTES)
        capacities = {
            name: len(old_bytes) - min_size
            for name, _offset, old_bytes, min_size, _rtype in regions
        }

        self.assertEqual(capacities["多行历史 callback 填充"], 1)


if __name__ == "__main__":
    unittest.main()
