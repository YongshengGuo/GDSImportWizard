#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20230410

import re
import math


from ..common import hfss3DLParameters
from ..common.arrayStruct import ArrayStruct
from ..common.complexDict import ComplexDict
from ..common.unit import Unit
from ..common.common import log,tuple2list
from .definition import Definitions,Definition



class Material(Definition):
    '''
    oMaterialManager.GetData()
    ['NAME:copper', 'CoordinateSystemType:=', 'Cartesian', 'BulkOrSurfaceType:=', 1, 
    ['NAME:PhysicsTypes', 'set:=', ['Electromagnetic', 'Thermal',"Structural"]], 
    'permittivity:=', '0.999991', 
    "permeability:="    , "1",
    "conductivity:="    , "0",
    "dielectric_loss_tangent:=", "0",
    "magnetic_loss_tangent:=", "0"
    'thermal_conductivity:=', '0', 
    'mass_density:=', '0', 
    'specific_heat:=', '0']
    '''
    



    def __init__(self, name = None,array = None,layout = None):
        super(self.__class__,self).__init__(name,type="Material",layout=layout)
        self.maps = {
            "DK":"permittivity",
            "DF":"dielectric_loss_tangent",
            "Cond":"conductivity",
            "Resistivity":{"Key":"conductivity","Get": lambda x:1/float(x),"Set": lambda x:str(1.0/x)},
            "k":"thermal_conductivity",
            "ur": "permeability"
            }


    def parse(self,force = False):
        '''
        mapping key must not have same value with maped key.
        '''
        
        if self.parsed and not force:
            return
        
        log.debug("parse definition: %s"%self.name)
        maps = self.maps
        
        datas = self.oManager.GetData(self.name)
        if datas:
            _array =  ArrayStruct(tuple2list(hfss3DLParameters.material),maps=maps)
            _array.update(ArrayStruct(datas))
        else:
            _array = ArrayStruct([])
        
#         self._info.update("self", self)
        self._info.update("Name",self.name)
        self._info.update("Array", _array)

        maps.update({"IsMetal":{
            "Key":"self",
            "Get":lambda s: s.isConductor()
            }})
        
        maps.update({"IsDielectric":{
            "Key":"self",
            "Get":lambda s: not s.isConductor()
            }})
        
        self._info.update("self", self)    
        self._info.setMaps(maps)
        self.maps = maps
        self.parsed = True

#     def parse(self):
#         self._array = ArrayStruct(tuple2list(hfss3DLParameters.material),maps=self.maps)
#         oMaterialManager = self.oDefinitionManager.GetManager("Material")
#         datas = oMaterialManager.GetData(self.name)
#         if not datas:
#             log.exception("Material not exist: %s"%self.name)
# 
#         self._array.update(ArrayStruct(datas))

    def update(self):
        '''
        update the material parameters to project
        All the material changeing will not update to project untill update
        
        if material not exist, will add, else will edit
        '''
        #oDefinitionManager.AddMaterial(["NAME:Material1",["NAME:PhysicsArrayTypes","set:=", ["Electromagnetic","Thermal","Structural"]]])
        
        if self.oDefinitionManager.DoesMaterialExist(self.name):
            self.oDefinitionManager.EditMaterial(self.name,self.Array.Datas)
        else:
            self.oDefinitionManager.AddMaterial(self.Array.Datas)
            
    def delete(self):
        oDefinitionManager = self.oProject.GetDefinitionManager()
        oDefinitionManager.RemoveMaterial(self.name, True, "", "Project")
        self.layout.Materials.refresh()


    def isConductor(self,threshed=10000):
        
        #---判断材料是否为导体，默认阈值为10000S/m
        try:
            if float(self.conductivity) < 10000:
                return False
            else:
                return True
        except:
            #conductivity is expression
            log.debug("float(conductivity) error:%s"%self.conductivity)
        
        #---判断材料是否为导体，默认阈值为10000S/m
        #---DS-Model or expression, 20260626
        #1e-12+2.84472e-12*Freq*(atan(Freq/70403)-atan(Freq/1.59155e+11))
        try:
            evalValue = self.layout.Variables.evalExpression(self.conductivity)
