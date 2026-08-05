#--- coding=utf-8
#--- @author: yongsheng.guo@synopsys.com
#--- @Time: ver 6.0 20260628
'''
解析layermap "C:\work\Project\AE\Script\gds2edb\itf2\65RFSOI.layermap" 
存放到字典中 ComplexDict({M5:[{LayerName:M5, LayerMap:122;40, LayerPurpose:drawing}]})
忽略注释行（#开头）和空行，LayerMap为Layer Stream Number;Datatype Stream Number的组合
LayerName可以存在重复项，因此需要用{LayerName: [ ... ]}的形式存放
参考option.py的实现

#Layer Name     Layer Purpose  Layer Stream Number  Datatype Stream Number
ALPA           drawing        83                   0
viaPA             drawing        79                   0
M5           drawing        122                  40
V4           drawing        123                  40
M4           drawing        120                  40
V3           drawing        121                  40
MIM            drawing        58                   0
MIM_P2       drawing         31                  0                         
M3             drawing        63                   0              
V2             drawing        71                   0              
M2             drawing        62                   0              
V1             drawing        70                   0              
M1             drawing        61                   0              
GT             drawing        30                   0              
AA             drawing        10                   0              
CT             drawing        50                   0
'''

from typing import Dict, List, Optional

from pyLayout import ComplexDict, log


class LayerMap(ComplexDict):
    def __init__(self, data: Optional[object] = None):
        ComplexDict.__init__(self)
        self.maps = {}

        if not data:
            return

        if isinstance(data, dict):
            self._dict = data
            return

        if isinstance(data, ComplexDict):
            self._dict = data.copy()._dict
            return

        if isinstance(data, str):
            self.readLayermap(data)
            return

        log.exception("Invalid layermap input: %s" % str(data))

    def readLayermap(self, path: str) -> Dict[str, List[Dict[str, str]]]:
        parsed: Dict[str, List[Dict[str, str]]] = {}
        maps: Dict[str, str] = {}
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                # Expected columns:
                # Layer Name | Layer Purpose | Layer Stream Number | Datatype Stream Number
                if len(parts) < 4:
                    continue

                layer_name = parts[0]
                layer_purpose = parts[1]
                stream_number = parts[2]
                datatype_number = parts[3]

                entry = {
                    "LayerName": layer_name,
                    "LayerMap": "%s;%s" % (stream_number, datatype_number),
                    "LayerPurpose": layer_purpose,
                }

                if layer_name not in parsed:
                    parsed[layer_name] = []
                parsed[layer_name].append(entry)

                # 如果layer_name是M\d+，比如M1则将其映射到maps中为{metal1:M1:}
                # 如果layer_name是V\d+，比如V1则将其映射到maps中为{via1:V1}
                if layer_name.startswith("M") and layer_name[1:].isdigit():
                    maps["metal" + layer_name[1:]] = layer_name
                elif layer_name.startswith("V") and layer_name[1:].isdigit():
                    maps["via" + layer_name[1:]] = layer_name

        self.updates(parsed)
        self.setMaps(maps)
        return parsed

if __name__ == "__main__":
    path = r"C:\work\Project\AE\Script\gds2edb\itf2\65RFSOI.layermap"
    lm = LayerMap(path)
    print(lm.get("M5"))
