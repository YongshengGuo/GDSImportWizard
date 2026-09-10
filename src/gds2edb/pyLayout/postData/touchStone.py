#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20260706


import os,sys,re,ast

isIronpython = "IronPython" in sys.version

np = None
plt = None
rf = None
 

def _load_touchstone_libs():
    global np, plt, rf

    if isIronpython:
        raise RuntimeError("IronPython is not supported for Touchstone. Please use CPython.")

    if np is None:
        import numpy as _np
        np = _np

    if plt is None:
        import matplotlib.pyplot as _plt
        # 设置全局中文字体（跨平台兼容）
        if sys.platform == 'win32':
            _plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        else:  # Linux, macOS
            _plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'DejaVu Sans', 'Arial']
        _plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        plt = _plt

    if rf is None:
        import skrf as _rf
        rf = _rf

if isIronpython:
    print("IronPython is not supported for Touchstone. Please use CPython.")


class Touchstone(object):
    '''
    用于快速读取SNP文件，获取S参数数据，
    合法输入格式：dB(S11), dB_S11,dB_S(11,22)->db,s,None,11,22 或者 dB(SDD11), dB_SDD11, dB_SDD(11,22)->db,s,dd,11,22    
    注意：所有的Port下标从1开始。
    '''
    
    def __init__(self, path = None,network = None):
        '''
        Constructor
        '''
        _load_touchstone_libs()
        self.path = path
        self._network = network
        self._diffNetwork = None
        self.diffZ0 = 100
        self.ax = None
        
    def __getitem__(self, key):
        return self.get(key)
        
    
    @property
    def Freq(self):
        return self.Network.f
    
    @property
    def freqCount(self):
        #frequency points
        return self.Network.frequency.shape[0]

    @property
    def portCount(self):
        try:
            return self.Network.s.shape[1]
        except (AttributeError):
            return 0
    
    @property
    def name(self):
        return self.Network.name

    @property
    def portNames(self):
        if isinstance(self.Network.port_names,np.ndarray) or self.Network.port_names != None:
            return self.Network.port_names
        
        return [str(i+1) for i in range(self.portCount)]
    
    @property
    def Network(self):
        if self._network is None:
            print("Read SNP file: %s"%self.path)
            self._network = rf.network.Network(self.path)
        return self._network

    @property
    def DiffNetwork(self):
        """
        return differetial S entry
        DD: 1->4, 2->5,3->6, CC: 7->10,8->11,9-12
        
          +------+               +------+
        1-|P1==P3|-3           1-|d1==d2|-2
          |      |   =se2gmm=>   |      |
        2-|P2==P4|-4           3-|c1==c2|-4
          +------+               +------+
        
        """
        if self._diffNetwork is None:
            self._diffNetwork = self.getDiffNetwork()
            # p = int(self.Network.number_of_ports/2)
            # snp = self.Network.copy()
            # z0_mm = snp.z0.copy()
            # z0_mm[:, 0:p] = self.diffZ0  # differential mode impedance
            # z0_mm[:, p:2 * p] = 0.25*self.diffZ0  # common mode impedance
            # snp.se2gmm(p,z0_mm)
            # self._diffNetwork = snp
        return self._diffNetwork

    def getDiffNetwork(self,diffZ0=None):
        
        """
        return differetial S entry
        DD: 1->4, 2->5,3->6, CC: 7->10,8->11,9-12
        
          +------+               +------+
        1-|P1==P3|-3           1-|d1==d2|-2
          |      |   =se2gmm=>   |      |
        2-|P2==P4|-4           3-|c1==c2|-4
          +------+               +------+
        
        """
        
        diffZ0 = diffZ0 or self.diffZ0 
        p = int(self.Network.number_of_ports/2)
        snp = self.Network.copy()
        z0_mm = snp.z0.copy()
        z0_mm[:, 0:p] = diffZ0  # differential mode impedance
        z0_mm[:, p:2 * p] = 0.25*diffZ0 # common mode impedance
        snp.se2gmm(p,z0_mm)
        
        def intersectionStr(str1,str2):
            i1 = len(str1)
            i2 = len(str2)
            ind = max(i1,i2)
            temp = ""
            for i in range(ind):
                if i>=i1:
                    temp += str2[i]
                    continue
                if i>=i2:
                    temp += str1[i]
                    continue
                if str1[i]==str2[i]:
                    temp += str1[i]
                    
            #去除temp末尾的_
            temp = temp.rstrip("_")
                    
            return  temp
        
        portNames = [intersectionStr(self.portNames[i*2],self.portNames[i*2+1]) for i in range(p)] #use self portnames 20260823
        snp.Network.port_names = portNames + portNames
        
        return snp

    def _quantity_parser(self,quantity):
        '''
        quantity: 由两部分组成 1) dB, mag, rad,cangRad, re, im,real, imag, deg, cangDeg 2) s11, s12, s21, s22 3) 差分信号标志dd,cc,dc,cd
        数字默认被分成两部分，比如dB_S1122 -> dB_S(11,22)
        合法输入格式：dB(S11), dB_S11,dB_S(11,22)->db,s,None,11,22 或者 dB(SDD11), dB_SDD11, dB_SDD(11,22)->db,s,dd,11,22
        
        解析方法：
        1. 替换掉_()为空值
        2. 匹配数值和"," 如果有","则分成两部分，没有","则把数字平均分割成2部分为端口号
        3. 匹配S和后面的dd,cc,dc,cd标志
        4. 匹配前面的dB,mag,rad,cangRad,re,im,deg,cangDeg标志， real, imag 统一返回 im,real
        5. 匹配dd,cc,dc,cd或者数字前面的一个字母S，可能值有S,Y,Z,A,H，T，g
        
        返回数值 db,s,None,11,22  db,s,dd,11,22
        '''
        # Step 1: 去掉 _, (, ), 空格
        q = re.sub(r'[_()\s]', '', quantity)
        
        # Step 4 format 关键字（长的放前面防止短的先匹配）
        fmt_pattern = r'(cangRad|cangDeg|imag|real|dB|mag|rad|deg|im|re)'
        # Step 5 参数类型字母：S, Y, Z
        param_pattern = r'([SYZ])'
        # Step 3 差分标志
        diff_pattern = r'(dd|cc|dc|cd)?'
        # Step 2 端口号：支持 "1,2" 或 "11" 或 "1122"
        port_pattern = r'(\d+(?:,\d+)?)'
        
        full_pattern = fmt_pattern + param_pattern + diff_pattern + port_pattern
        match = re.fullmatch(full_pattern, q, re.IGNORECASE)
        
        if not match:
            raise ValueError("无法解析 quantity 字符串: %s" % quantity,
                             "正确的格式示例: dBS11, dB(S11), dB_S11, dB_S(11,22), dB(SDD11), dB_SDD11, dB_SDD(11,22)"
                             )
        
        fmt_raw = match.group(1)
        param_type = match.group(2).lower()
        diff_mode = match.group(3).lower() if match.group(3) else None
        port_str = match.group(4)
        
        # 归一化 format 名称（保留大小写规范）
        fmt_norm_map = {
            'cangrad': 'rad_unwrap', 'cangdeg': 'deg_unwrap',
            'db': 'db', 'mag': 'mag', 'rad': 'rad', 'deg': 'deg',
            'real': 're', 'imag': 'im', 're': 're', 'im': 'im',
        }
        fmt = fmt_norm_map.get(fmt_raw.lower(), fmt_raw.lower())
        
        # Step 2: 解析端口号
        if ',' in port_str:
            parts = port_str.split(',')
            port1, port2 = parts[0], parts[1]
        else:
            half = len(port_str) // 2
            port1, port2 = port_str[:half], port_str[half:]
        
        return fmt, param_type, diff_mode, port1, port2


    def _get_single_quantity(self, quantity):
        fmt, param_type, diff_mode, port1, port2 = self._quantity_parser(quantity)
        # 获取对应的S参数数据
        if diff_mode:
            portCount = self.Network.number_of_ports
            if portCount % 4 == 0:
                n = int(portCount / 4)
            else:
                raise ValueError('the Network must have 4n port')

            entryOffsetdict = {"DD":[0,0],"DC":[0,2*n],"CD":[2*n,0],"CC":[2*n,2*n]}
            if diff_mode.upper() not in entryOffsetdict:
                raise ValueError('diff_mode must be one of DD,DC,CD,CC')
            offset = entryOffsetdict[diff_mode.upper()]
            port1 = int(port1) + offset[0]
            port2 = int(port2) + offset[1]
            prop = getattr(self.DiffNetwork, "%s_%s" % (param_type, fmt))
            return prop[:,int(port1)-1, int(port2)-1]

        prop = getattr(self.Network, "%s_%s" % (param_type, fmt))
        return prop[:,int(port1)-1, int(port2)-1]

    def _get_single_Lable(self, quantity):
        fmt, param_type, diff_mode, port1, port2 = self._quantity_parser(quantity)
        # 获取对应的S参数数据
        if diff_mode:
            portCount = self.Network.number_of_ports
            if portCount % 4 == 0:
                n = int(portCount / 4)
            else:
                raise ValueError('the Network must have 4n port')

            entryOffsetdict = {"DD":[0,0],"DC":[0,2*n],"CD":[2*n,0],"CC":[2*n,2*n]}
            if diff_mode.upper() not in entryOffsetdict:
                raise ValueError('diff_mode must be one of DD,DC,CD,CC')
            offset = entryOffsetdict[diff_mode.upper()]
            port1 = int(port1) + offset[0]
            port2 = int(port2) + offset[1]
            return "{fmt}{param_type}{diff_mode}({port1},{port2})".format(fmt=fmt,param_type=param_type,
                     diff_mode=diff_mode,port1=self.getPortNameByIndex(port1),port2=self.getPortNameByIndex(port2))

        return "{fmt}{param_type}({port1},{port2})".format(fmt=fmt,param_type=param_type,
                    port1=self.getPortNameByIndex(port1),port2=self.getPortNameByIndex(port2))


    def _eval_quantity_expression(self, expr):
        # 提取 quantity 片段并映射成占位符，随后用 AST 安全计算
        token_re = re.compile(
            r'(?i)(?:'
            r'(?:cangRad|cangDeg|imag|real|dB|mag|rad|deg|im|re)\s*\(\s*[SYZ]\s*(?:dd|cc|dc|cd)?\s*\d+\s*(?:,\s*\d+\s*)?\)|'
            r'(?:cangRad|cangDeg|imag|real|dB|mag|rad|deg|im|re)\s*_?\s*[SYZ]\s*(?:dd|cc|dc|cd)?\s*\d+'
            r')'
        )
        token_map = {}

        def _replace_token(match):
            token = match.group(0)
            name = "__q%d" % len(token_map)
            token_map[name] = token
            return name

        safe_expr = token_re.sub(_replace_token, expr.replace('^', '**'))
        if not token_map:
            raise ValueError("表达式中未找到合法 quantity: %s" % expr)

        try:
            node = ast.parse(safe_expr, mode='eval')
        except SyntaxError:
            raise ValueError("表达式语法错误: %s" % expr)

        def _eval(node_obj):
            if isinstance(node_obj, ast.Expression):
                return _eval(node_obj.body)
            if isinstance(node_obj, ast.Name):
                if node_obj.id not in token_map:
                    raise ValueError("表达式包含未授权标识符: %s" % node_obj.id)
                # 递归调用 get，满足“每个操作数递归获取数据”的要求
                return self.get(token_map[node_obj.id])
            if isinstance(node_obj, ast.Constant):
                if isinstance(node_obj.value, (int, float)):
                    return node_obj.value
                raise ValueError("仅支持数字常量")
            if isinstance(node_obj, ast.UnaryOp):
                val = _eval(node_obj.operand)
                if isinstance(node_obj.op, ast.UAdd):
                    return val
                if isinstance(node_obj.op, ast.USub):
                    return np.negative(val)
                raise ValueError("不支持的一元运算")
            if isinstance(node_obj, ast.BinOp):
                left = _eval(node_obj.left)
                right = _eval(node_obj.right)
                if isinstance(node_obj.op, ast.Add):
                    return np.add(left, right)
                if isinstance(node_obj.op, ast.Sub):
                    return np.subtract(left, right)
                if isinstance(node_obj.op, ast.Mult):
                    return np.multiply(left, right)
                if isinstance(node_obj.op, ast.Div):
                    return np.divide(left, right)
                if isinstance(node_obj.op, ast.Pow):
                    return np.power(left, right)
                raise ValueError("不支持的运算符")
            raise ValueError("不支持的表达式元素: %s" % type(node_obj).__name__)

        return _eval(node)

    def getPortNameByIndex(self,ind):
        """
        ind start from 1
        """
        return self.portNames[int(ind)-1]

    def getLable(self,quantity):
        '''
        有运算表达式直接返回表达式，其他情况返回Port实际名称
        '''
        q = quantity.strip()
        # 含运算符则按表达式处理；否则按单一 quantity 处理
        if re.search(r'[+\-*/^()]', q):
            return quantity
        else:
            

            return self._get_single_quantity(q)
        
        

    def get(self,quantity):
        '''
        Network合法的组合格式{PrimaryPropertiesT}_{ComponentFuncT}
        PrimaryPropertiesT = Literal['s', 'z', 'y', 'a', 'g', 'h', 't']
        ComponentFuncT = Literal["re", "im", "mag", "db", "db10", "rad", "deg", "arcl", "rad_unwrap", "deg_unwrap",
                                "arcl_unwrap", "vswr", "time", "time_db", "time_mag", "time_impulse", "time_step"]
                                
        合法输入格式：dB(S11), dB_S11,dB_S(11,22)->db,s,None,11,22 或者 dB(SDD11), dB_SDD11, dB_SDD(11,22)->db,s,dd,11,22    
        注意：所有的Port下标从1开始。      
        
        增加对表达式的支持，允许用户输入类似 "dB(S11) + dB(S22)" 或 "dB(S11) - dB(S21)" 的表达式，返回计算结果。
        支持运算的类型：加法 (+), 减法 (-), 乘法 (*), 除法 (/)，比如：
        - "dB(S11) + dB(S22)"
        - "dB(S11) - dB(S21)"
        - "dB(S11) * dB(S22)"
        - "dB(S11) / dB(S21)"
        - "dB(S11) + 3" (支持与常数的运算)
        - "dB(S11) - 2.5"
        - "dB(S11) * 2"
        - "dB(S11) / 0.5"
        - "dB(S11) ** 2" 或  "dB(S11) ^ 2" (支持幂运算)
        - "dB(S11) + dB(S22) - dB(S21)" (支持多项式运算)        
        '''
        q = quantity.strip()
        # 含运算符则按表达式处理；否则按单一 quantity 处理
        if re.search(r'[+\-*/^()]', q):
            try:
                return self._eval_quantity_expression(q)
            except ValueError:
                # 非法表达式则回退到单一 quantity 解析，给出更明确错误信息
                pass
        return self._get_single_quantity(q)
        
    def plot(self, quantitys, ylabel = None, title=None,labels=None, ax = None, **kwargs):
        '''
        绘制S参数曲线
        quantity: 由两部分组成 1) dB, mag, rad,cangRad, re, im,real, imag, deg, cangDeg 2) s11, s12, s21, s22 3) 差分信号标志dd,cc,dc,cd
        数字默认被分成两部分，比如dB_S1122 -> dB_S(11,22)
        合法输入格式：dB(S11), dB_S11,dB_S(11,22)->db,s,None,11,22 或者 dB(SDD11), dB_SDD11, dB_SDD(11,22)->db,s,dd,11,22    
        
        labels: 可选参数，指定每条曲线的标签列表。如果未提供，则使用默认标签。
        
        注意：所有的Port下标从1开始。

        
        '''
        quantityList = re.split(r'[,;]+', quantitys)
        data = [self.get(quantity) for quantity in quantityList]
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            
        for idx, (quantity, d) in enumerate(zip(quantityList, data)):
            
            #获取label
            if labels is None:
                label = self._get_single_Lable(quantity)
            else:
                if isinstance(labels, str):
                    labels = re.split(r'[,;]+', labels)
                    
                if labels and len(labels) != len(quantityList):
                    print("waring: labels 的数量和 quantityList不相同，忽略 labels 参数")
                    labels = quantityList
                label = labels[idx]

            ax.plot(self.Network.f/1e9, d, label=label, **kwargs) #Ghz
            
        ax.set_xlabel("Frequency [GHz]")
        if ylabel:
            ax.set_ylabel(ylabel)
        else:
            ax.set_ylabel(", ".join(quantityList))
            
        if title:
            ax.set_title(title)
        ax.grid()
        ax.legend()
        self.ax = ax
        return ax
    
    def copy(self):
        """
        Create a deep copy of the Touchstone instance.
        """
        copy_network = self.Network.copy()
        ts = Touchstone(network=copy_network)
        ts.path = self.path
        return ts
    
    def cmpPlot(self,others,quantitys, ylabel = None, title=None, ax = None,  **kwargs):
        '''
        绘制S参数曲线对比,others: list of Touchstone, 如不过不是list则[others], 绘制在同一张图上
        quantity: 同plot和get函数
        '''
        quantityList = [q for q in re.split(r'[,;\s]+', quantitys) if q]
        if len(quantityList) == 0:
            raise ValueError("quantitys 不能为空")

        if not isinstance(others, list):
            others = [others]

        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)

        # 第一条曲线来源 self，后续来自 others
        datasets = [self] + [obj for obj in others if obj is not None]
        for idx, tsData in enumerate(datasets):
            if not hasattr(tsData, "get") or not hasattr(tsData, "Network"):
                raise TypeError("others 中对象必须是 Touchstone 或兼容对象")

            if tsData.path:
                data_name = os.path.basename(tsData.path)
            else:
                data_name = "self" if idx == 0 else "other%d" % idx

            freq_ghz = tsData.Network.f / 1e9
            for quantity in quantityList:
                d = tsData.get(quantity)
                ax.plot(freq_ghz, d, label="%s:%s" % (data_name, quantity), **kwargs)

        ax.set_xlabel("Frequency [GHz]")
        if ylabel:
            ax.set_ylabel(ylabel)
        else:
            ax.set_ylabel(", ".join(quantityList))

        if title:
            ax.set_title(title)
        else:
            ax.set_title("Touchstone Compare Plot")

        ax.grid()
        ax.legend()
        self.ax = ax
        return ax
        
    
    def savePlotPic(self,savePicPath=None,ax=None):
        ax = ax if ax is not None else self.ax

        if savePicPath is None:
            savePicPath = os.path.splitext(self.path)[0] + "_plot.png"
        else:
            if not os.path.isabs(savePicPath):
                savePicPath = os.path.join(os.path.dirname(self.path), savePicPath)
            else:
                savePicPath = os.path.abspath(savePicPath)
        
        ax.figure.savefig(savePicPath, dpi=300)
        print("Plot saved to: %s" % savePicPath)
    
    
    def _parse_frequency(self, freq_str):
        """
        Parse frequency string with unit support.
        freq_str: "0Hz", "1KHz", "10MHz", "100GHz", "1THz"
        Returns: frequency in Hz
        """
        unit_map = {
            'hz': 1,
            'khz': 1e3,
            'mhz': 1e6,
            'ghz': 1e9,
            'thz': 1e12,
        }
        
        match = re.match(r'([\d.]+)\s*([a-zA-Z]+)', freq_str.strip())
        if not match:
            raise ValueError("无法解析频率字符串: %s" % freq_str)
        
        value = float(match.group(1))
        unit = match.group(2).lower()
        
        if unit not in unit_map:
            raise ValueError("未支持的频率单位: %s (支持: Hz, KHz, MHz, GHz, THz)" % unit)
        
        return value * unit_map[unit]
    
    def resampleSweepData(self,sweepData):
        """
        Resample the network to new frequencies using interpolation.
        sweepData examples: 
            "LIN 0Hz 20GHz 0.01GHz"
            "LIN 0MHz 10MHz 100KHz"
            "DEC 1GHz 10GHz 10"
            "LINC 0Hz 10GHz 100"
            "DEC 1GHz 10GHz 10 LIN 1GHz 10GHz 0.1GHz"
        """
        # Parse the sweepData string to extract frequency points
        freq_points = []
        sweep_parts = re.split(r'\s+', sweepData.strip())
        i = 0
        while i < len(sweep_parts):
            if sweep_parts[i].upper() in ['LIN', 'DEC', 'LINC']:
                mode = sweep_parts[i].upper()
                start_freq = self._parse_frequency(sweep_parts[i + 1])
                end_freq = self._parse_frequency(sweep_parts[i + 2])
                if mode == 'LIN':
                    step_freq = self._parse_frequency(sweep_parts[i + 3])
                    freq_points.extend(np.arange(start_freq, end_freq + step_freq, step_freq))
                    i += 4
                elif mode == 'DEC':
                    num_points = int(sweep_parts[i + 3])
                    freq_points.extend(np.logspace(np.log10(start_freq), np.log10(end_freq), num=num_points))
                    i += 4
                elif mode == 'LINC':
                    num_points = int(sweep_parts[i + 3])
                    freq_points.extend(np.linspace(start_freq, end_freq, num=num_points))
                    i += 4
            else:
                i += 1

        freq_points = np.unique(freq_points)  # Remove duplicates and sort

        # Interpolate the network to the new frequency points
        new_network = self.Network.interpolate(freq_points)
        ts = Touchstone(network=new_network)
        ts.path = self.path
        return ts

    def cascadeNTimes(self,N):
        """
        Cascade the network N times.
        """
        N = int(N)
        
        if N < 1:
            raise ValueError("N must be a positive integer.")
        
        cascaded_network = self.Network.copy()
        for _ in range(N - 1):
            cascaded_network = cascaded_network ** self.Network
        
        ts = Touchstone(network=cascaded_network)
        ts.path = self.path
        return ts


    def save(self, path=None):
        if path is None:
            path = self.path
        self.Network.write_touchstone(path)


if __name__ == "__main__":
    path = r"C:\work\Project\AE\optislang\Material_fitting\90ohm_measurement.s4p"
    tsData = Touchstone(path)
    ax = tsData.plot("dbS31;dbS32;dbS33;dbS34", ylabel="Magnitude [dB]", title="S-Parameters")
    tsData.get("dbs21*2")
    tsData.Network.s_mag[1,2]
    print(tsData.Network)