#             evalValue = self.layout.Variables.EvalExpressionValue.SIValue
            if float(evalValue) < 10000:
                return False
            else:
                return True
        except:
            #conductivity is expression
            log.debug("Eval conductivity value error:%s"%self.conductivity)

        log.warning("Can't justment the material %s is counductor or not, just return False."%self.name)
        return False

    
class Materials(Definitions):

    def __init__(self,layout=None):
        super(self.__class__,self).__init__(layout, type="Material",definitionCalss=Material)
            
    def __getitem__(self, key):
        try:
            return super(self.__class__,self).__getitem__(key)
        except: 
            return self.getByName(key)
            
    def __contains__(self,key):
        #key is case-insensitive
        if super(self.__class__,self).__contains__(key):
            return True
        
        return bool(self.getByName(key))

            
    def create(self,infoDict={},name=None,**kwargs):
        '''
        infoDict(dict): {name:copper,....}
        
        Only create the Material object, not add to layout
        '''
        ops = ComplexDict(infoDict)
        ops.updates(kwargs)
        ary = ArrayStruct(tuple2list(hfss3DLParameters.material),maps=Material().maps).copy()
        
        if name:
#             name = name
            ary.Array[0] = 'NAME:%s'%name
#             if "Name" in ops:
#                 del ops["Name"]
        else:
            name = ops["Name"]
            ary.Array[0] = 'NAME:%s'%name
        
        for item in ["Name","Freq"]:
            if item in ops:
                del ops[item]
            
        for k in ops.Keys:
            if k in ary:
                ary[k] = str(ops[k])
            else:
                log.info("Material key '%s' ignor."%k)
                
        material = Material(name,layout=self.layout)
        material.Array = ary
