
#--- coding=utf-8
#--- @author: yongsheng.guo@synopsys.com
#--- @Time: ver 6.0 20260628
'''
解析ict工艺文件："C:\work\Project\AE\Script\gds2edb\PEX_65&40\65\ICT\QRC_65_1P5M_3Ic_2TTMc2_ALPA2_TYP.ict"
参照IRCXTech.py的实现，解析ict工艺文件，生成techBase
实现需求并进行toCSV测试
'''

import re
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from pyLayout import log

from techBase import TechBase


def _to_decimal(value, default=None):
	if isinstance(default, Decimal):
		default_value = default
	elif default is None:
		default_value = None
	else:
		default_value = Decimal(str(default))

	if value in [None, "", "None", "N/A"]:
		return default_value
	try:
		return Decimal(str(value).strip())
	except Exception:
		return default_value


def _parse_key_value_line(line: str) -> Optional[Tuple[str, str]]:
	clean = line.strip()
	if not clean or clean.startswith("#") or clean.endswith("{") or clean == "}":
		return None
	parts = clean.split()
	if len(parts) < 2:
		return None
	return parts[0].strip(), " ".join(parts[1:]).strip()


def _extract_balanced_block(lines: List[str], start_idx: int) -> Tuple[str, int]:
	brace = 0
	body: List[str] = []
	i = start_idx
	while i < len(lines):
		line = lines[i]
		brace += line.count("{")
		brace -= line.count("}")
		body.append(line)
		i += 1
		if brace == 0:
			break
	return "\n".join(body), i


