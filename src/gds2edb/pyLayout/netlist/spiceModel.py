#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20260131

import re
from functools import partial


from ..common.common import log,readData,writeData
from ..common.complexDict import ComplexDict
from ..common.progressBar import ProgressBar

#  定义一个全局辅助函数，用于在子进程中解析单行
# 必须定义在模块级别，以便 pickle 能够找到它
def _parse_element_line(line):
    """
    Helper function for multiprocessing. 
    Parses a single line and returns a lightweight tuple/dict.
    Returns None if line is invalid or comment.
    """
    if not line or line.startswith('*'):
        return None
    
    try:
        # Reuse the logic from Element.parse but return raw data to avoid object overhead in subprocess
        # We create a temporary Element just to parse, then extract data
        # Or better, implement a static fast parser here.
        # For simplicity and consistency, let's use a simplified parser here 
        # that mirrors Element._parse_simple/_parse_complex
        
        # Fast check for type
        first_char = line[0]
        if not first_char.isalpha():
            stripped = line.lstrip()
            if not stripped: return None
            first_char = stripped[0]
            
        elem_type = first_char.upper()
        
        # Simple split for most cases
        if '=' not in line and '"' not in line and "'" not in line:
            parts = line.split()
            if len(parts) < 2: return None
            
            name = parts[0]
            nodes = []
            value = None
            params = []
            
            if elem_type in ["R", "L", "C", "K", "G", "V", "I"]:
                if len(parts) >= 3:
                    nodes = [parts[1], parts[2]]
                if len(parts) >= 4:
                    params = parts[3:]
                    value = params[0]
                    
            elif elem_type == "X":
                if len(parts) >= 3:
                    nodes = parts[1:-1]
                    params = parts[-1] # Subckt name
            
            else:
                # Skip unsupported types or handle generically
                return None
                
            return (name, elem_type, nodes, value, params, line)
            
        else:
            # Fallback to regex for complex lines
            pattern = r'(["\'].*?["\'])|(\w+\s*=\s*\S+)|(\S+)'
            matches = re.findall(pattern, line)
            result = [''.join(match).strip() for match in matches if ''.join(match).strip()]
            
            if not result: return None
            
            name = result[0]
            nodes = []
            value = None
            params = []
            
            if elem_type in ["R", "L", "C", "K", "G", "V", "I"]:
                if len(result) >= 3:
                    nodes = result[1:3]
                if len(result) >= 4:
                    params = result[3:]
                    value = params[0]
                    
            elif elem_type == "X":
                if len(result) > 2:
                    nodes = result[1:-1]
                    params = result[-1]
            
            else:
                return None
                
            return (name, elem_type, nodes, value, params, line)

    except Exception:
        return None


