from urllib import response

from async_timeout import timeout
from .game_config import *
import asyncio
import time
import discord
import random
from functions.db_game import DB
from discord.ui import Button, View, button, Modal, InputText
from discord import ButtonStyle, Embed

game_records = {}
turn_count = 30
hit_count = 20
seats = 10
end_step = 4

player_init = {}

class Hit_Modal(Modal):
    def __init__(self, text: str, view: View, act: str, max_amount: int) -> None:
        super().__init__(text)
        self.add_item(InputText(label=f"Nicoins (max: {max_amount}, min: 100)", placeholder="Nicoins", value="", style=discord.InputTextStyle.short))
        self.view = view
        self.act = act
        self.max_amount = max_amount
    
    async def callback(self, interaction: discord.Interaction):
        try:
            chips = int(self.children[0].value)
            if chips < 100:
                await interaction.response.send_message("You must bet as least 100 :coin:", delete_after=5)
                return
            elif chips > self.max_amount:
                await interaction.response.send_message(f"The max amount is {self.max_amount} :coin:", delete_after=5)
                return
        except:
            await interaction.response.send_message("You must input a positive integer!", delete_after=5)
            return

        guild_id = str(interaction.guild.id)
        turn = game_records[guild_id]["turn"]

        if game_records[guild_id]["step"] != 2 or game_records[guild_id]["players"][turn]["user_id"] != interaction.user.id:
            await interaction.response.send_message(f"Not your turn.", delete_after=3)
            return
        elif len(game_records[guild_id]["players"][turn]["cards"]) > 2:
            await interaction.response.send_message(f"Invalid command!", delete_after=3)
            return
        else:
            if self.act == "in":
                game_records[guild_id]['players'][turn]["bet"] = "in"
            elif self.act == "big":
                game_records[guild_id]['players'][turn]["bet"] = "big"
            else: # small
                game_records[guild_id]['players'][turn]["bet"] = "small"

            game_records[guild_id]['players'][turn]['bet_amount'] = chips
            game_records[guild_id]['players'][turn]["cards"].append(hit_a_card(game_records[guild_id]['cards']))
            game_records[guild_id]['players'][turn]['revealed'] = True
            cards, result = show_cards(game_records[guild_id]['players'][turn])
            msg = f"<@!{game_records[guild_id]['players'][turn]['user_id']}> shot!\nchips: {chips} ({self.act.upper()})\ncards: {cards}"

            db = DB()
            if result == 0 or (result == 1.1 and self.act == "small") or (result == 1.2 and self.act == "big"):
                game_records[guild_id]["prize"] -= chips
                db.save_guild_pool(guild_id, game_records[guild_id]["prize"])
                b = db.get_balance(interaction.user.id, chips)
                msg += f"\n{game_records[guild_id]['players'][turn]['user_name']} won {chips} :coin:, now has {b} :coin:" 
            elif result == 1 or (result == 1.1 and self.act == "big") or (result == 1.2 and self.act == "small"):
                game_records[guild_id]["prize"] += chips
                db.save_guild_pool(guild_id, game_records[guild_id]["prize"])
                b = db.get_balance(interaction.user.id, chips*-1)
                msg += f"\n{game_records[guild_id]['players'][turn]['user_name']} lost {chips} :coin:, now has {b} :coin:" 
            elif result == 2:
                game_records[guild_id]["prize"] += chips*2
                db.save_guild_pool(guild_id, game_records[guild_id]["prize"])
                b = db.get_balance(interaction.user.id, chips*-2)
                msg += f"\n{game_records[guild_id]['players'][turn]['user_name']} lost {chips} :coin:, now has {b} :coin:" 
            elif result == 3:
                game_records[guild_id]["prize"] += chips*3
                db.save_guild_pool(guild_id, game_records[guild_id]["prize"])
                b = db.get_balance(interaction.user.id, chips*-3)
                msg += f"\n{game_records[guild_id]['players'][turn]['user_name']} lost {chips} :coin:, now has {b} :coin:" 
            db.close()
            await interaction.response.send_message(msg, delete_after=4)
        # self.view.stop()


