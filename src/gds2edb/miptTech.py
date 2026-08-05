
#--- coding=utf-8
#--- @author: yongsheng.guo@synopsys.com
#--- @Time: ver 6.0 20260628
'''
解析mipt工艺文件："C:\work\Project\AE\Script\gds2edb\PEX_65&40\65\MIPT\calibrexrc_65_1P3M_2Ic_1TTMc1_ALPA2_TYP.mipt"
参照IRCXTech.py的实现，解析mipt工艺文件，生成techBase
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


def _parse_block_properties(block_text: str) -> Dict[str, str]:
	props: Dict[str, str] = {}
	for raw in block_text.splitlines():
		line = raw.strip()
		if not line or line.startswith("#") or "=" not in line:
			continue
		key, value = line.split("=", 1)
		key = key.strip()
		value = value.strip()
		if value.startswith("{") and value.endswith("}"):
			value = value[1:-1].strip()
		props[key] = value
	return props


def _read_mipt_blocks(path: str) -> Tuple[str, List[Dict[str, object]]]:
	with open(path, "r", encoding="utf-8") as f:
		text = f.read()

	process_name = ""
	m = re.search(r"(?m)^\s*process\s*=\s*(.+?)\s*$", text)
	if m:
		process_name = m.group(1).strip()

	block_pattern = re.compile(r"(?ms)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^\s{]+)\s*\{(.*?)\}")
	blocks: List[Dict[str, object]] = []
	for match in block_pattern.finditer(text):
		kind = match.group(1).strip().lower()
		name = match.group(2).strip()
		body = match.group(3)
		blocks.append(
			{
				"kind": kind,
				"name": name,
				"props": _parse_block_properties(body),
			}
		)
	return process_name, blocks


class MiptTech(TechBase):
	def __init__(self, path: Optional[str] = None):
		super(MiptTech, self).__init__()
		self.path = path
		self.parsed = False
		if path:
			self.parse(path)

	def _new_layer(self) -> Dict[str, object]:
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

	def _lookup(self, name: Optional[str]):
		if not name:
			return None
		return self.findLayer(name, "all")

	def _resolve_height(self, props: Dict[str, str], cursor):
		thickness = _to_decimal(props.get("thickness"), Decimal("0"))
		zbottom = _to_decimal(props.get("zbottom"), None)
		if zbottom is not None:
			return zbottom

		ztop = _to_decimal(props.get("ztop"), None)
		if ztop is not None:
			return ztop - thickness

		measured_from = props.get("measured_from")
		from_layer = self._lookup(measured_from)
		if from_layer:
			return Decimal(str(from_layer["Height"])) + Decimal(str(from_layer["Thickness"]))

		return cursor

	def _calc_cond_from_sheet(self, props: Dict[str, str], thickness):
		r_sheet = _to_decimal(props.get("r_sheet"), None)
		if r_sheet in [None, 0] or thickness in [None, 0]:
			return None
		return Decimal("1000000") / (r_sheet * thickness)

	def parse(self, path: Optional[str] = None):
		if self.parsed:
			return
		super(MiptTech, self).__init__()
		self.parsed = True

		path = path or self.path
		if not path:
			log.info("MIPT path is required")
			return

		process_name, blocks = _read_mipt_blocks(path)
		self.Tech["Header"]["Process"] = process_name

		cursor = Decimal("0")
		tref = Decimal("25")

		for block in blocks:
			kind = block["kind"]
			name = block["name"]
			props = block["props"]

			# Dielectrics
			if kind in ["base", "dielectric"]:
				layer = self._new_layer()
				thickness = _to_decimal(props.get("thickness"), Decimal("0"))
				height = self._resolve_height(props, cursor)
				layer["LayerName"] = name
				layer["Type"] = "Dielectric"
				layer["Thickness"] = thickness
				layer["Height"] = height
				layer["DK"] = _to_decimal(props.get("eps"), Decimal("1"))
				layer["Tref"] = tref
				self.Tech["Dielectrics"].append(layer)
				cursor = max(cursor, height + thickness)
				continue

			# Conductors (poly/diffusion are conductive layers in MIPT)
			if kind in ["conductor", "poly", "diffusion"]:
				layer = self._new_layer()
				thickness = _to_decimal(props.get("thickness"), Decimal("0"))
				height = self._resolve_height(props, cursor)
				layer["LayerName"] = name
				layer["Type"] = "Conductor"
				layer["Thickness"] = thickness
				layer["Height"] = height
				layer["Cond"] = self._calc_cond_from_sheet(props, thickness)
				layer["TC1"] = _to_decimal(props.get("tc1"), None)
				layer["TC2"] = _to_decimal(props.get("tc2"), None)
				layer["Tref"] = tref
				self.Tech["Conductors"].append(layer)
				cursor = max(cursor, height + thickness)
				continue

			# Through/contact layers
			if kind in ["via", "derived"]:
				measured_from = props.get("measured_from")
				measured_to = props.get("measured_to")
				if not measured_from or not measured_to:
					continue

				lower = self._lookup(measured_from)
				upper = self._lookup(measured_to)
				if not lower or not upper:
					continue

				lower_top = Decimal(str(lower["Height"])) + Decimal(str(lower["Thickness"]))
				upper_top = Decimal(str(upper["Height"])) + Decimal(str(upper["Thickness"]))
				thickness = abs(upper_top - lower_top)

				width = _to_decimal(props.get("min_width"), None)
				resistance = _to_decimal(props.get("resistance"), None)
				cond = None
				if resistance not in [None, 0] and width not in [None, 0] and thickness not in [None, 0]:
					# Approximate via conductivity from R = rho * L / A, A ~ w^2
					cond = Decimal("1000000") * thickness / (resistance * width * width)

				layer = self._new_layer()
				layer["LayerName"] = name
				layer["Type"] = "Via"
				layer["LowerLayer"] = measured_from
				layer["UpperLayer"] = measured_to
				layer["Thickness"] = thickness
				layer["Height"] = min(lower_top, upper_top)
				layer["Cond"] = cond
				layer["TC1"] = _to_decimal(props.get("tc1"), None)
				layer["TC2"] = _to_decimal(props.get("tc2"), None)
				layer["Tref"] = tref
				self.Tech["Vias"].append(layer)


if __name__ == "__main__":
	mipt_path = r"C:\work\Project\AE\Script\gds2edb\PEX_65&40\65\MIPT\calibrexrc_65_1P3M_2Ic_1TTMc1_ALPA2_TYP.mipt"
	mipt = MiptTech(mipt_path)
	mipt.parse()
	mipt.toCSV(r"C:\work\Project\AE\Script\gds2edb\PEX_65&40\65\MIPT\calibrexrc_65_1P3M_2Ic_1TTMc1_ALPA2_TYP.csv")