class Element(object):
    """
    Represents a single SPICE circuit element.
    Optimized for high-volume parsing using __slots__ and fast-path string splitting.
    """
    __slots__ = ['Data', 'Name', 'Nodes', 'Params', 'Type', 'Value']

    def __init__(self, data=None):
        self.Data = data
        self.Name = None
        self.Nodes = []
        self.Params = []
        self.Type = None
        self.Value = None

        if data:
            self.parse(data)

    def parse(self, data=None):
        """
        Parses the SPICE element string.
        Uses a fast split() path for standard elements and regex for complex parameters.
        """
        data = data or self.Data
        if not data:
            return
            
        # Handle list/tuple input (multi-line continuation)
        if isinstance(data, (list, tuple)):
            temp = []
            for line in data:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("+"):
                    temp.append(line[1:])
                elif line.startswith("*"):
                    continue
                else:
                    temp.append(line)
            if not temp:
                return
            data = " ".join(temp)

        if not isinstance(data, str) or not data.strip():
            return
        
        # 1. Determine Type
        first_char = data[0]
        # Handle optional leading whitespace or special chars if any, but usually Type is first
        if not first_char.isalpha():
             # Try to find first alpha char if there's leading space/comment residue
             stripped = data.lstrip()
             if stripped:
                 first_char = stripped[0]
             else:
                 return
                 
        self.Type = first_char.upper()

        # 2. Fast Path vs Slow Path
        # Regex is slow. Most SPICE lines are simple: "Name Node1 Node2 Value"
        # We only use regex if there are '=' signs (parameters) or quotes.
        if '=' in data or '"' in data or "'" in data:
            self._parse_complex(data)
        else:
            self._parse_simple(data)

    def _parse_simple(self, data):
        """
        Fast parsing using split() for standard R, L, C, V, I, X elements without complex params.
        """
        parts = data.split()
        if len(parts) < 2:
            return

        self.Name = parts[0]
        
        # Standard 2-terminal elements: R, L, C, V, I, G, K
        if self.Type in ["R", "L", "C", "K", "G", "V", "I"]:
            if len(parts) >= 3:
                self.Nodes = [parts[1], parts[2]]
            else:
                self.Nodes = []
            
            if len(parts) >= 4:
                self.Params = parts[3:]
                self.Value = self.Params[0]
            else:
                self.Params = []
                self.Value = None

        # Subcircuit instances: X
        elif self.Type == "X":
            if len(parts) >= 3:
                # Nodes are everything between Name and the last token (Subckt Name)
                self.Nodes = parts[1:-1]
                self.Params = parts[-1] # Subckt name
                self.Value = None
            else:
                self.Nodes = []
                self.Params = ""

        else:
            # Fallback for unknown types or malformed lines
            # Log warning if necessary, but for speed we might skip
            pass

    def _parse_complex(self, data):
        """
        Parsing using Regex for elements with parameters (e.g., R1 N1 N2 R=1k TC=0.01)
        or quoted strings.
        """
        # Pattern explanation:
        # 1. (["'].*?["']) : Match quoted strings
        # 2. (\w+\s*=\s*\S+) : Match Key=Value pairs
        # 3. (\S+) : Match standard tokens
        pattern = r'(["\'].*?["\'])|(\w+\s*=\s*\S+)|(\S+)'
        matches = re.findall(pattern, data)
        
        # Flatten the match groups and filter empty strings
        result = []
        for match in matches:
            # match is a tuple of 3 groups, only one is non-empty
            token = ''.join(match).strip()
            if token:
                result.append(token)

        if not result:
            return

        self.Name = result[0]

        if self.Type in ["R", "L", "C", "K", "G", "V", "I"]:
            if len(result) >= 3:
                self.Nodes = result[1:3]
            else:
                self.Nodes = []
            
            if len(result) >= 4:
                self.Params = result[3:]
                self.Value = self.Params[0]
            else:
                self.Params = []
                self.Value = None

        elif self.Type == "X":
            if len(result) > 2:
                self.Nodes = result[1:-1]
                self.Params = result[-1]
                self.Value = None
            else:
                self.Nodes = []
                self.Params = ""


class Node(object):

    __slots__ = ['Name', 'Elements']
    def __init__(self,name=None):
        self.Name = name
        self.Elements = []
    def addElement(self,ele):
        self.Elements.append(ele)
        

class Elements(ComplexDict):

    def __init__(self):
        super(Elements,self).__init__()

    def add(self,ele):
        self._dict[ele.Name] = ele
    
    def update(self,ele):
        if ele.Name in self:
            self.remove(self._dict[ele.Name])
        self.add(ele)

    def remove(self,ele):
        if isinstance(ele,Element):
            eleName = ele.Name
        elif isinstance(ele,str):
            eleName = ele
        else:
            log.exception("Invalid element %s"%str(ele))
            return

        try:
            del self._dict[eleName]
        except:
            log.error("Element %s not found"%eleName)

    def has(self,eleName):
        return eleName in self


class Nodes(ComplexDict):
    
    # __slots__ = ['_dict', 'maps', 'ignorCase','Elements_NodeNames']
    def __init__(self,dictData=None):
        super(Nodes,self).__init__(dictData)

    def add(self,nodeName):
        self._dict[nodeName] = []

    def has(self,nodeName):
        return self.__contains__()

def blockLinesGenerator(lines, flag = [".subckt",".ends"] , comment = "*"):
    '''''_summary_''
    Args:
        strDatas (_type_): _description_
        flag (list, optional): "{}" , [".subckt",".ends"].
        comment (str, optional): _description_. Defaults to "$".
    '''

    pos = 0
    total = len(lines)-1
    
    while pos<total:
#         count = 0
        temp = []
        
        #read first {
        while not lines[pos].strip().lower().startswith(flag[0]):
#             temp += lines[pos]
            
            if pos<total:
                pos += 1
            else:
                yield []
                return            
        
        temp.append(lines[pos])
        pos += 1
        count = 1
        
        while count:
            
            if lines[pos].strip().lower().startswith(flag[0]):
                count += 1
    
            if lines[pos].strip().lower().startswith(flag[-1]):
                count -= 1
            
            temp.append(lines[pos])
            
            if count<1:
                yield temp
                pos += 1
                break
            
            if pos<total:
                pos += 1
            else:
                break