#         material._info = ary
        return material
            
            
    def add(self,name=None,infoDict={},**kwargs):
        '''
        info(dict): {name:copper,...., Freq:xxxx}
        if material not exist, will add, else will edit
        '''

        #兼容设计
        if isinstance(name,(dict,ComplexDict)) and not infoDict:
            infoDict = ComplexDict(name)
            name = infoDict["Name"]
        
        ops = ComplexDict(infoDict)
        ops.updates(kwargs)
        if "Freq" in ops and ops.Freq:
            #Frequency-independent material
            dks = re.split(r"\s*[;,]+\s*",ops.DK)
            freqs = re.split(r"\s*[;,]+\s*",ops.Freq)
            dk = dks[0]
            df = ops.DF
            if len(freqs) == 1:
                f1 = freqs[0]
                f2 = 10**12/(2*math.pi)
            elif len(freqs) == 2:
                f1 = freqs[0]
                f2 = freqs[1]
            else:
                log.exception("Material %s Frequencies set error:%s."%(name,ops.Freq))

            #---DS-Model
            if len(dks) == 1:
                #hfss DS-Model
                if "_ds" not in ops.Name[-3:].lower():
                    name = ops.Name + "_DS_%s"%("_".join(freqs))
                else:
                    name = ops.Name
                return self.addHFSSDSModle(name,dk,df,f1=f1,fB=f2)
            elif len(dks) == 2:
                #stander DS-Model
                if "_ds" not in ops.Name[-3:].lower():
                    name = "%s_DS_%s"%("_".join(dks),"_".join(freqs))
                else:
                    name = ops.Name
                return self.addStdDSModel(name,dks[0],dks[1],fA=f1,fB=f2)
            else:
                log.exception("Material %s DK set error:%s."%(name,ops.DK))
        else:
            material = self.create(infoDict,name,**kwargs)
            material.update()
            self.push(material.name)
            return material
    
    def removeUnusedMaterials(self):
        '''
        Remove the unused materials in project
        '''
        self.layout.oProject.RemoveUnusedDefinitions(
            [
                [
                    "NAME:Materials", 
                ] + self.NameList
            ])

    
    def addHFSSDSModle(self,name,dk=4,df=0.02,f1=1e9,cond_dc=1e-12,fB=10**12/(2*math.pi)):
        '''
        Djordjevic-Sarkar Model Parameter Calculation in hfss
        WA<<W1=> f1>>fB
        fB default 10^12/(2*pi) = 159.155
        '''
        # K = f"({dk} * {df} - {cond_dc} / (2 * pi * {freqA} * e0)) / atan({freqB} / {freqA})"
        dk = Unit(dk).V
        df = Unit(df).V
        f1 = Unit(f1).V
        fB = Unit(fB).V
        cond_dc = Unit(cond_dc).V
        w1 = 2*math.pi*f1
        wB = 2*math.pi*fB
        
        e0 = 8.854187817e-12  
        
        K = (dk*df-cond_dc/(w1*e0))/math.atan(wB/w1)
        e_infi = dk-0.5*K*math.log(wB**2/w1**2+1)
        e_delta = 10*df*e_infi
        fA = fB/math.exp(e_delta/K)
        
        log.info("Djordjevic-Sarkar Model Parameter:\n",
                 "e_infi:%s "%e_infi,
                 "e_delta:%s "%e_delta,
                 "fA:%s "%fA,
                 "fB:%s "%fB
                 )
        
        # e_freq = "{e_infi}+{K}/2*ln(({fB}**2+Freq*Freq)/({fA}**2+Freq*Freq))".format(e_infi=e_infi,K=K,fB=fB,fA=fA)
        # cond_freq = "{cond_dc}+2*pi*Freq*e0*{K}*(atan(Freq/{fA})-atan(Freq/{fB}))".format(cond_dc=cond_dc,K=K,fB=fB,fA=fA)
        
        # log.info("Djordjevic-Sarkar Model Parameter:\n",
        #          "DK:%s\n"%e_freq,
        #          "Conductivity:%s"%cond_freq
        #          )
        
        #兼容Siwave 20260521 （测试不成功）
        epsilon_0 = 8.8541878128e-12
        e_freq = "{e_infi:.5f}+{Kd2:.8f}*ln(({fBp2:.5e}+Freq*Freq)/({fAp2:.5e}+Freq*Freq))".format(e_infi=e_infi,Kd2=K/2,fBp2=fB**2,fAp2=fA**2)
        cond_freq = "{cond_dc}+{Kx:.5e}*Freq*(atan(Freq/{fA:.1f})-atan(Freq/{fB:.5e}))".format(cond_dc=cond_dc,Kx=K*2*math.pi*epsilon_0,fB=fB,fA=fA)
        
        log.info("Djordjevic-Sarkar Model Parameter:\n",
                 "DK:%s\n"%e_freq,
                 "Conductivity:%s"%cond_freq
                 )

        material = self.create({
            "Name":name,
            "DK":e_freq,
            "Cond":cond_freq
            })
        material.update()
        self.push(material.name)
        return material
        
        
    def addHfssVariableDSModle(self,name,dk=4,df=0.02,f1=1e9,cond_dc=1e-12,fB=10**12/(2*math.pi)):
        '''
        Note that the frequency unit in the formula is GHz.

        e_freq（介电常数频变）：
        e_freq=
        $dk-0.5*(($dk*$df-$cond_dc/(2*pi*$fA*1e9*e0))/atan(2*pi*$fB*1e9/(2*pi*$fA*1e9)))*ln((2*pi*$fB*1e9)**2/(2*pi*$fA*1e9)**2+1)+(($dk*$df-$cond_dc/(2*pi*$fA*1e9*e0))/atan(2*pi*$fB*1e9/(2*pi*$fA*1e9)))/2*ln((($fB*1e9)**2+Freq**2)/(($fB*1e9/exp(10*$df*($dk-0.5*(($dk*$df-$cond_dc/(2*pi*$fA*1e9*e0))/atan(2*pi*$fB*1e9/(2*pi*$fA*1e9)))*ln((2*pi*$fB*1e9)**2/(2*pi*$fA*1e9)**2+1))/(($dk*$df-$cond_dc/(2*pi*$fA*1e9*e0))/atan(2*pi*$fB*1e9/(2*pi*$fA*1e9)))))**2+Freq**2))

        cond_freq（电导率频变）：
        cond_freq=
        $cond_dc+2*pi*Freq*e0*(($dk*$df-$cond_dc/(2*pi*$fA*1e9*e0))/atan(2*pi*$fB*1e9/(2*pi*$fA*1e9)))*(atan(Freq/($fB*1e9/exp(10*$df*($dk-0.5*(($dk*$df-$cond_dc/(2*pi*$fA*1e9*e0))/atan(2*pi*$fB*1e9/(2*pi*$fA*1e9)))*ln((2*pi*$fB*1e9)**2/(2*pi*$fA*1e9)**2+1))/(($dk*$df-$cond_dc/(2*pi*$fA*1e9*e0))/atan(2*pi*$fB*1e9/(2*pi*$fA*1e9))))))-atan(Freq/($fB*1e9)))

        step1: 创建变量fA，fB，dk，df，cond_dc，增加${name}_前缀， 比如 ${name}_fA, ${name}_fB, ${name}_dk, ${name}_df, ${name}_cond_dc
        step2: 创建变量 self.layout.Variables.add(var,val)，增加${name}_前缀
        step3: 创建材料，DK= e_freq, Cond=cond_freq
        
        '''
        prefix = "%s_" % name

        dk_var = prefix + "dk"
        df_var = prefix + "df"
        fA_var = prefix + "fA"
        fB_var = prefix + "fB"
        cond_var = prefix + "cond_dc"

        self.layout.Variables.add(dk_var, dk)
        self.layout.Variables.add(df_var, df)
        self.layout.Variables.add(fA_var, f1)
        self.layout.Variables.add(fB_var, fB)
        self.layout.Variables.add(cond_var, cond_dc)

        e_freq = (
            "{dk}-0.5*((({dk}*{df}-{cond_dc}/(2*pi*{fA}*1e9*e0))/"
            "atan(2*pi*{fB}*1e9/(2*pi*{fA}*1e9))))*"
            "ln((2*pi*{fB}*1e9)**2/(2*pi*{fA}*1e9)**2+1)+"
            "((({dk}*{df}-{cond_dc}/(2*pi*{fA}*1e9*e0))/"
            "atan(2*pi*{fB}*1e9/(2*pi*{fA}*1e9))))/2*"
            "ln((({fB}*1e9)**2+Freq**2)/((((({fB}*1e9)/exp(10*{df}*({dk}-0.5*((({dk}*{df}-{cond_dc}/(2*pi*{fA}*1e9*e0))/"
            "atan(2*pi*{fB}*1e9/(2*pi*{fA}*1e9))))*ln((2*pi*{fB}*1e9)**2/(2*pi*{fA}*1e9)**2+1))/"
            "((({dk}*{df}-{cond_dc}/(2*pi*{fA}*1e9*e0))/atan(2*pi*{fB}*1e9/(2*pi*{fA}*1e9)))))))**2+Freq**2))"
        ).format(
            dk=dk_var,
            df=df_var,
            cond_dc=cond_var,
            fA=fA_var,
            fB=fB_var,
        )
        cond_freq = (
            "{cond_dc}+2*pi*Freq*e0*((({dk}*{df}-{cond_dc}/(2*pi*{fA}*1e9*e0))/"
            "atan(2*pi*{fB}*1e9/(2*pi*{fA}*1e9))))"
            "*(atan(Freq/((({fB}*1e9)/exp(10*{df}*({dk}-0.5*((({dk}*{df}-{cond_dc}/(2*pi*{fA}*1e9*e0))/"
            "atan(2*pi*{fB}*1e9/(2*pi*{fA}*1e9))))*ln((2*pi*{fB}*1e9)**2/(2*pi*{fA}*1e9)**2+1))/"
            "((({dk}*{df}-{cond_dc}/(2*pi*{fA}*1e9*e0))/atan(2*pi*{fB}*1e9/(2*pi*{fA}*1e9))))))))"
            "-atan(Freq/({fB}*1e9)))"
        ).format(
            dk=dk_var,
            df=df_var,
            cond_dc=cond_var,
            fA=fA_var,
            fB=fB_var,
        )
        
        log.info("Note that the frequency unit in the formula is GHz. ",)

        log.info("Djordjevic-Sarkar Model Parameter:\n",
                 "DK:%s\n" % e_freq,
                 "Cond:%s" % cond_freq,
                 )

        material = self.create({
            "Name":name,
            "DK":e_freq,
            "Cond":cond_freq
            })
        material.update()
        self.push(material.name)
        return material
        
        
    def addHFSSDSModle2(self,name,dk=4,df=0.02,f1=1e9,cond_dc=1e-12,fB=10**12/(2*math.pi)):
        '''
        Djordjevic-Sarkar Model Parameter Calculation in hfss
        WA<<W1=> f1>>fB
        fB default 10^12/(2*pi)
        '''
        # K = f"({dk} * {df} - {cond_dc} / (2 * pi * {freqA} * e0)) / atan({freqB} / {freqA})"
        dk = Unit(dk).V
        df = Unit(df).V
        f1 = Unit(f1).V
        fB = Unit(fB).V
        cond_dc = Unit(cond_dc).V
        w1 = 2*math.pi*f1
        wB = 2*math.pi*fB
        e0 = 8.854187817e-12  
        
        K = (dk*df-cond_dc/(w1*e0))/math.atan(wB/w1)
        e_infi = dk-0.5*K*math.log(wB**2/w1**2+1)
        e_delta = 10*df*e_infi
        fA = fB/math.exp(e_delta/K)
        log.info("Causal material set fA as: %s"%fA)
        self.addStdDSModel(name,e_infi,e_delta,fA,fB,cond_dc)


    def addStdDSModel(self,name,e_infi,e_delta,fA,fB,cond_dc=1e-12):
        e_infi = Unit(e_infi).V
        e_delta = Unit(e_delta).V
        cond_dc = Unit(cond_dc).V
        wA = 2*math.pi*Unit(fA).V
        wB = 2*math.pi*Unit(fB).V
        e0 = 8.854187817e-12  
        
        log.info("Djordjevic-Sarkar Model Parameter:\n",
                 "e_infi:%s "%e_infi,
                 "e_delta:%s "%e_delta,
                 "fA:%s "%fA,
                 "fB:%s "%fB
                 )
        
        cer = "{e_infi}+{e_delta}/ln({wB}/{wA})*ln(({wB}+1j*2*pi*Freq)/({wA}+1j*2*pi*Freq))+{cond_dc}/(1j*2*pi*Freq*e0)".format(
            e_infi=e_infi,e_delta=e_delta,wB=wB,wA=wA,cond_dc=cond_dc
            )
        dk = "re({cer})".format(cer=cer)
        df = "-im({cer})/re({cer})".format(cer=cer)
        log.info("Djordjevic-Sarkar Model Parameter:\n",
                 "DK:%s\n"%dk,
                 "DF:%s"%df
                 )
        # self.add({
        #     "Name":name,
        #     "DK":dk,
        #     "DF":df
        #     })
        material = self.create({
            "Name":name,
            "DK":dk,
            "DF":df
            })
        material.update()
        self.push(material.name)
        return material
    
    def getByName(self,name):
        '''
        Args:
            name (str): material name in lib, ingor case
        Returns:
            (material): material object of material name
             
        Raises:
            material name not found in lib
        '''
#         oDefinitionManager = self.layout.oProject.GetDefinitionManager()
#         if not oDefinitionManager.DoesMaterialExist(name): #only for project material
#             raise Exception("Material not definition: %s"%name)
#         oMaterialManager = oDefinitionManager.GetManager("Material")
        rst = super(self.__class__,self).getByName(name)
        if rst:
            return rst
        else:
            temp =  Material(name,layout=self.layout)
            if temp.Array.Datas:
                return temp
            else:
                return None
            
