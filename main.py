import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from api_client import get_ocid, get_character_basic, get_character_stat, get_character_items
from database import init_db, add_alert, remove_alert, get_all_alerts, get_all_nicknames, is_alert_exists

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# [추가] 전투력 숫자 포맷 함수
def format_combat_power(power) -> str:
    # 숫자가 아니거나 '정보 없음' 등의 문자열인 경우 그대로 반환
    if not isinstance(power, (int, float)) or power <= 0:
        return str(power)
    
    eok = int(power // 100000000)          # 억 단위
    remainder = int(power % 100000000)
    man = remainder // 10000           # 만 단위
    rest = remainder % 10000           # 나머지
    
    result = []
    if eok > 0:
        result.append(f"{eok}억")
    if man > 0:
        result.append(f"{man:,}만")       # 3자리마다 콤마 추가
    if rest > 0 or (eok == 0 and man == 0):
        result.append(f"{rest:,}")
        
    return " ".join(result)

# [자동 완성 함수]
async def nickname_autocomplete(interaction: discord.Interaction, current: str):
    nicknames = await get_all_nicknames()
    return [
        app_commands.Choice(name=nick, value=nick)
        for nick in nicknames if current.lower() in nick.lower()
    ][:25]

@bot.event
async def on_ready():
    await init_db()
    await bot.tree.sync()
    check_level_up.start()
    print(f"{bot.user} 봇이 온라인 상태이며, 모든 슬래시 명령어와 레벨 알림 기능이 준비되었습니다!")

@tasks.loop(minutes=5)
async def check_level_up():
    alerts = await get_all_alerts()
    for nickname, ocid, old_level in alerts:
        data = await get_character_basic(ocid)
        if data:
            new_level = data.get("character_level")
            if new_level > old_level:
                channel = discord.utils.get(bot.get_all_channels(), name="일반")
                if channel:
                    await channel.send(f"🎉 축하합니다! **{nickname}** 님이 **{new_level}레벨**로 업하셨습니다!")
                await add_alert(nickname, ocid, new_level)

@bot.tree.command(name="캐릭터", description="메이플스토리 캐릭터의 상세 정보와 장비를 조회합니다.")
@app_commands.describe(nickname="조회할 캐릭터의 닉네임")
async def 캐릭터(interaction: discord.Interaction, nickname: str):
    await interaction.response.defer()

    ocid = await get_ocid(nickname)
    if not ocid:
        await interaction.followup.send("캐릭터를 찾을 수 없습니다.")
        return

    basic = await get_character_basic(ocid)
    stat = await get_character_stat(ocid)
    items = await get_character_items(ocid)

    if basic:
        embed = discord.Embed(title=f"캐릭터 정보: {nickname}", color=discord.Color.blue())
        embed.set_image(url=basic.get('character_image'))
        
        embed.add_field(name="레벨", value=basic.get('character_level'), inline=True)
        embed.add_field(name="직업", value=basic.get('character_class'), inline=True)
        embed.add_field(name="길드", value=basic.get('character_guild_name') or "없음", inline=True)
        
        if stat:
            final_stats = stat.get('final_stat', [])
            raw_power = next((item.get('stat_value') for item in final_stats if item.get('stat_name') == '전투력'), '정보 없음')
            
            # [수정] 전투력 숫자를 '억 만' 단위로 변환
            try:
                # API에서 문자열 형태의 숫자로 올 수 있으므로 float/int로 변환 시도
                power_val = float(raw_power)
                power = format_combat_power(power_val)
            except (TypeError, ValueError):
                power = raw_power  # 변환할 수 없는 경우(정보 없음 등) 원래 값 유지
                
            embed.add_field(name="전투력", value=power, inline=False)

        if items:
            item_list = items.get('item_equipment', [])
            equipment_str = "\n".join([f"{i.get('item_equipment_part')}: {i.get('item_name')}" for i in item_list[:5]])
            embed.add_field(name="주요 장비", value=equipment_str or "없음", inline=False)

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("정보를 가져오는 데 실패했습니다.")

@bot.tree.command(name="레벨알림", description="특정 캐릭터의 레벨업 자동 알림을 등록합니다.")
@app_commands.describe(nickname="알림을 등록할 캐릭터의 닉네임")
async def 레벨알림(interaction: discord.Interaction, nickname: str):
    await interaction.response.defer()

    if await is_alert_exists(nickname):
        await interaction.followup.send(f"⚠️ **{nickname}** 님은 이미 레벨알림 설정이 되어 있습니다!")
        return
    
    ocid = await get_ocid(nickname)
    if not ocid:
        await interaction.followup.send("캐릭터를 찾을 수 없습니다.")
        return
    
    data = await get_character_basic(ocid)
    if data:
        level = data.get("character_level")
        await add_alert(nickname, ocid, level)
        await interaction.followup.send(f"✅ **{nickname}** 님의 레벨업 알림이 등록되었습니다. (현재 레벨: {level})")
    else:
        await interaction.followup.send("캐릭터 기본 정보를 불러오지 못했습니다.")

@bot.tree.command(name="알림취소", description="등록된 캐릭터의 레벨업 알림을 취소합니다.")
@app_commands.describe(nickname="알림을 취소할 캐릭터의 닉네임")
@app_commands.autocomplete(nickname=nickname_autocomplete)
async def 알림취소(interaction: discord.Interaction, nickname: str):
    if not await is_alert_exists(nickname):
        await interaction.response.send_message(f"⚠️ **{nickname}** 님은 레벨알림 설정이 되어 있지 않습니다!", ephemeral=True)
        return

    await remove_alert(nickname)
    await interaction.response.send_message(f"❌ **{nickname}** 님의 레벨업 알림을 취소했습니다.")

bot.run(DISCORD_TOKEN)