class Subckt(object):
    def __init__(self,datas=None):
        self.datas = datas #include headerNodes and elements
        self.name = ""
        self.headerNodes = [] #nodes in subckt
        self.elements = Elements()
        self.nodes = Nodes() #spice nodes in netlist
        if datas:
            self.parse()
        
    def parse(self, datas=None):
        """
        解析给定路径下的电路描述文件，并提取.subckt行以及其节点信息。
        
        参数:
        - path: str, 文件路径。如果未提供，则使用self.path。
        
        没有返回值，但更新self.name和self.nodes属性。
        """
        # 确定要读取的文件路径
        datas = datas or self.datas

        # 初始化存储每行数据的列表
        lines = []
        # 分行处理数据
        for l in datas:
            # 去除行首尾的空白字符
            line = l.strip()
            # 跳过空行
            if not line:
                continue
            
            # 跳过以"*"开头的行
            if line.startswith("*"):
                continue
            
            # 处理以"+"开头的行，将其余下部分与上一行合并
            if line.startswith("+"):
                if not lines:
                    continue
                lines[-1] += " " + line[1:]
                continue
            
            # 将处理后的行添加到lines列表中
            lines.append(line)
        
        # # 查找.subckt行
        # header = ""
        # for line in lines:
        #     if line.lower().startswith(".subckt"):
        #         header = line
        #         break

        header = lines[0]
        if not header.lower().startswith(".subckt"):
            log.exception("Invalid .subckt defition: %s"%header)

        # 分割header行，提取子电路的名称和节点
        splits = header.split()
        self.name = splits[1]
        self.headerNodes = splits[2:]
        self.datas = lines

    def addNode(self, nodeName):
        self.headerNodes.append(nodeName)
        self.datas[0] = self.datas[0]+" "+nodeName

    def addNetlist(self, netlist):
        self.datas.insert(-1,netlist)

    def generateNodes(self):
        
        log.info("update netlist nodes...")
        self.nodes = Nodes()
        bar = ProgressBar(self.elements.Count,"update netlist nodes:")
        for ele in self.elements.values():
            bar.showPercent()
            for node in ele.Nodes: 
                if node not in self.nodes:
                    self.nodes.add(node)
                self.nodes[node].append(ele)

        bar.stop()
        
    def update(self):
        '''当element发生变化时，调用此方法跟新subckt结构
        '''
        #update data
        log.info("Update %s data"%self.name)
        datas = []
        # datas.append(".subckt {0} {1}".format(self.name,"\n".join(["+ %s"%node for node in self.headerNodes]))) #.subckt
        datas.append(".subckt {0} {1}".format(self.name," ".join(self.headerNodes))) #.subckt
        datas.extend([ele.Data for ele in self.elements])    # elements
        datas.append(self.datas[-1]) #.ends
        self.datas = datas
    
    
    # def parseAll(self):
    #     if not self.datas:
    #         self.parse()
        
    #     if not self.datas:
    #         log.info("No data to parse")
    #         return
    #     lines = self.datas[1:-1]
    #     log.info("Pasre full spice netlist...")
    #     bar = ProgressBar(len(lines),"Spice netlist parse models:")
    #     for line in lines:
    #         bar.showPercent()
    #         ele = Element(line)
    #         self.elements.add(ele)
    #     bar.stop()
        
    #     # self.generateNodes()
        
    def parseAll(self, use_multiprocessing=True, chunk_size=5000):
        """
        Parse all elements in the subcircuit.
        
        Args:
            use_multiprocessing (bool): Whether to use multi-core processing.
            chunk_size (int): Number of lines per chunk for parallel processing.
        """
        if not self.datas:
            self.parse()
        
        if not self.datas:
            log.info("No data to parse")
            return
            
        lines = self.datas[1:-1]
        total_lines = len(lines)
        
        if total_lines == 0:
            return

        log.info("Parsing full spice netlist (%d elements)..." % total_lines)
        
        parsed_data_list = []
        
        # Decision: Use Multiprocessing or Single Process?
        # Overhead of multiprocessing is significant for small lists.
        if use_multiprocessing and total_lines > chunk_size:
            import multiprocessing as mp
            try:
                # Split lines into chunks
                chunks = [lines[i:i + chunk_size] for i in range(0, total_lines, chunk_size)]
                
                # Use Pool
                # Note: On Windows, this must be protected by if __name__ == '__main__' in the caller,
                # but since this is inside a class method called from main, it should be fine.
                with mp.Pool() as pool:
                    # map_async or imap can be used. map returns results in order.
                    # Each chunk returns a list of tuples
                    results = pool.map(_parse_chunk_worker, chunks)
                    
                # Flatten results
                for chunk_result in results:
                    if chunk_result:
                        parsed_data_list.extend(chunk_result)
                        
            except Exception as e:
                log.warning("Multiprocessing failed (%s). Falling back to single process." % str(e))
                parsed_data_list = self._parse_single_process(lines)
        else:
            parsed_data_list = self._parse_single_process(lines)
            
        # Convert parsed data tuples into Element objects
        bar = ProgressBar(len(parsed_data_list), "Instantiating Elements:")
        for data_tuple in parsed_data_list:
            if data_tuple:
                # data_tuple: (name, type, nodes, value, params, original_line)
                ele = Element()
                ele.Name = data_tuple[0]
                ele.Type = data_tuple[1]
                ele.Nodes = data_tuple[2]
                ele.Value = data_tuple[3]
                ele.Params = data_tuple[4]
                ele.Data = data_tuple[5]
                self.elements.add(ele)
            bar.showPercent()
        bar.stop()
        
        log.info("Parsing complete. Total elements: %d" % self.elements.Count)

    def _parse_single_process(self, lines):
        """Fallback single-process parser"""
        parsed_data = []
        bar = ProgressBar(len(lines), "Spice netlist parse models:")
        for line in lines:
            bar.showPercent()
            res = _parse_element_line(line)
            if res:
                parsed_data.append(res)
        bar.stop()
        return parsed_data

    def _parse_chunk_worker(chunk_lines):
        """Worker function for multiprocessing pool"""
        results = []
        for line in chunk_lines:
            res = _parse_element_line(line)
            if res:
                results.append(res)
        return results




    def reduceLC(self):
        count = self.elements.Count
        log.info("Reduce LC Element ... ")
        bar = ProgressBar(count,"Reduce LC Element:")
        elements = Elements()
        for ele in self.elements.values():
            bar.showPercent()
            if ele.Type in ["C","K"]:
                pass
            elif ele.Type in ["L"]:
                ele.Type = "R"
                ele.Name = "R_" + ele.Name
                ele.Params = ["0"]
                ele.Data = " ".join([ele.Name," ".join(ele.Nodes)," ".join(ele.Params)])
                elements.add(ele)
            elif ele.Type in ["R"]:
                elements.add(ele)
            else:
                log.info("Un-handle element type %s"%ele.Type)
                elements.add(ele)
        bar.stop()
        self.elements = elements
        count2 = self.elements.Count
        log.info("reduceLC Total elements:%s, Reduced elements:%s, finnal elements:%s"%(count,count-count2,count2))
        
