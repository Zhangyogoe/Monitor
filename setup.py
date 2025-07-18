#!/usr/bin/env python3
"""
飞书自动推送机器人 - 一键安装配置脚本
为小白用户提供简单的安装和配置流程
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

class FeishuBotSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.env_file = self.project_root / ".env"
        
    def print_banner(self):
        """打印欢迎横幅"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                    飞书自动推送机器人                        ║
║                  一键安装配置向导                            ║
║                                                              ║
║  🤖 智能内容抓取  📊 多维表格集成  🔔 自动推送              ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
    def check_python_version(self):
        """检查Python版本"""
        print("\n🔍 检查Python环境...")
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ 需要Python 3.8或更高版本")
            print(f"   当前版本: Python {version.major}.{version.minor}.{version.micro}")
            print("   请升级Python后重试")
            return False
        print(f"✅ Python版本检查通过: Python {version.major}.{version.minor}.{version.micro}")
        return True
    
    def create_virtual_environment(self):
        """创建虚拟环境"""
        print("\n📦 创建Python虚拟环境...")
        
        if self.venv_path.exists():
            print("✅ 虚拟环境已存在")
            return True
            
        try:
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], 
                         check=True, capture_output=True)
            print("✅ 虚拟环境创建成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 创建虚拟环境失败: {e}")
            return False
    
    def get_pip_executable(self):
        """获取pip可执行文件路径"""
        if platform.system() == "Windows":
            return self.venv_path / "Scripts" / "pip.exe"
        else:
            return self.venv_path / "bin" / "pip"
    
    def install_dependencies(self):
        """安装依赖包"""
        print("\n📥 安装项目依赖...")
        
        pip_exe = self.get_pip_executable()
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            print("❌ requirements.txt文件不存在")
            return False
            
        try:
            # 升级pip
            subprocess.run([str(pip_exe), "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # 安装依赖
            subprocess.run([str(pip_exe), "install", "-r", str(requirements_file)], 
                         check=True, capture_output=True)
            print("✅ 依赖安装成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            return False
    
    def configure_environment(self):
        """配置环境变量"""
        print("\n⚙️ 配置系统参数...")
        
        if self.env_file.exists():
            print("✅ 配置文件已存在，跳过配置步骤")
            return True
        
        print("\n请按照提示输入配置信息（按回车使用默认值）：")
        
        # 获取用户输入
        configs = {}
        
        # 飞书配置
        print("\n🔗 飞书机器人配置：")
        configs['FEISHU_WEBHOOK_URL'] = input("飞书Webhook URL（必填）: ").strip()
        if not configs['FEISHU_WEBHOOK_URL']:
            print("❌ Webhook URL是必填项")
            return False
            
        configs['FEISHU_WEBHOOK_SECRET'] = input("飞书Webhook密钥（可选）: ").strip()
        
        # 多维表格配置
        print("\n📊 飞书多维表格配置（可选）：")
        configs['FEISHU_APP_ID'] = input("飞书应用ID: ").strip()
        configs['FEISHU_APP_SECRET'] = input("飞书应用密钥: ").strip()
        configs['FEISHU_BITABLE_TOKEN'] = input("多维表格Token: ").strip()
        configs['FEISHU_TABLE_ID'] = input("表格ID: ").strip()
        
        # 系统配置
        print("\n🔧 系统配置：")
        configs['SECRET_KEY'] = input("系统密钥（留空自动生成）: ").strip()
        if not configs['SECRET_KEY']:
            import secrets
            configs['SECRET_KEY'] = secrets.token_hex(32)
        
        configs['DEBUG'] = input("调试模式 (true/false) [false]: ").strip() or "false"
        
        # 写入配置文件
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write("# 飞书自动推送机器人配置文件\n")
                f.write("# 请根据实际情况修改以下配置\n\n")
                
                f.write("# 基础配置\n")
                f.write(f"SECRET_KEY={configs['SECRET_KEY']}\n")
                f.write(f"DEBUG={configs['DEBUG']}\n")
                f.write("DATABASE_URL=sqlite:///feishu_bot.db\n\n")
                
                f.write("# 飞书Webhook配置\n")
                f.write(f"FEISHU_WEBHOOK_URL={configs['FEISHU_WEBHOOK_URL']}\n")
                if configs['FEISHU_WEBHOOK_SECRET']:
                    f.write(f"FEISHU_WEBHOOK_SECRET={configs['FEISHU_WEBHOOK_SECRET']}\n")
                f.write("\n")
                
                f.write("# 飞书多维表格配置（可选）\n")
                if configs['FEISHU_APP_ID']:
                    f.write(f"FEISHU_APP_ID={configs['FEISHU_APP_ID']}\n")
                if configs['FEISHU_APP_SECRET']:
                    f.write(f"FEISHU_APP_SECRET={configs['FEISHU_APP_SECRET']}\n")
                if configs['FEISHU_BITABLE_TOKEN']:
                    f.write(f"FEISHU_BITABLE_TOKEN={configs['FEISHU_BITABLE_TOKEN']}\n")
                if configs['FEISHU_TABLE_ID']:
                    f.write(f"FEISHU_TABLE_ID={configs['FEISHU_TABLE_ID']}\n")
                f.write("\n")
                
                f.write("# 爬虫配置\n")
                f.write("CRAWLER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\n")
                f.write("CRAWLER_REQUEST_DELAY=2\n")
                f.write("CRAWLER_MAX_RETRIES=3\n")
                f.write("CRAWLER_TIMEOUT=30\n\n")
                
                f.write("# 调度器配置\n")
                f.write("SCHEDULER_TIMEZONE=Asia/Shanghai\n")
                f.write("SCHEDULER_MAX_WORKERS=4\n\n")
                
                f.write("# 日志配置\n")
                f.write("LOG_LEVEL=INFO\n")
            
            print("✅ 配置文件创建成功")
            return True
            
        except Exception as e:
            print(f"❌ 创建配置文件失败: {e}")
            return False
    
    def initialize_database(self):
        """初始化数据库"""
        print("\n🗄️ 初始化数据库...")
        
        python_exe = self.get_python_executable()
        init_script = self.project_root / "init_data.py"
        
        if not init_script.exists():
            print("❌ 数据库初始化脚本不存在")
            return False
        
        try:
            subprocess.run([str(python_exe), str(init_script)], 
                         check=True, cwd=str(self.project_root))
            print("✅ 数据库初始化成功")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 数据库初始化失败: {e}")
            return False
    
    def get_python_executable(self):
        """获取Python可执行文件路径"""
        if platform.system() == "Windows":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"
    
    def create_startup_scripts(self):
        """创建启动脚本"""
        print("\n📝 创建启动脚本...")
        
        # Windows启动脚本
        start_bat = self.project_root / "start.bat"
        with open(start_bat, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write('echo 正在启动飞书自动推送机器人...\n')
            f.write('cd /d "%~dp0"\n')
            f.write(f'"{self.get_python_executable()}" start.py\n')
            f.write('pause\n')
        
        # Linux/Mac启动脚本
        start_sh = self.project_root / "start.sh"
        with open(start_sh, 'w', encoding='utf-8') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "正在启动飞书自动推送机器人..."\n')
            f.write('cd "$(dirname "$0")"\n')
            f.write(f'"{self.get_python_executable()}" start.py\n')
        
        # 给脚本执行权限
        if platform.system() != "Windows":
            os.chmod(start_sh, 0o755)
        
        print("✅ 启动脚本创建成功")
        return True
    
    def create_desktop_shortcut(self):
        """创建桌面快捷方式（Windows）"""
        if platform.system() != "Windows":
            return True
            
        print("\n🖱️ 创建桌面快捷方式...")
        
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "飞书自动推送机器人.lnk")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = str(self.project_root / "start.bat")
            shortcut.WorkingDirectory = str(self.project_root)
            shortcut.IconLocation = str(self.project_root / "start.bat")
            shortcut.save()
            
            print("✅ 桌面快捷方式创建成功")
            return True
        except ImportError:
            print("⚠️ 无法创建桌面快捷方式（缺少依赖库）")
            return True
        except Exception as e:
            print(f"⚠️ 创建桌面快捷方式失败: {e}")
            return True
    
    def show_completion_info(self):
        """显示安装完成信息"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                      🎉 安装完成！                           ║
╚══════════════════════════════════════════════════════════════╝

📋 使用说明：

1️⃣  启动系统：
   Windows: 双击 start.bat 或运行桌面快捷方式
   Linux/Mac: 运行 ./start.sh

2️⃣  管理界面：
   打开浏览器访问: http://localhost:5000

3️⃣  配置步骤：
   - 添加要监控的网站
   - 设置关键词和分类
   - 配置定时任务
   - 测试推送功能

4️⃣  重要文件：
   - .env: 配置文件（可手动编辑）
   - feishu_bot.db: 数据库文件（请定期备份）
   - logs/: 日志文件夹

⚠️  注意事项：
   - 首次使用需要配置网站和关键词
   - 确保飞书机器人配置正确
   - 定期查看日志确保系统正常运行

📚 更多帮助：
   查看 README.md 文件或访问项目文档

祝您使用愉快！ 🚀
        """)
    
    def run_setup(self):
        """运行完整安装流程"""
        self.print_banner()
        
        # 检查环境
        if not self.check_python_version():
            return False
        
        # 创建虚拟环境
        if not self.create_virtual_environment():
            return False
        
        # 安装依赖
        if not self.install_dependencies():
            return False
        
        # 配置环境
        if not self.configure_environment():
            return False
        
        # 初始化数据库
        if not self.initialize_database():
            return False
        
        # 创建启动脚本
        if not self.create_startup_scripts():
            return False
        
        # 创建桌面快捷方式
        self.create_desktop_shortcut()
        
        # 显示完成信息
        self.show_completion_info()
        
        return True

def main():
    """主函数"""
    setup = FeishuBotSetup()
    
    try:
        success = setup.run_setup()
        if success:
            print("\n✅ 安装完成！按任意键退出...")
        else:
            print("\n❌ 安装失败！请检查错误信息后重试...")
        
        input()  # 等待用户按键
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断安装")
    except Exception as e:
        print(f"\n❌ 安装过程中发生错误: {e}")
        print("请检查错误信息并重试")

if __name__ == "__main__":
    main() 