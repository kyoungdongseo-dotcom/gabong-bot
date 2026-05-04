import asyncio
import pkgutil
import importlib
from pathlib import Path
from telegram.ext import ApplicationBuilder
import config
from utils import init_database, scheduler, send_daily_summary, check_changes

PLUGIN_DIRECTORY = Path("plugins")


def load_plugins(enabled_names):
    plugins = []
    if not PLUGIN_DIRECTORY.exists():
        print("plugins 디렉토리가 존재하지 않습니다.")
        return plugins

    for finder, module_name, ispkg in pkgutil.iter_modules([str(PLUGIN_DIRECTORY)]):
        if not module_name.endswith("_plugin"):
            continue
        plugin_name = module_name[: -len("_plugin")]
        if enabled_names and plugin_name not in enabled_names:
            continue
        try:
            module = importlib.import_module(f"plugins.{module_name}")
            plugins.append((plugin_name, module))
            print(f"로딩된 플러그인: {plugin_name}")
        except Exception as e:
            print(f"플러그인 로드 실패: {module_name} -> {e}")
    return plugins


async def post_init(app):
    init_database()
    loop = asyncio.get_running_loop()
    scheduler.configure(event_loop=loop)
    scheduler.start()
    for _, plugin in loaded_plugins:
        if hasattr(plugin, "post_init"):
            try:
                result = plugin.post_init(app)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"플러그인 post_init 오류: {plugin.__name__} -> {e}")
    scheduler.add_job(send_daily_summary, 'cron', hour=20, minute=0, args=[app.bot], id="daily_summary")
    asyncio.create_task(check_changes(app))


enabled_plugins = config.get("enabled_plugins") or []
loaded_plugins = load_plugins(enabled_plugins)

app = ApplicationBuilder().token(config.get("telegram_token")).post_init(post_init).build()

for plugin_name, plugin in loaded_plugins:
    if hasattr(plugin, "register"):
        try:
            plugin.register(app, config)
        except Exception as e:
            print(f"플러그인 등록 실패: {plugin_name} -> {e}")
    else:
        print(f"플러그인에 register 함수가 없습니다: {plugin_name}")

print("봇 시작!")
app.run_polling(allowed_updates=["message", "message_reaction"])
