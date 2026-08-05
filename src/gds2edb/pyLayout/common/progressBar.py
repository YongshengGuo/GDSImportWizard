#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20240710


'''
ProgressBar is used to show progress of for loop or function need long time cost
'''
from __future__ import print_function

import re
import os
import sys
import time
from threading import Thread,Event

class ProgressBar(object):

    def __init__(self,total=100,prompt="progress",step=3):
        self.total = total
        self.prompt = prompt
        self.step = step
        self.pos = 0
        self.temp = 0
        self.start = None
        self.event = None
        
    def showPercent(self,pos=None):
        '''
        当指定数量时使用，显示进度百分比
        '''
        
        if self.start == None:
            self.start = time.time()
        if pos==None:
            self.pos +=1
        else:
            self.pos = pos
            
        progress = int(self.pos*100/self.total)
        if progress>self.temp:
#             print("\r{} %{}: {}".format(self.prompt,progress, "#" * (int(progress/self.step)+1)),end="")
            finsh = "▓" * int(progress/self.step+1)
            need_do = "-" * int(100/self.step - int(progress/self.step+1))
            dur = time.time() - self.start
            print("\r{}: {:^3.0f}%[{}->{}]  {:.2f}s  ".format(self.prompt,float(progress), finsh, need_do, dur), end="")          
#             sys.stdout.flush()
            self.temp = progress
    
    def _animatedProgress(self,prompt,event):
        
        total = 100
        pos = 0
        step = 3
        start = time.time()
        dur = 0
        
        while True:
#             print("_animatedProgress")
            progress = int(pos*100/total)%100
            pos += 1

            finsh = "*" * int(progress/step+1)
            need_do = "-" * int(100/step - int(progress/step+1))
            dur = time.time() - start
            print("\r{}: {}[{}->{}]  {:.2f}s  ".format(prompt,"Running", finsh, need_do, dur), end="")       
#             print("\r{}: {}[{}->{}]  {:.2f}s  ".format(prompt,progress, finsh, need_do, dur), end="")      
#             sys.stdout.flush()
            
            if event.is_set():
                break
            
#             if dur>20:
#                 break
            
            time.sleep(0.1)

    def _train(self,prompt,event):
        # 火车的文本表示  
        train = "═╚⊙══⊙╝" 
          
        # 火车动画的长度（即屏幕宽度）  
        screen_width = 20  
          
        # 火车的初始位置  
        train_pos = 0  
          
        # 清除屏幕的简单方法（在Windows中）  
        def clear_screen():  
            print("\r" * (screen_width + len(train[-1]) + 1), end="")  
          
        try:  
            while True:  
                # 清除屏幕  
                clear_screen()  
          
                # 打印空格来模拟火车移动  
                print(" " * train_pos, end="")  
                print(train, end="")
                
#                 # 打印火车的当前形态  
#                 for part in train:  
#                     print(part, end="")  
#                     time.sleep(0.1)  # 延迟来创建动画效果  
                  
                print("\r" * (len(train) + 1), end="")  # 回到行首，准备下一次打印  
          
                # 更新火车位置  
                train_pos += 1  
                if train_pos > screen_width:  
                    train_pos = 0  
          
                # 控制动画速度  
                time.sleep(0.5)  
                if event.is_set():
                    break
          
        except KeyboardInterrupt:  
            print("\n动画结束")


                
    def showProgress(self):
        '''
        不指定数据长度，只显示进度条，指示状态信息
        '''
        
        
        self.event = Event()
        thread1 = Thread(target=self._animatedProgress, args=(self.prompt,self.event))
        # Prefer modern API and keep compatibility with Python 2.7.
        try:
            thread1.daemon = True #3.7
        except AttributeError:
            thread1.setDaemon(True) #2.7
        thread1.start()
#         thread.join()
        
    def stop(self):
        if self.event:
            self.event.set()
        time.sleep(1) #wait for last log output
        print("{} finished.".format(self.prompt))


def ShowProcessBar(prompt=""):
    def wrapper(func):
        def wrapped_function(*args, **kwargs):
            bar = ProgressBar(prompt=prompt)
            bar.showProgress()
            try:
                return func(*args, **kwargs)
            finally:
                bar.stop()
        return wrapped_function
    return wrapper