#         for each in list(self.elements.keys()):
#             ele = self.elements[each]
#             bar.showPercent()
#             if ele.Type in ["C","K"]:
#                 self.elements.remove(ele)
#             elif ele.Type in ["L"]:
#                 ele.Type = "R"
#                 ele.Name = "R_" + ele.Name
#                 ele.Params = ["0"]
#                 ele.Data = " ".join([ele.Name," ".join(ele.Nodes)," ".join(ele.Params)])
#             elif ele.Type in ["R"]:
#                 pass
#             else:
#                 log.info("Un-handle element type %s"%ele.Type)
#                 pass
#         bar.stop()

    def reduceR(self,ResMinValue=Node,ResMaxValue=None):

        if ResMinValue == None:
            ResMinValue = 1e-12
        else:
            ResMinValue = float(ResMinValue)
        if ResMaxValue == None:
            ResMaxValue = 1e12
        else:
            ResMaxValue = float(ResMaxValue)
        count = self.elements.Count
        elements = Elements()
        shortNodes = set()
        #find short and open node
        log.info("Find short and open node ... ")
        for ele in self.elements.values():
            if ele.Type in ["R"]:
                value = float(ele.Params[0])
                if value < ResMinValue:
                    ele.Params[0] = 0
                    log.info("Remove short element: %s"%ele.Data)
                    shortNodes.add(" ".join(ele.Nodes))
                elif value > ResMaxValue:
                    log.info("Remove open element: %s"%ele.Data) #remove
                else:
                    elements.add(ele)
            else:
                elements.add(ele)

        self.elements = elements
        self.generateNodes()

        # short nodes
        flag = True
        while flag:
            flag = False
            log.info("Short nodes iteration ... ")
            for shortNode in shortNodes:
                node1,node2 = shortNode.split()
                if node1 not in self.nodes: 
                    continue
                if node2 not in self.nodes: 
                    continue
                log.info("Handle short node:%s"%shortNode)
                for ele in self.nodes[node2]:
                    for i in range(len(ele.Nodes)):
                        if ele.Nodes[i] == node2:
                            ele.Nodes[i] = node1
                            flag = True
                    ele.Data = " ".join([ele.Name," ".join(ele.Nodes)," ".join(ele.Params)])
                    self.elements.update(ele)
            if flag: 
                # log.info("Short nodes iteration ... ")
                self.generateNodes()


