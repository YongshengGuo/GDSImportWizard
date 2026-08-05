#coding:utf-8
'''
    ##模块功能：
    初始化日志属性、生成日志文件、返回日志文件的日志器, 可以被调用打印日志文件

    Examples:
        1.从log文件导入Log类
        >>> from log import Log
        
        2.实例化类Log()后使用其方法setPath()设置log文件完整路径
        >>> log = Log() #默认log Level是DEBUG(即全部都打印)
        >>> log = Log('Error') #指定log Level是Error, (Optional)
        
        >>> log.setPath(r'C:\Temp\logfile.log') #必须设置log文件全名称
        
        3.设置log Level (Optional)
        >>> logger.setLogLevel('Error')
                总共5个log级别,目前默认是DEBUG(即全部都打印)
        
        4.打印日志        
        >>> log.debug('debug,用来打印一些调试信息，级别最低')
        >>> log.info('info,用来打印一些正常的操作信息')
        >>> log.warning('waring,用来用来打印警告信息')
        >>> log.error('error,一般用来打印一些错误信息')
        >>> log.critical('critical,用来打印一些致命的错误信息，等级最高')

'''
import os,sys
import logging
import shutil
import tempfile
from datetime import datetime


def isSamePath(path1,path2):
    """
    判定两个文件路径是否相同（os.path 实现）
    :param path1: 第一个文件路径（字符串）
    :param path2: 第二个文件路径（字符串）
    :return: 路径是否相同（布尔值）
    """
    # 步骤1：转换为绝对路径（消除相对路径歧义）
    abs_path1 = os.path.abspath(path1)
    abs_path2 = os.path.abspath(path2)
    
    # 步骤2：规范化路径（处理分隔符、末尾斜杠、上级目录../等问题）
    norm_path1 = os.path.normpath(abs_path1)
    norm_path2 = os.path.normpath(abs_path2)
    
    # 步骤3：比较规范化后的绝对路径
    return norm_path1 == norm_path2