class LM_View(View):
    @button(label="Show card", style=ButtonStyle.primary, emoji="👀")
    async def show_callback(self, button: discord.Button, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        if game_records.get(guild_id):
            turn = game_records[guild_id]["turn"]
            if game_records[guild_id]["step"] != 2 or game_records[guild_id]["players"][turn]["user_id"] != interaction.user.id:
                await interaction.response.send_message(f"Not your turn.", delete_after=1)
                return
            else:
                cards, points = show_cards(game_records[guild_id]["players"][turn], force_show=True)
                if len(game_records[guild_id]['players'][turn]["cards"]) < 3:
                    if deck_of_card[game_records[guild_id]['players'][turn]["cards"][0]]["r_number"] != deck_of_card[game_records[guild_id]['players'][turn]["cards"][1]]["r_number"]:
                        await interaction.response.send_message(f"Your card is {cards}.\nWhat do you want to do?", ephemeral=True, view=LM_Card_In_View())
                    else:
                        await interaction.response.send_message(f"Your card is {cards}.\nWhat do you want to do?", ephemeral=True, view=LM_Card_UD_View())
                else:
                    await interaction.response.send_message("Invalid command.", delete_after=1, ephemeral=True)
        else:
            await interaction.response.send_message(f"Use command `/lm_start` or `bj!lm_start` to create a game first.", delete_after=1)

class LM_Card_In_View(View):
    def __init__(self) -> None:
        super().__init__(timeout=20)

    @button(label="In", style=ButtonStyle.green, emoji="🥅")
    async def in_callback(self, button: discord.Button, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        turn = game_records[guild_id]["turn"]

        if game_records[guild_id]["step"] != 2 or game_records[guild_id]["players"][turn]["user_id"] != interaction.user.id:
            await interaction.response.send_message(f"Not your turn.", delete_after=2)
            return

        db = DB()
        user_bal = db.query_user_balance(interaction.user.id)
        db.close()
        max_amount  = game_records[guild_id]["prize"] if user_bal > game_records[guild_id]["prize"] else user_bal
        await interaction.response.send_modal(Hit_Modal("How many chips do you want to shoot?", self, "in", max_amount))
        # self.stop()
        
        
    @button(label="Stand", style=ButtonStyle.red, emoji="🛑")
    async def stand_callback(self, button: discord.Button, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        turn = game_records[guild_id]["turn"]

        if game_records[guild_id]["step"] != 2 or game_records[guild_id]["players"][turn]["user_id"] != interaction.user.id:
            await interaction.response.send_message(f"Not your turn.", delete_after=2)
            return
        elif len(game_records[guild_id]["players"][turn]["cards"]) > 2:
            await interaction.response.send_message(f"Invalid command!", delete_after=2)
            return

        turn = game_records[guild_id]["turn"]
        game_records[guild_id]['players'][turn]["cards"].append(-1)
        game_records[guild_id]['players'][turn]['revealed'] = True
        cards, result = show_cards(game_records[guild_id]['players'][turn])
        msg = f"<@!{game_records[guild_id]['players'][turn]['user_id']}> stood!\nchips: 0 :coin:\ncards: {cards}"
        await interaction.response.send_message(content=msg, delete_after=4)

class LM_Card_UD_View(View):
    @button(label="Big", style=ButtonStyle.green, emoji="🔼")
    async def big_callback(self, button: discord.Button, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        turn = game_records[guild_id]["turn"]

        if game_records[guild_id]["step"] != 2 or game_records[guild_id]["players"][turn]["user_id"] != interaction.user.id:
            await interaction.response.send_message(f"Not your turn.", delete_after=2)
            return

        db = DB()
        user_bal = db.query_user_balance(interaction.user.id)
        db.close()
        max_amount  = game_records[guild_id]["prize"] if user_bal > game_records[guild_id]["prize"] else user_bal
        await interaction.response.send_modal(Hit_Modal("How many chips do you want to shoot?", self, "big", max_amount))

    @button(label="Small", style=ButtonStyle.primary, emoji="🔽")
    async def small_callback(self, button: discord.Button, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        turn = game_records[guild_id]["turn"]

        if game_records[guild_id]["step"] != 2 or game_records[guild_id]["players"][turn]["user_id"] != interaction.user.id:
            await interaction.response.send_message(f"Not your turn.", delete_after=2)
            return

        db = DB()
        user_bal = db.query_user_balance(interaction.user.id)
        db.close()
        max_amount  = game_records[guild_id]["prize"] if user_bal > game_records[guild_id]["prize"] else user_bal
        await interaction.response.send_modal(Hit_Modal("How many chips do you want to shoot?", self, "small", max_amount))

    @button(label="Stand", style=ButtonStyle.red, emoji="🛑")
    async def stand_callback(self, button: discord.Button, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        turn = game_records[guild_id]["turn"]

        if game_records[guild_id]["step"] != 2 or game_records[guild_id]["players"][turn]["user_id"] != interaction.user.id:
            await interaction.response.send_message(f"Not your turn.", delete_after=2)
            return
        elif len(game_records[guild_id]["players"][turn]["cards"]) > 2:
            await interaction.response.send_message(f"Invalid command!", delete_after=2)
            return

        turn = game_records[guild_id]["turn"]
        game_records[guild_id]['players'][turn]["cards"].append(-1)
        game_records[guild_id]['players'][turn]['revealed'] = True
        cards, result = show_cards(game_records[guild_id]['players'][turn])
        msg = f"<@!{game_records[guild_id]['players'][turn]['user_id']}> stood!\nchips: 0 :coin:\ncards: {cards}"
        await interaction.response.send_message(content=msg, delete_after=4)

async def game_task(channel, guild_id, m):
    if guild_id in game_records:
        await channel.send("A server can only create a LongMan game in the same time, please wait for the last game has been finished.")
        return
    db = DB()
    game_records[guild_id] = {"players": [], "turn": -1, "message": m, "start_time": int(time.time()), "prize": db.query_guild_pool(guild_id), "step": 0, "record": {}, "cards": [i for i in range(52)]}
    db.close()
    while True:
        if game_records[guild_id]["step"] == 0:
            await step(game_records[guild_id])
        if game_records[guild_id]["step"] == 1:
            await step1(game_records[guild_id])
        if game_records[guild_id]["step"] == 2:
            await step2(game_records[guild_id])
        if game_records[guild_id]["step"] == 3:
            await step3(game_records[guild_id])

        if game_records[guild_id]["step"] == end_step:
            game_records.pop(guild_id)
            break

        await asyncio.sleep(async_delay)

async def step(record):
    time_left = turn_count - (int(time.time()) - record['start_time'])
    time_left = 0 if time_left < 0 else time_left
    embed = discord.Embed()
    embed.type = "rich"
    embed.set_author(name="A LongMan game is started! Use command `bj!lm_join` or `/lm_join` to join this game. ")
    seats_left = seats - len(record["players"])
    embed.set_footer(text=f"The game will start in {time_left} second(s), {seats_left} seats left.")
    embed.colour = discord.Colour.orange() 

    prize = record["prize"]
    embed.add_field(name="Prize Pool", value=f"{prize} :coin:", inline=False)

    for item in record["players"]:
        embed.add_field(name=item["user_name"], value=f"chips: {item['bet_amount']} :coin:\ncards: ", inline=False)

    if time_left <= 0:
        record["step"] += 1

    await record["message"].edit(embed=embed)
    record["message"].embeds[0] = embed

async def step1(record):
    # longman.game_records[channel_id]["players"].append({"user_id": ctx.author.id, "user_name": ctx.author.display_name, "bet_amount": 0, "bet": "", "cards": [], "revealed": False, "result": None})
    embed = discord.Embed()
    embed.type = "rich"
    embed.colour = discord.Colour.orange() 
    content = "Game start!"
    n_players = len(record["players"])

    record['start_time'] = int(time.time()-50)

    prize = record["prize"]
    embed.add_field(name="Prize Pool", value=f"{prize} :coin:", inline=False)

    if n_players == 0:
        record["step"] = end_step
        return
    
    for i, item in enumerate(record["players"]):
        embed.add_field(name=item["user_name"], value=f"chips: {item['bet_amount']} :coin:\ncards: ", inline=False)

    await record["message"].delete()
    # await record["message"].edit(embed=embed, content=content)
    record["message"] = await record["message"].channel.send(embed=embed, content=content)

    for _ in range(2):
        for i in range(n_players):
            await asyncio.sleep(1)
            record["players"][i]["cards"].append(hit_a_card(record["cards"]))
            
            # delete the point finger
            if i == 0:
                ix = n_players - 1
                cards, points = show_cards(record["players"][ix])
                embed.set_field_at(ix+1, name=f"{record['players'][ix]['user_name']}", value=f"chips: {record['players'][ix]['bet_amount']} :coin:\ncards: {cards}", inline=False)
            else:
                ix = i - 1
                cards, points = show_cards(record["players"][ix])
                embed.set_field_at(ix+1, name=f"{record['players'][ix]['user_name']}", value=f"chips: {record['players'][ix]['bet_amount']} :coin:\ncards: {cards}", inline=False)
            
            cards, points = show_cards(record["players"][i])
            embed.set_field_at(i+1, name=f":point_right: {record['players'][i]['user_name']}", value=f"chips: {record['players'][i]['bet_amount']} :coin:\ncards: {cards}", inline=False)
            embed.set_author(name=f"It's {record['players'][i]['user_name']}'s turn.")
            content = f"<@!{record['players'][i]['user_id']}> got {cards}"
            await record["message"].edit(embed=embed, content=content)

    await asyncio.sleep(1)
    embed.set_field_at(n_players, name=f"{record['players'][n_players - 1]['user_name']}", value=f"chips: {record['players'][n_players - 1]['bet_amount']} :coin:\ncards: {cards}", inline=False)
    await record["message"].edit(embed=embed, content=None)
    record["message"].embeds[0] = embed

    record["step"] += 1

async def step2(record):
    # await record["message"].edit(view=LM_View())

    for i, p in enumerate(record["players"]):
        record['turn'] = i
        cards, result = show_cards(p)

        record["message"].embeds[0].set_field_at(i+1, name=f":point_right: {record['players'][i]['user_name']}", value=f"chips: {record['players'][i]['bet_amount']} :coin:\ncards: {cards}", inline=False)
        await record["message"].edit(embed=record["message"].embeds[0], content=f"{p['user_name']}'s turn.")

        if record.get("message2"):
            await record["message2"].delete()
            
        # record["message2"] = await record["message"].channel.send(f"It's <@!{record['players'][i]['user_id']}>'s turn.", view=LM_View())
        cards, points = show_cards(p, force_show=True)
        if deck_of_card[p["cards"][0]]["r_number"] != deck_of_card[p["cards"][1]]["r_number"]:
            record["message2"] = await record["message"].channel.send(f"<@!{p['user_id']}> card is {cards}.\nWhat do you want to do?", view=LM_Card_In_View())
        else:
            record["message2"] = await record["message"].channel.send(f"<@!{p['user_id']}> card is {cards}.\nWhat do you want to do?", view=LM_Card_UD_View())

        record['start_time'] = int(time.time())
        while True:
            if p["revealed"]:
                time_left = 5 - (int(time.time()) - record['start_time'])
                time_left = 0 if time_left < 0 else time_left
                msg = f"<@!{record['players'][i]['user_id']}>'s turn is over.Left {time_left} second(s) for next player."
            else:
                time_left = hit_count - (int(time.time()) - record['start_time'])
                time_left = 0 if time_left < 0 else time_left
                msg = f"<@!{record['players'][i]['user_id']}>'s turn.\nClick \"Show card\" to see your cards.\nYou left {time_left} second(s)."

            await record["message"].edit(content=msg)   
            await record["message2"].edit(content=f"<@!{p['user_id']}> card is {cards}.\nWhat do you want to do?\nYou left {time_left} second(s).")         
                
            bet_str = f"({record['players'][i]['bet'].upper()})" if record['players'][i]['bet'] != "" else ""
            record["message"].embeds[0].set_field_at(i+1, name=f":point_right: {record['players'][i]['user_name']}", value=f"chips: {record['players'][i]['bet_amount']} :coin: {bet_str}\ncards: {cards}", inline=False)
            # await record["message"].edit(embed=record["message"].embeds[0], content=f"{record['players'][i]['user_name']}'s turn.")
            await record["message"].edit(embed=record["message"].embeds[0])

            await asyncio.sleep(0.8)
            if time_left <= 0:
                cards, result = show_cards(p)
                bet_str = f"({record['players'][i]['bet'].upper()})" if record['players'][i]['bet'] != "" else ""
                record["message"].embeds[0].set_field_at(0, name="Prize Pool", value=f"{record['prize']} :coin:", inline=False)
                record["message"].embeds[0].set_field_at(i+1, name=f"{record['players'][i]['user_name']}", value=f"chips: {record['players'][i]['bet_amount']} :coin: {bet_str}\ncards: {cards}", inline=False)
                await record["message"].edit(embed=record["message"].embeds[0])
                break

        if record['prize'] == 0:
            embed = discord.Embed()
            embed.colour = discord.Colour.red()
            if record["message"].guild.icon:
                embed.set_author(name=f"The server's prize pool is empty.", icon_url=record["message"].guild.icon.url)
            else:
                embed.set_author(name=f"The server's prize pool is empty.")
            # await record["message"].channel.send(f"The server's prize pool is empty.")
            await record["message"].channel.send(embed=embed)
            break

    await record["message2"].delete()
    await record["message"].edit(content="")
    record["step"] += 1

async def step3(record):
    await asyncio.sleep(1)

    content = "LongMan Result:"
    embed = embed=record["message"].embeds[0]
    embed.set_field_at(0, name="Prize Pool", value=f"{record['prize']} :coin:", inline=False)

    await record["message"].delete()
    await record["message"].channel.send(content=content, embed=embed)

    record["step"] += 1


def show_cards(player, force_show=False):
    now_cards = ""
    cards_rnum = []
    result = None
    for i, card in enumerate(player["cards"]):
        if player["revealed"] or force_show:
            if i < 2:
                now_cards += f"|:{deck_of_card[card]['suit']}:{deck_of_card[card]['number']}| "
                cards_rnum.append(deck_of_card[card]['r_number'])
            else:
                if card != -1:
                    now_cards += f", shot: |:{deck_of_card[card]['suit']}:{deck_of_card[card]['number']}| "
                    cards_rnum.append(deck_of_card[card]['r_number'])

                    if cards_rnum[0] != cards_rnum[1]:
                        if cards_rnum[0] == cards_rnum[2] or cards_rnum[1] == cards_rnum[2]:
                            result = 2
                            now_cards += "\nresult: HIT!!!"
                            now_cards += f" Lost {player['bet_amount']*2} :coin:"
                        elif cards_rnum[0] > cards_rnum[2] > cards_rnum[1] or cards_rnum[0] < cards_rnum[2] < cards_rnum[1]:
                            result = 0
                            now_cards += "\nresult: IN!!!"
                            now_cards += f" Won {player['bet_amount']} :coin:"
                        else:
                            result = 1
                            now_cards += "\nresult: OUT!!!"
                            now_cards += f" Lost {player['bet_amount']} :coin:"
                    else:
                        if cards_rnum[0] == cards_rnum[2]:
                            result = 3
                            now_cards += "\nresult: HIT!!!"
                            now_cards += f" Lost {player['bet_amount']*3} :coin:"
                        elif cards_rnum[2] > cards_rnum[0]:
                            result = 1.2
                            now_cards += "\nresult: BIG!!!"
                            if player["bet"] == "big":
                                now_cards += f" Won {player['bet_amount']} :coin:"
                            else:
                                now_cards += f" Lost {player['bet_amount']} :coin:"
                        else:
                            result = 1.1
                            now_cards += "\nresult: SMALL!!!"
                            if player["bet"] == "small":
                                now_cards += f" Won {player['bet_amount']} :coin:"
                            else:
                                now_cards += f" Lost {player['bet_amount']} :coin:"
                else:
                    # now_cards += f"\nshot: |:regional_indicator_x:| "
                    now_cards += f", shot: |:x:| "
                    now_cards += "\nresult: N/A"
        else:
            now_cards += "|:question:| "

    return now_cards, result

def hit_a_card(cards: list):
    rand_num = random.randint(0, len(cards)-1)
    hit = cards.pop(rand_num)
    # card = f"|:{deck_of_card[hit]['suit']}:{deck_of_card[hit]['number']}| "
    return hit