#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230416

'''
支持单位量纲运算

Support unit dimensional operations
value × prefix × unit, 5Ghz, 100Mhz, 1Km

Examples:

    >>> rst = Unit("1mm")
    >>> 100*1e-3
    
    >>> rst = Unit("1mm","km") #km will ignor
    >>> 100*1e-3
    
    >>> rst = Unit("1","mm") #km will ignor
    >>> 100*1e-3

    >>> Unit("1um").V
    1e-6
    
    >>> Unit(1e-6).V
    1e-6
    
    >>> Unit("1um+1um").V
    2e-6
    
    >>> rst = Unit("1um") + "1um"
    >>> rst.V
    2e-6

    >>> rst = Unit("1um")*"1um"
    >>> rst.V
    1e-12
    
    compare Unit objects
    
    >>> Unit("1.5um") > Unit("1um")
    True
    >>> Unit("1.5um") < "1um"
    False
    
    
    support unit convertion
    
    >>> rst = Unit("1um")
    >>> rst["nm"]
    '0.001nm'
'''


import re

class Unit(object):
    
    unitConv = {
        'f':'*1e-15',
        'p':'*1e-12',
        'n':'*1e-9',
        'u':'*1e-6',
        'm':'*1e-3',
        'K':'*1e3',
        'M':'*1e6',
        'G':'*1e9',
        'T':'*1e12',
        'P':'*1e15',
        'Expression':'*1e18',
        'Z':'*1e21',
                }
    
    preUnit = {
        "in": "*0.0254",
        "uin": "*0.0000000254",
        "mil":"*0.0000254",
        "ft": "*.3048",
        "dm":"*0.1",
        "cm":"*0.01",
        "meter":"",
        "hz":"h",
        "kg":"",
        "deg":"",
        "rad":"",
        "ohm":"o"
        }
    
    
    def __init__(self,value = 0,unit=""):
        '''_summary_

        Args:
            value (str): value with unit, value could be expression
            value (int,float): will convert to str using str()
        '''
        
        self.unit = unit
        
        if isinstance(value,Unit):
            self._value = value.Expression
        else:
            self._value = str(value)+unit
        
        
    @property
    def Expression(self):
        return self.converToExpression(self._value)

    @property
    def Value(self):
        return self.V
        
    @property
    def U(self):
        '''
        return unit: mm, um
        '''
        if not self.unit:
            rst = re.findall(r"\d+([a-zA-Z]+)",self._value)
            if rst:
                self.unit = rst[0]
            else:
                self.unit = ""
        
        return self.unit

    @property
    def V(self):
        s = self.Expression
        if s[0] == "*":  #for Unit("Ghz")
            s = "1"+s
        #log.debug(type(s))
        try:
            return float(s)
        except:
            return eval(s)
    @property
    def S(self):
        return str(self.Expression)     
    
    def  __getitem__(self, key,decimal=None):
        return self.convertoNewUnit(key,decimal)
    
    def __call__(self,unit):
        return self.convertoNewUnit(unit)
    
    def __str__(self):
        return self._value

    def __repr__(self):
        return self._value
    
    def __float__(self):
        return self.V

    def __add__(self,u):
        if isinstance(u, Unit):
            return Unit(self.V+u.V)
        if isinstance(u, str):
            return self + Unit(u)
        return self + str(u)
        
    def __sub__(self,u):
        
        if isinstance(u, Unit):
            return Unit(self.V-u.V)
        if isinstance(u, str):
            return self - Unit(u)
        return self - str(u)
 
    def __mul__(self,u):
        
        if isinstance(u, Unit):
            return Unit(self.V*u.V)
        if isinstance(u, str):
            return self * Unit(u)
        return self * str(u)
    
    def __truediv__(self,u):
        if isinstance(u, Unit):
            return Unit(self.V/u.V)
        if isinstance(u, str):
            return self/Unit(u)
        return self/str(u)

    def __div__(self,u):
        if isinstance(u, Unit):
            return Unit(self.V/u.V)
        if isinstance(u, str):
            return self/Unit(u)
        return self/str(u)
           
    def __radd__(self,u):
        return self + u
        
    def __rsub__(self,u):
        return Unit(u) - self
 
    def __rmul__(self,u):
        return self * u
          
    def __rdiv__(self,u):
        return (self.__class__(0)+u)/self

    def __rtruediv__(self,u):
        return (self.__class__(0)+u)/self

    def __pow__(self,u):
        if isinstance(u, Unit):
            return Unit(self.V**u.V)
        if isinstance(u, str):
            return self**Unit(u)
        return self**str(u)


    def __eq__(self,u):
        if isinstance(u, Unit):
            v1 = self.V
            v2 = u.V
            delta = min(abs(v1),abs(v2))*1e-3
            if abs(v1-v2)<delta:
                return True
            else:
                return False
        if isinstance(u, str):
            return self==Unit(u)
        return self==str(u)        
        
    def __gt__(self,u):
        if isinstance(u, Unit):
            v1 = self.V
            v2 = u.V
            delta = min(abs(v1),abs(v2))*1e-3
            if v1-v2>delta:
                return True
            else:
                return False
        if isinstance(u, str):
            return self>Unit(u)
        return self>str(u)       

    def __lt__(self,u):
        if isinstance(u, Unit):
            v1 = self.V
            v2 = u.V
            delta = min(abs(v1),abs(v2))*1e-3
            if v2-v1>delta:
                return True
            else:
                return False
        if isinstance(u, str):
            return self<Unit(u)
        return self<str(u)

    def __ge__(self,u):
        """重载 >= 运算符"""
        if isinstance(u, Unit):
            v1 = self.V
            v2 = u.V
            delta = min(abs(v1),abs(v2))*1e-3
            if v1>=v2:
                return True
            else:
                return False
        if isinstance(u, str):
            return self>=Unit(u)
        return self>=str(u)       

    def __le__(self,u):
        """重载 <= 运算符"""
        if isinstance(u, Unit):
            v1 = self.V
            v2 = u.V
            delta = min(abs(v1),abs(v2))*1e-3
            if v1<=v2:
                return True
            else:
                return False
        if isinstance(u, str):
            return self<=Unit(u)
        return self<=str(u)


    def __abs__(self):
        return abs(self.V)
    
    def converToExpression(self,s):
        #"60Gps+5m-2pf" ->600e-9+ 5e-3-2e-12
        if not isinstance(self._value, str):
            return s
        #pre replace
        for x in self.preUnit:
            s = re.sub(x,self.preUnit[x],s,re.IGNORECASE)
#             s = s.replace(x,self.preUnit[x])
        s = re.sub(r"([\*\+\-0-9]+)[a-df-zA-DF-Z]{1}(([\*\+\-0-9]+)|$)",r"\1\2",s) #replace single letter,except e
        s = re.sub(r"([a-zA-Z]{1})[a-zA-Z]+",r"\1unit",s) #keep only one letter
        for k in self.unitConv:
            #add unit to void e or Expression as a scale
            s = s.replace(k+"unit",self.unitConv[k])
        return s
    
    def convertoNewUnit(self,u="",decimal = None):
        '''
        return string value of given unit
        '''
        if not isinstance(self._value, str):
            raise ValueError("New unit must a string format")
        
        if u == "":
            return str(self.V)
        
        if len(u.strip())<2:
            raise ValueError("New unit must not less then two letter ")
        if decimal:
            fmt = "%%.%df%%s"%decimal
            return fmt%(self/Unit(u),u)
        else:
            return "%s%s"%(self/Unit(u),u)
    #short name for convertoNewUnit
#     U = convertoNewUnit

if __name__ == '__main__':
    u = Unit("60Gps+5m-2pf") 
    print(u)
    pass