def _extract_named_blocks(text: str, keywords: List[str]) -> List[Dict[str, str]]:
	lines = text.splitlines()
	i = 0
	blocks: List[Dict[str, str]] = []
	pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+([^\s{]+)\s*\{")
	keyword_set = {k.lower() for k in keywords}

	while i < len(lines):
		line = lines[i]
		m = pattern.match(line)
		if m and m.group(1).lower() in keyword_set:
			kind = m.group(1).lower()
			name = m.group(2)
			block_text, next_i = _extract_balanced_block(lines, i)
			first_brace = block_text.find("{")
			last_brace = block_text.rfind("}")
			body = block_text[first_brace + 1:last_brace] if first_brace >= 0 and last_brace >= 0 else ""
			blocks.append({"kind": kind, "name": name, "body": body})
			i = next_i
			continue
		i += 1

	return blocks


def _parse_flat_props(block_body: str) -> Dict[str, str]:
	props: Dict[str, str] = {}
	depth = 0
	for raw in block_body.splitlines():
		line = raw.strip()
		if not line or line.startswith("#"):
			continue

		opens = line.count("{")
		closes = line.count("}")
		kv = _parse_key_value_line(line)
		if depth == 0 and kv:
			k, v = kv
			props[k] = v

		depth += opens
		depth -= closes
		if depth < 0:
			depth = 0

	return props


def _new_layer() -> Dict[str, object]:
	return {
		"LayerName": None,
		"Type": None,
		"LayerMap": None,
		"TextLayerMap": None,
		"Thickness": None,
		"Height": None,
		"LowerLayer": None,
		"UpperLayer": None,
		"DK": None,
		"DF": None,
		"Cond": None,
		"TC1": None,
		"TC2": None,
		"Tref": None,
	}


class IctTech(TechBase):
	def __init__(self, path: Optional[str] = None):
		super(IctTech, self).__init__()
		self.path = path
		self.parsed = False
		if path:
			self.parse(path)

	def _calc_conductor_cond(self, props: Dict[str, str], thickness):
		resistivity = _to_decimal(props.get("resistivity"), None)
		if resistivity in [None, 0] or thickness in [None, 0]:
			return None
		return 1e6 / (float(resistivity) * float(thickness))

	def _lookup(self, name: Optional[str]):
		if not name:
			return None
		return self.findLayer(name, "all")

	def _append_conductor(self, name: str, props: Dict[str, str], tref):
		layer = _new_layer()
		thickness = _to_decimal(props.get("thickness"), Decimal("0"))
		layer["LayerName"] = name
		layer["Type"] = "Conductor"
		layer["Thickness"] = thickness
		layer["Height"] = _to_decimal(props.get("height"), Decimal("0"))
		layer["Cond"] = self._calc_conductor_cond(props, thickness)
		layer["TC1"] = _to_decimal(props.get("temp_tc1"), None)
		layer["TC2"] = _to_decimal(props.get("temp_tc2"), None)
		layer["Tref"] = tref
		self.Tech["Conductors"].append(layer)

	def _append_dielectric(self, name: str, props: Dict[str, str], tref):
		layer = _new_layer()
		layer["LayerName"] = name
		layer["Type"] = "Dielectric"
		layer["Thickness"] = _to_decimal(props.get("thickness"), Decimal("0"))
		layer["Height"] = _to_decimal(props.get("height"), Decimal("0"))
		layer["DK"] = _to_decimal(props.get("dielectric_constant"), Decimal("1"))
		layer["Tref"] = tref
		self.Tech["Dielectrics"].append(layer)

	def _append_via(self, name: str, props: Dict[str, str], tref):
		lower_name = props.get("bottom_layer")
		upper_name = props.get("top_layer")
		if not lower_name or not upper_name:
			return

		lower = self._lookup(lower_name)
		upper = self._lookup(upper_name)
		if not lower or not upper:
			return

		lower_top = Decimal(str(lower["Height"])) + Decimal(str(lower["Thickness"]))
		upper_top = Decimal(str(upper["Height"])) + Decimal(str(upper["Thickness"]))
		thickness = abs(upper_top - lower_top)

		width = _to_decimal(props.get("min_width"), None)
		resistance = _to_decimal(props.get("contact_resistance"), None)
		cond = None
		if resistance not in [None, 0] and width not in [None, 0] and thickness not in [None, 0]:
			cond = Decimal("1000000") * thickness / (resistance * width * width)

		layer = _new_layer()
		layer["LayerName"] = name
		layer["Type"] = "Via"
		layer["LowerLayer"] = lower_name
		layer["UpperLayer"] = upper_name
		layer["Thickness"] = thickness
		layer["Height"] = min(lower_top, upper_top)
		layer["Cond"] = cond
		layer["Tref"] = tref
		self.Tech["Vias"].append(layer)

	def parse(self, path: Optional[str] = None):
		if self.parsed:
			return
		super(IctTech, self).__init__()
		self.parsed = True

		path = path or self.path
		if not path:
			log.info("ICT path is required")
			return

		with open(path, "r", encoding="utf-8") as f:
			text = f.read()

		process_blocks = _extract_named_blocks(text, ["process"])
		tref = Decimal("25")
		if process_blocks:
			process_props = _parse_flat_props(process_blocks[0]["body"])
			self.Tech["Header"]["Process"] = process_blocks[0]["name"]
			tref = _to_decimal(process_props.get("temp_reference"), Decimal("25"))

		# Parse conductors and nested sub_conductors.
		for block in _extract_named_blocks(text, ["conductor"]):
			parent_props = _parse_flat_props(block["body"])
			self._append_conductor(block["name"], parent_props, tref)

			for sub in _extract_named_blocks(block["body"], ["sub_conductor"]):
				sub_props = parent_props.copy()
				sub_props.update(_parse_flat_props(sub["body"]))
				self._append_conductor(sub["name"], sub_props, tref)

		for block in _extract_named_blocks(text, ["dielectric"]):
			self._append_dielectric(block["name"], _parse_flat_props(block["body"]), tref)

		# Parse vias and nested sub_vias.
		for block in _extract_named_blocks(text, ["via"]):
			parent_props = _parse_flat_props(block["body"])
			self._append_via(block["name"], parent_props, tref)

			for sub in _extract_named_blocks(block["body"], ["sub_via"]):
				sub_props = parent_props.copy()
				sub_props.update(_parse_flat_props(sub["body"]))
				self._append_via(sub["name"], sub_props, tref)


if __name__ == "__main__":
	ict_path = r"C:\work\Project\AE\Script\gds2edb\PEX_65&40\65\ICT\QRC_65_1P5M_3Ic_2TTMc2_ALPA2_TYP.ict"
	ict = IctTech(ict_path)
	ict.parse()
	ict.toCSV(r"C:\work\Project\AE\Script\gds2edb\PEX_65&40\65\ICT\QRC_65_1P5M_3Ic_2TTMc2_ALPA2_TYP.csv")
