#--- coding:utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20260704

from __future__ import absolute_import


def with_metaclass(meta, *bases):
    class TemporaryClass(object):
        pass
    return meta("TemporaryClass", bases or (object,), {"__module__": __name__})

class SetupsBase(type):
    def __call__(cls, *args, **kwargs):
        layout = kwargs.get("layout")
        if layout is None:
            for arg in args:
                if hasattr(arg, "DesignType"):
                    layout = arg
                    break

        if layout is None:
            raise ValueError("layout with DesignType is required.")

        # 根据条件选择目标模块
        if layout.DesignType == 'HFSS':
            from . import hfssSetup as Setups
        elif layout.DesignType == 'HFSS 3D Layout Design':
            from . import hfss3DLayoutSetup as Setups
        else:
            raise ValueError("Unsupported DesignType: %s" % getattr(layout, "DesignType", None))

        # 按当前占位类名分发到对应实现类
        targetClass = getattr(Setups, cls.__name__)
        return targetClass(*args, **kwargs)



class SetupBase(type):
    def __call__(cls, *args, **kwargs):
        layout = kwargs.get("layout")
        if layout is None:
            for arg in args:
                if hasattr(arg, "DesignType"):
                    layout = arg
                    break

        if layout is None:
            raise ValueError("layout with DesignType is required.")

        # 根据条件选择目标模块
        if layout.DesignType == 'HFSS':
            from . import hfssSetup as Setup
        elif layout.DesignType == 'HFSS 3D Layout Design':
            from . import hfss3DLayoutSetup as Setup
        else:
            raise ValueError("Unsupported DesignType: %s" % getattr(layout, "DesignType", None))

        # 按当前占位类名分发到对应实现类
        targetClass = getattr(Setup, cls.__name__)
        return targetClass(*args, **kwargs)


class SweepsBase(type):
    def __call__(cls, *args, **kwargs):
        layout = kwargs.get("layout")
        if layout is None:
            for arg in args:
                if hasattr(arg, "DesignType"):
                    layout = arg
                    break

        if layout is None:
            raise ValueError("layout with DesignType is required.")

        # 根据条件选择目标模块
        if layout.DesignType == 'HFSS':
            from . import hfssSetup as Sweeps
        elif layout.DesignType == 'HFSS 3D Layout Design':
            from . import hfss3DLayoutSetup as Sweeps
        else:
            raise ValueError("Unsupported DesignType: %s" % getattr(layout, "DesignType", None))

        # 按当前占位类名分发到对应实现类
        targetClass = getattr(Sweeps, cls.__name__)
        return targetClass(*args, **kwargs)


class SweepBase(type):
    def __call__(cls, *args, **kwargs):
        layout = kwargs.get("layout")
        if layout is None:
            for arg in args:
                if hasattr(arg, "DesignType"):
                    layout = arg
                    break

        if layout is None:
            raise ValueError("layout with DesignType is required.")

        # 根据条件选择目标模块
        if layout.DesignType == 'HFSS':
            from . import hfssSetup as Sweep
        elif layout.DesignType == 'HFSS 3D Layout Design':
            from . import hfss3DLayoutSetup as Sweep
        else:
            raise ValueError("Unsupported DesignType: %s" % getattr(layout, "DesignType", None))

        # 按当前占位类名分发到对应实现类
        targetClass = getattr(Sweep, cls.__name__)
        return targetClass(*args, **kwargs)


class Sweep(with_metaclass(SweepBase, object)):
    pass


class Sweeps(with_metaclass(SweepsBase, object)):
    pass


class Setup(with_metaclass(SetupBase, object)):
    pass


class Setups(with_metaclass(SetupsBase, object)):
    pass