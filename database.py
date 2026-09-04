import aiosqlite

async def init_db():
    async with aiosqlite.connect("maple_bot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                nickname TEXT PRIMARY KEY,
                ocid TEXT,
                level INTEGER
            )
        """)
        await db.commit()

async def add_alert(nickname, ocid, level):
    async with aiosqlite.connect("maple_bot.db") as db:
        await db.execute("INSERT OR REPLACE INTO alerts VALUES (?, ?, ?)", (nickname, ocid, level))
        await db.commit()

async def remove_alert(nickname):
    async with aiosqlite.connect("maple_bot.db") as db:
        await db.execute("DELETE FROM alerts WHERE nickname = ?", (nickname,))
        await db.commit()

async def get_all_alerts():
    async with aiosqlite.connect("maple_bot.db") as db:
        async with db.execute("SELECT * FROM alerts") as cursor:
            return await cursor.fetchall()

async def get_all_nicknames():
    async with aiosqlite.connect("maple_bot.db") as db:
        async with db.execute("SELECT nickname FROM alerts") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

# [추가] 이미 등록된 닉네임인지 확인하는 함수
async def is_alert_exists(nickname):
    async with aiosqlite.connect("maple_bot.db") as db:
        async with db.execute("SELECT 1 FROM alerts WHERE nickname = ?", (nickname,)) as cursor:
            row = await cursor.fetchone()
            return row is not None