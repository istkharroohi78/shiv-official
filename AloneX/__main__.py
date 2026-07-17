# Copyright (c) 2026 THE SHIV
# Licensed under the MIT License.
# This file is part of MahiMusic
# DEVELOPER - THE SHIV

import asyncio
import importlib

from pyrogram import idle

from AloneX import (anon, app, db,
                    logger, stop, userbot)
from AloneX.plugins import all_modules

# ✅ Auto-clean function ko yahan import kiya gaya hai
from AloneX.core.dir import auto_clean_downloads


async def main():
    await db.connect()
    await app.boot()
    await userbot.boot()
    await anon.boot()

    for module in all_modules:
        importlib.import_module(f"AloneX.plugins.{module}")
    logger.info(f"Loaded {len(all_modules)} modules.")

    sudoers = await db.get_sudoers()
    app.sudoers.update(sudoers)
    app.bl_users.update(await db.get_blacklisted())
    logger.info(f"Loaded {len(app.sudoers)} sudo users.")

    # ✅ Yahan par auto-clean task ko background mein start kar diya gaya hai
    asyncio.create_task(auto_clean_downloads())
    logger.info("Auto-clean storage monitor started.")

    await idle()
    await stop()


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        pass
