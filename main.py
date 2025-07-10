# coding=utf-8
import ctypes
from ctypes import wintypes
import sys
from datetime import datetime
import asyncio
import astrbot.api.event.filter as filter
import psutil
from astrbot.api.event.filter import event_message_type, EventMessageType
from astrbot.api.all import AstrMessageEvent, Context, Image, Plain, Node, Reply, At
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

process_dict = {
    "windowsterminal" : "cmd",
    "taskmgr" : "任务管理器",
    "360desktopservice64" : "桌面",
    "notepad" : "记事本",
    "explorer" : "文件夹",
    "calc": "计算器",
    "mspaint": "画图",
    "SnippingTool": "截图工具",
    "msedge": "Edge",
    "PhotosApp": "照片",
    "Camera": "相机",
    "Clock": "时钟",
    "Calendar": "日历",
    "Mail": "邮件",
    "Maps": "地图",
    "Microsoft.ZuneVideo": "电影和电视",
    "Microsoft.ZuneMusic": "音乐",
    "SoundRecorder": "录音机",
    "Wordpad": "写字板",
    "mstsc": "远程桌面",
    "regedit": "注册表",
    "services": "服务",
    "eventvwr": "事件查看器",
    "control": "控制面板",
    "mssettings": "设置",
    "SecurityHealthSystray": "Windows安全中心",
    "WindowsTerminal": "终端",
    "cmd": "命令提示符",
    "powershell": "PowerShell",

    "chrome": "Chrome",
    "firefox": "Firefox",
    "wechat": "微信",
    "DingTalk": "钉钉",
    "AcroRd32": "Adobe阅读器",
    "FoxitReader": "福昕阅读器",
    "QQMusic": "QQ音乐",
    "cloudmusic": "网易云音乐",
    "baidunetdisk": "百度网盘",
    "Code": "VS Code",
    "pycharm64": "PyCharm",
    "idea64": "IDEA",
    "studio64": "Android Studio",
    "steamwebhelper": "Steam",
    "EpicGamesLauncher": "Epic",
    "Battle.net Launcher": "战网",
    "360Safe": "360安全卫士",
    "QQPCMgr": "腾讯电脑管家",
    "SogouInput": "搜狗输入法",
    "BaiduPinyin": "百度输入法",
    "DingTalkLauncher": "钉钉",
    "feishu": "飞书",
    "NeteaseMail": "网易邮箱",
    "AliyunDrive": "阿里云盘",
    "TencentDocs": "腾讯文档",
    "Aria2c": "Aria2下载器",
    "Thunder": "迅雷",
    "WeChatWork": "企业微信",
    "DingTalkPC": "钉钉",
    "NetSarangXshell": "Xshell",
    "NetSarangXftp": "Xftp",
    "PotplayerMini": "PotPlayer",
    "DBCamera": "大白摄像头",
    "ScreenToGif": "Gif录制器",
    "FreeDownloadManager": "FDM",
    "GeekUninstaller": "Geek卸载器",
}

def 获取cpu负载() -> str:
    percent = (psutil.cpu_percent(interval=0.1) + psutil.cpu_percent(interval=0.1)) / 2.0
    return f"{int(percent)}%"

def 获取活动窗口名称() -> str:
    '''
        获取当前活跃的窗口的进程名称, 尝试使用process_dict表替换为中文名称
    '''
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)

        # 设置函数原型
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD

        # 获取前台窗口句柄
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""

        # 获取进程ID
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        if pid.value == 0:
            return ""

        名称 = psutil.Process(pid.value).name().lower().replace('.exe', '')

        # 替换为指定名称, 若字典无对应名称则返回原名称
        名称 = process_dict.get(名称, 名称)

    except Exception as e:
        logger.warning(f"名称获取失败: {e}")
        return ""

    if len(名称) > 10:
        名称 = 名称[:8] + '..'

    return 名称

@register("astrbot_plugin_sysinfo_nickupdater", "周佳豪", "系统状态昵称", "1.0.0",
          "https://github.com/zhoujiahao111/astrbot_plugin_sysinfo_nickupdater")
class sysinfoNickupdater(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)

        self.默认昵称 = config.get("default_nickname", None)
        if self.默认昵称 is None:
            logger.warning(f"未配置默认昵称!")
            return

        self.是否获取活动窗口名称 = config.get("active_window_monitoring", True)
        self.事件对象 = None
        self.轮询时间 = int(config.get("time", 3600))

        asyncio.create_task(self.定时轮询任务())

    @event_message_type(EventMessageType.ALL)
    async def 获取事件对象(self, event: AstrMessageEvent):
        '''
        获取一次event事件并存储, 之后的代码借助event对象执行方法
        '''
        if self.事件对象:
            return

        self.事件对象 = event

    async def 获取群列表(self) -> list[str]:
        payloads = {
            "no_cache": True,
        }
        try:
            结果 = await self.事件对象.bot.api.call_action("get_group_list", **payloads)
        except Exception as e:
            # logger.warning(f"群{id} 名称修改失败: "+str(e))
            return []

        # 返回群列表
        return [str(i["group_id"]) for i in 结果]


    async def 修改昵称(self):
        '''
            获取群列表, 迭代并修改群名片
        '''

        cpu负载 = 获取cpu负载()
        活动窗口名称 = ""

        if self.是否获取活动窗口名称:
            if sys.platform != "win32":
                logger.warning(f"非windows系统, 不兼容喵")
                return

            活动窗口名称 = 获取活动窗口名称()

        昵称 = "|".join([
            self.默认昵称,
            f"🧠{cpu负载}",
            f"🖥️{活动窗口名称}",
            "🔄"+datetime.now().strftime(("%#m-%#d %#H:%#M"))
        ])

        for id in await self.获取群列表():
            payloads = {
                "group_id": id,
                "user_id": self.事件对象.get_self_id(),
                "card": 昵称
            }
            try:
                await self.事件对象.bot.api.call_action("set_group_card", **payloads)
            except Exception as e:
                # logger.warning(f"群{id} 名称修改失败: "+str(e))
                pass

    @filter.command("刷新昵称状态")
    async def 手动刷新(self, event: AstrMessageEvent):
        await self.修改昵称()
        yield event.plain_result("刷新完毕!")

    async def 定时轮询任务(self):
        '''
            初始化后, 需要先接收到一次event才能正常使用
        '''
        while True:
            await asyncio.sleep(self.轮询时间)

            if self.事件对象 is None:
                logger.warning(f"本次任务未获取到消息事件")
            else:
                await self.修改昵称()