def switchLogPath(logger,newLogPath, copyOldContent=True, mode='a'):
    """
    动态切换logger的文件处理器到新路径，并可选择复制旧日志内容

    参数:
        logger: 要操作的logging.Logger对象
        newLogPath: 新的日志文件完整路径
        copyOldContent: 是否将旧日志文件内容复制到新文件（默认True）
        mode: 新文件的打开模式，默认'a'（追加模式）
    """
    
    # 1. 查找logger中现有的FileHandler
    old_file_handler = None
    old_log_path = None
    
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            old_file_handler = handler
            # 获取当前日志文件路径
            if hasattr(handler, 'baseFilename'):
                old_log_path = handler.baseFilename
            break
        
    if not old_log_path:
        new_file_handler = logging.FileHandler(newLogPath, mode=mode, encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        new_file_handler.setFormatter(formatter)
        logger.addHandler(new_file_handler)
        return newLogPath
        
    if isSamePath(newLogPath, old_log_path):
        return newLogPath
    
    # 确保新路径的目录存在
#     os.makedirs(os.path.dirname(os.path.abspath(newLogPath)), exist_ok=True) 
    
    #兼容 Python 2.7 和 Python 3.10 的多级目录创建函数
    try:
        # 递归创建多级目录，两个版本均支持核心功能
        os.makedirs(os.path.dirname(os.path.abspath(newLogPath)))
    except OSError as e:
        # 捕获异常：仅忽略「目录已存在」的情况，其他异常正常抛出
        # errno.EEXIST：错误码，表示「文件/目录已存在」（跨平台兼容）
        import errno
        if e.errno != errno.EEXIST:
            raise  # 重新抛出非「目录已存在」的异常（如权限不足、路径非法等）
        else:
            # 可选：打印日志，提示目录已存在
            # print(f"目录已存在，无需重复创建：{dir_path}")
            pass
    

    # 2. 如果需要，复制旧日志内容到新文件
    if copyOldContent and old_log_path and os.path.exists(old_log_path):
        try:
            # 以二进制方式复制文件，保留所有格式
            shutil.copy2(old_log_path, newLogPath)
        except Exception as e:
            pass
    
    # 3. 如果存在旧的FileHandler，则移除它
    if old_file_handler:
        # 先刷新并关闭旧处理器
        old_file_handler.flush()
        old_file_handler.close()
        logger.removeHandler(old_file_handler)
    
    # 4. 创建新的FileHandler
    new_file_handler = logging.FileHandler(newLogPath, mode=mode, encoding='utf-8')
    
    # 复制旧处理器的格式（如果存在），否则使用默认格式
    if old_file_handler and old_file_handler.formatter:
        new_file_handler.setFormatter(old_file_handler.formatter)
    else:
        # 设置一个默认格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        new_file_handler.setFormatter(formatter)
    
    # 5. 添加新的FileHandler到logger
    logger.addHandler(new_file_handler)
    return old_log_path


class Log(object):
    # 初始化日志
    def __init__(self, logLevel='DEBUG', logPath = None):
        '''
        Args:
            >>> logLevel(str): 打印log日志的级别, 默认是DEBUG以上级别(即全部打印),optional
        '''
        if logPath:
            self._logPath = logPath
        else:
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 生成日志文件名
            log_filename = "pylayout_Log_{timestamp}.log".format(timestamp=timestamp)
            log_path = os.path.join(temp_dir, log_filename)
            self._logPath = log_path
            
        self._logLevel = logLevel
#         self._logFormat = '%(filename)s-%(lineno)s: - %(asctime)s - %(levelname)s: %(message)s'
        self._logFormat = '%(asctime)s - %(levelname)s: %(message)s'
        self._datefmt = "%Y/%m/%d %X"
        
        self.logger = logging.getLogger()
        self.file_handler = None
        
        # 显式设置控制台输出编码为 UTF-8，避免 Windows 下 charmap 编码错误
        # Python 3.7+ 支持 reconfigure 方法
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self.console_handler)
        self.setPath(self._logPath)
        
        self.setLogLevel(self._logLevel)
        self.setLogFormat()
        
    
    def __del__(self):
        if self.file_handler:
            self.file_handler.close()
        if self.console_handler:
            self.console_handler.close()
        logging.shutdown()
    
    
    def setLogLevel(self,logLevel=None):
        '''
        #用来设置LogLevel
        Args:
            logLevel(str): 打印log日志的级别, 默认是DEBUG以上级别(即全部打印), 字段包含CRITICAL > ERROR > WARNING > INFO > DEBUG, 不区分大小写, optional
        '''
        if logLevel:
            self._logLevel = logLevel.upper()
        
        level = eval('logging.' + self._logLevel.upper())
        self.logger.setLevel(level)
        for handle in self.logger.handlers:
            handle.setLevel(level)

        
    def setPath(self,logPath=None):
        '''
        Args:
            logPath(str): log文件完整路径
        '''
        if not logPath:
            return
        
        self.logPath = logPath
        
        if self.file_handler:
            self.file_handler.close()
            self.logger.removeHandler(self.file_handler)
            
        # 显式设置文件编码为 UTF-8，避免 Windows 下 charmap/cp1252 编码错误
        self.file_handler = logging.FileHandler(logPath, mode='a', encoding='utf-8')
        self.logger.addHandler(self.file_handler)
        self.setLogFormat()
        self.setLogLevel()
  
            
    def setLogFormat(self,logFormat = None,datefmt = None):
        # 1、设置formatter，日志的输出格式
        if logFormat:
            self._logFormat = logFormat
        if datefmt:
            self._datefmt = datefmt
            
        fmt = logging.Formatter(self._logFormat,self._datefmt)
        for hdlr in self.logger.handlers:
            hdlr.setFormatter(fmt)
        
    def aedtMessage(self,content):
        Module = sys.modules['__main__']
        oDesktop = None
        if hasattr(Module, "oDesktop"):
            oDesktop = getattr(Module, "oDesktop")
            
        if oDesktop:
            oDesktop.AddMessage("","",0,content)
        else:
            return
        
    def debug(self,content,*args):
        self.logger.debug(content+",".join(args))
#         self.aedtMessage(content)

    def info(self,content,*args):
        self.logger.info(str(content)+",".join(list(args)))
#         self.aedtMessage(content+",".join(args))
           
    def warning(self,content,*args):
        self.logger.warning(str(content)+",".join(args))
        self.aedtMessage(str(content)+",".join(args))
            
    def error(self,content,*args):
        self.logger.error(str(content)+",".join(args))
        self.aedtMessage(str(content)+",".join(args))
           
    def critical(self,content,*args):
        self.logger.critical(str(content)+",".join(args))
        self.aedtMessage(str(content)+",".join(args))
        
    def exception(self,content,*args):
        content = Exception(str(content)+",".join(args))
        self.logger.error(content)
        raise content

    #for debug
    def messageBox(self,content):
        from System.Windows.Forms import MessageBox
        MessageBox.Show(str(content))
        
    def switchLogPath(self, newLogPath, copyOldContent=True, mode='a'):
        return switchLogPath(self.logger,newLogPath, copyOldContent, mode)
        
        