#         bar = ProgressBar(count,"Reduce Rxxx Element:")
        log.info("Reduce Rxxx Element ... ")
        for node,elements in self.nodes.items():
#             bar.showPercent()
            if len(elements) == 1:
                self.elements.remove(elements[0])
            elif len(elements) == 2:
                ele1,ele2 = elements
                ele1.nodes.remove(node)
                ele2.nodes.remove(node)
                ele1.nodes.append(ele2.nodes[0])
                ele1.Params[0] = float(ele1.Params[0]) + float(ele2.Params[0])
                
                ele1.Data = " ".join([ele1.Name," ".join(ele1.Nodes)," ".join(ele1.Params)])
                ele2.Data = " ".join([ele2.Name," ".join(ele2.Nodes)," ".join(ele2.Params)])
                self.elements.update(ele1)
                self.elements.remove(ele2)
            else:
                pass
#         bar.stop()
        count2 = self.elements.Count
        log.info("reduceR Total elements:%s, Reduced elements:%s, finnal elements:%s"%(count,count-count2,count2))

    def reducedRLCK(self,ResMaxValue=None):
        '''
        1. L短路处理
        2. K删除
        3. C删除
        4. 大电阻删除
        '''

        if ResMaxValue == None:
            ResMaxValue = 1e12
        else:
            ResMaxValue = float(ResMaxValue)

        if not self.datas:
            self.parse()

        datas = []
        count = len(self.datas)-2
        bar = ProgressBar(count,"Reduce RLCK Element")
        for line in self.datas:
            bar.showPercent()
            typ = line[0].upper()
            if typ == "R":
                rst = line.split()
                value = float(rst[-1])
                if value > ResMaxValue:
                    # log.info("Remove open element: %s"%line)
                    pass
                else:
                    datas.append(line)
            elif typ in ["K","C"]:
                # log.info("Remove element: %s"%line)
                continue
            elif typ in ["L"]:
                rst = line.split()
                rst[0] = "R_" + rst[0]
                rst[-1] = "0"
                datas.append(" ".join(rst))
            else:
                datas.append(line)
        bar.stop()
        self.datas = datas
        count2 = len(self.datas)-2
        log.info("reduceR Total elements:%s, Reduced elements:%s, finnal elements:%s"%(count,count-count2,count2))

class SpiceModel(object):
    def __init__(self,path):
        self.path = path
        self.subckts = []
        self.headerLines = []
        
        if path:
            self.parse()
        
    def parse(self, path=None):
        """
        解析给定路径下的电路描述文件，并提取所有.subckt行以及其对应的节点信息。
        
        参数:
        - path: str, 文件路径。如果未提供，则使用self.path。
        
        没有返回值，但更新self.subckts属性。
        """

        path = path or self.path
        datas = readData(path)
        lines = datas.splitlines()
        headerLines = []
        flag = 0
        for line in lines:
            if line.strip().lower().startswith(".subckt"):
                flag += 1
                continue
            
            if line.strip().lower().startswith(".ends"):
                flag -= 1
                continue
            
            if flag>0:
                continue
            else:
                headerLines.append(line)
            
        self.headerLines = headerLines

        for block in blockLinesGenerator(lines,flag=[".subckt",".ends"],comment="*" ):
            if block:
                subckt = Subckt(block)
                self.subckts.append(subckt)


    def write(self,path=None):
        path = path or self.path
        log.info("Write Spice Model to %s"%path)
        lines = []
        # lines.append("* This Spice file was generated or modified by an automated script, authored by yongsheng.guo@ansys.com." )
        lines += self.headerLines
        for subckt in self.subckts:
            lines += subckt.datas
        writeData(lines,path)

    def save(self,path=None):
        return self.write(path)