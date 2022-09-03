from datetime import datetime, timedelta

import requests
import telebot
from bs4 import BeautifulSoup, Tag
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton

token = '1725310174:AAGwJv_i1eBrv0DZdjHQ7GM4tJdgKVRaXu0'
bot = telebot.TeleBot(token=token, parse_mode=None)

total_time = 0  # The total time of all fights
olga_chat_id = 406082320


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: Message):
    markup = ReplyKeyboardMarkup()
    markup.add(KeyboardButton("ufc"))
    bot.send_message(chat_id=message.chat.id, reply_markup=markup, text='choose')


@bot.message_handler(func=lambda message: True)
def all_text(message: Message):
    if message.text.lower() == "ufc":
        bot.send_message(text=parse_latest_fight(), chat_id=message.chat.id, parse_mode='Markdown')
    if message.text.lower() == "ufc":
        bot.send_message(text=parse_latest_fight(), chat_id=message.chat.id, parse_mode='I am working')


def parse_latest_fight() -> str:
    page = 'https://www.ufc.com/events'

    resp = requests.get(page)
    soup = BeautifulSoup(resp.text, features='html.parser')

    past_fight_id, past_fight_date = get_fight_info(soup.select("div.view-display-id-past")[0])
    upcoming_fight_id, upcoming_fight_date = get_fight_info(soup.select("div.view-display-id-upcoming")[0])

    lower_bound = datetime.now() - timedelta(days=3)
    upper_bound = datetime.now() + timedelta(days=3)
    if lower_bound < datetime.strptime(upcoming_fight_date, '%b %d').replace(year=datetime.now().year) < upper_bound:
        return check_fight(upcoming_fight_id[upcoming_fight_id.rindex("#") + 1:])
    elif lower_bound < datetime.strptime(past_fight_date, '%b %d').replace(year=datetime.now().year) < upper_bound:
        return check_fight(past_fight_id[past_fight_id.rindex("#") + 1:])


def get_fight_info(fight: Tag):
    fight_info = fight.select("ul.l-listing__group")[0] \
        .select("li.l-listing__item")[0]
    fight_date = fight_info.select("div.c-card-event--result__date")[0] \
        .contents[1] \
        .contents[0] \
        .split("/")[0].split(",")[1].strip()
    fight_id = fight_info.find_all(lambda tag: tag.name == "a" and "#" in tag["href"])[0] \
        .attrs['href']
    return fight_id, fight_date


def check_fight(fight_id: str) -> str:
    url = f"https://d29dxerjsp82wz.cloudfront.net/api/v3/event/live/{fight_id}.json"
    resp = requests.get(url)

    event = resp.json()['LiveEventDetail']
    name = event['Name']
    event_start_date = datetime.strptime(event['StartTime'], '%Y-%m-%dT%H:%MZ').strftime("%d %b %Y")

    must_watch = []
    for fight in event['FightCard']:
        awarded_fight = is_awarded_fight(fight)
        early_finish = is_early_finish(fight)
        if awarded_fight or early_finish:
            fight_name = get_fight_name(fight)
            fight_length = get_fight_length(fight)
            must_watch.append(f" {fight_length} {fight_name}")
    must_watch_string = '\n'.join(must_watch)
    return f"*{name}, {event_start_date}* \nTotal time: {timedelta(seconds=total_time)}\n{must_watch_string}"


def get_fight_length(fight: dict) -> str:
    global total_time
    result = fight['Result']
    ending_round = result['EndingRound']
    end_time = datetime.strptime(result['EndingTime'], '%M:%S')
    fight_total_time = (ending_round - 1) * 300 + end_time.time().minute * 60 + end_time.time().second
    total_time = total_time + fight_total_time

    if ending_round == 1 or (ending_round == 2 and end_time.minute < 3):
        return '🟢'
    elif ending_round == 2 or (ending_round == 3 and end_time.minute < 3):
        return '🟡'
    elif ending_round is not None and ending_round >= 3:
        return '🔴'


def is_early_finish(fight: dict) -> bool:
    result = fight['Result']
    ending_round = result['EndingRound']
    ending_time = result['EndingTime']
    possible_rounds = fight['RuleSet']['PossibleRounds']

    if ending_time != '5:00' and ending_round != 3:
        return True

    if possible_rounds == 5 and (ending_time != '5:00' and ending_round != 4):
        return True

    return False


def get_fight_name(fight: dict) -> str:
    fighters = fight['Fighters']
    fighter_1 = f"{fighters[0]['Name']['FirstName']} {fighters[0]['Name']['LastName']}"
    fighter_2 = f"{fighters[1]['Name']['FirstName']} {fighters[1]['Name']['LastName']}"
    return f"{fighter_1} vs {fighter_2}"


def is_performance_of_the_night(fight: dict) -> bool:
    fighters = fight['Fighters']
    return fighters[0]['PerformanceOfTheNight'] or fighters[1]['PerformanceOfTheNight']


def is_submission_of_the_night(fight: dict) -> bool:
    fighters = fight['Fighters']
    return fighters[0]['SubmissionOfTheNight'] or fighters[1]['SubmissionOfTheNight']


def is_KO_of_the_night(fight: dict) -> bool:
    fighters = fight['Fighters']
    return fighters[0]['KOOfTheNight'] or fighters[1]['KOOfTheNight']


def is_fight_of_the_night(fight: dict) -> bool:
    return fight['Result']['FightOfTheNight']


def is_awarded_fight(fight: dict) -> bool:
    return is_performance_of_the_night(fight) \
           or is_KO_of_the_night(fight) \
           or is_submission_of_the_night(fight) \
           or is_fight_of_the_night(fight)


def debug():
    return parse_latest_fight()


def start_bot():
    bot.polling(none_stop=True, timeout=60)


if __name__ == '__main__':
    # debug()
    start_bot()
