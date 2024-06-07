import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from catboost import CatBoostClassifier


sex_map = {"Мужской": 1, "Женский": 0}
general_health_map = {
    "Плохо": 0,
    "Хорошо": 1,
    "Очень хорошо": 2,
    "Удовлетворительно": 3,
    "Замечательно": 4,
}
teeth_map = {"Ни одного": 0, "От 1 до 5": 1, "6 и более, то не все": 2, "Все": 3}
yes_no_map = {"Да": 1, "Нет": 0}


params_GeneralHealth = {"mean": 2.0708702385646287, "std": 1.12369567583818}
params_SleepHours = {"mean": 7.02131188189242, "std": 1.4406981630517373}
params_RemovedTeeth = {"mean": 0.6826183982147285, "std": 0.873865538300792}
params_AgeCategory = {"mean": 133197.13791141118, "std": 72450.87773767972}
params_HeightInMeters = {"mean": 1.705150378232045, "std": 0.1066541302436651}
params_WeightInKilograms = {"mean": 83.61552174072102, "std": 21.323231983631334}
params_BMI = {"mean": 28.668258344071237, "std": 6.514005141049461}


def calc_bmi(height, weight):
    return 703 * (weight / (height**2))


def age_category(age):
    if 18 <= age <= 24:
        return 0
    elif 25 <= age <= 29:
        return 1
    elif 30 <= age <= 34:
        return 2
    elif 35 <= age <= 39:
        return 3
    elif 40 <= age <= 44:
        return 4
    elif 45 <= age <= 49:
        return 5
    elif 50 <= age <= 54:
        return 6
    elif 55 <= age <= 59:
        return 7
    elif 60 <= age <= 64:
        return 8
    elif 65 <= age <= 69:
        return 9
    elif 70 <= age <= 74:
        return 10
    elif 75 <= age <= 79:
        return 11
    else:
        return 12


model = CatBoostClassifier()
model.load_model("model.cbm")

with open("config.txt", "r") as config:
    API_TOKEN = config.readline()
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

start_help_cancel_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton('/start'),
    KeyboardButton('/help'),
    KeyboardButton('/cancel')
)
yes_no_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Да"), KeyboardButton("Нет")
)
yes_no_list = ["Да", "Нет"]
w_m_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Мужской"), KeyboardButton("Женский")
)
w_m_list = ["Мужской", "Женский"]
gen_health_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Замечательно"),
    KeyboardButton("Очень хорошо"),
    KeyboardButton("Хорошо"),
    KeyboardButton("Удовлетворительно"),
    KeyboardButton("Плохо"),
)
gen_health_list = [
    "Замечательно",
    "Очень хорошо",
    "Хорошо",
    "Удовлетворительно",
    "Плохо",
]
teeth_kb = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Ни одного"),
    KeyboardButton("От 1 до 5"),
    KeyboardButton("6 и более, но не все"),
    KeyboardButton("Все"),
)
teeth_list = ["Ни одного", "От 1 до 5", "6 и более, но не все", "Все"]


class Form(StatesGroup):
    sex = State()
    general_health = State()
    sleep_hours = State()
    teeth = State()
    had_angina = State()
    had_stroke = State()
    difficulty_walking = State()
    chest_scan = State()
    age = State()
    height = State()
    weight = State()


@dp.message_handler(commands="start")
async def cmd_start(message: types.Message):
    await Form.sex.set()
    await message.answer(
        "Привет! Я бот, который собирает Ваши данные и делает предсказание вероятности сердечного приступа. Начнем?\nВаш пол?",
        reply_markup=w_m_kb,
    )

@dp.message_handler(commands="help")
async def cmd_help(message: types.Message):
    await Form.sex.set()
    await message.answer(
        "Нажмите /start, чтобы начать опрос\nНажмите /cancel, чтобы отменить сбор данных", reply_markup=start_help_cancel_kb
    )


@dp.message_handler(lambda message: message.text in w_m_list, state=Form.sex)
async def process_health(message: types.Message, state: FSMContext):
    await state.update_data(sex=message.text)
    await Form.next()
    await message.answer("Как вы оцениваете свое здоровье?", reply_markup=gen_health_kb)


@dp.message_handler(
    lambda message: message.text in gen_health_list, state=Form.general_health
)
async def process_general_health(message: types.Message, state: FSMContext):
    await state.update_data(general_health=message.text)
    await Form.next()
    await message.answer(
        "Сколько часов Вы спите каждый день в среднем?",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message_handler(state=Form.sleep_hours)
async def process_sleep(message: types.Message, state: FSMContext):
    try:
        hours = float(message.text)
        if hours < 0:
            await message.answer("Пожалуйста, введите корректное значение.")
        await state.update_data(sleep_hours=hours)
        await Form.next()
        await message.answer("Сколько у Вас удалено зубов?", reply_markup=teeth_kb)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное значение.")


@dp.message_handler(lambda message: message.text in teeth_list, state=Form.teeth)
async def process_teeth(message: types.Message, state: FSMContext):
    await state.update_data(teeth=message.text)
    await Form.next()
    await message.answer("Была ли у Вас ангина?", reply_markup=yes_no_kb)


@dp.message_handler(lambda message: message.text in yes_no_list, state=Form.had_angina)
async def process_angina(message: types.Message, state: FSMContext):
    await state.update_data(had_angina=message.text)
    await Form.next()
    await message.answer("Был ли у Вас инсульт?", reply_markup=yes_no_kb)


@dp.message_handler(lambda message: message.text in yes_no_list, state=Form.had_stroke)
async def process_stroke(message: types.Message, state: FSMContext):
    await state.update_data(had_stroke=message.text)
    await Form.next()
    await message.answer(
        "Есть ли у Вас проблемы с передвижением?", reply_markup=yes_no_kb
    )


@dp.message_handler(
    lambda message: message.text in yes_no_list, state=Form.difficulty_walking
)
async def process_difficulty_walking(message: types.Message, state: FSMContext):
    await state.update_data(difficulty_walking=message.text)
    await Form.next()
    await message.answer("Делали ли Вы КТ грудной клетки?", reply_markup=yes_no_kb)


@dp.message_handler(lambda message: message.text in yes_no_list, state=Form.chest_scan)
async def process_chest_scan(message: types.Message, state: FSMContext):
    await state.update_data(chest_scan=message.text)
    await Form.next()
    await message.answer("Сколько Вам лет?", reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=Form.age)
async def process_age(message: types.Message, state: FSMContext):
    try:
        age = float(message.text)
        if age < 0:
            await message.answer("Пожалуйста, введите корректное значение.")
        await state.update_data(age=age)
        await Form.next()
        await message.answer("Какой у Вас рост?", reply_markup=ReplyKeyboardRemove())
    except ValueError:
        await message.answer("Пожалуйста, введите корректное значение.")


@dp.message_handler(state=Form.height)
async def process_height(message: types.Message, state: FSMContext):
    try:
        height = float(message.text)
        if height < 0:
            await message.answer("Пожалуйста, введите корректное значение.")
        await state.update_data(height=height)
        await Form.next()
        await message.answer("Какой у Вас вес?", reply_markup=ReplyKeyboardRemove())
    except ValueError:
        await message.answer("Пожалуйста, введите корректное значение.")


@dp.message_handler(state=Form.weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight < 0:
            await message.answer("Пожалуйста, введите корректное значение.")
        await state.update_data(weight=weight)

        user_data = await state.get_data()
        user_data["sex"] = sex_map.get(user_data["sex"])
        user_data["general_health"] = general_health_map.get(
            user_data["general_health"]
        )
        user_data["teeth"] = teeth_map.get(user_data["teeth"])
        for feature in ["had_angina", "had_stroke", "difficulty_walking", "chest_scan"]:
            user_data[feature] = yes_no_map.get(user_data[feature])
        user_data["bmi"] = calc_bmi(user_data["height"], user_data["weight"])
        user_data["age"] = age_category(user_data["age"])

        data = pd.DataFrame(
            {
                "Sex": [user_data["sex"]],
                "GeneralHealth": [
                    (user_data["general_health"] - params_GeneralHealth["mean"])
                    / params_GeneralHealth["std"]
                ],
                "SleepHours": [
                    (user_data["sleep_hours"] - params_SleepHours["mean"])
                    / params_SleepHours["std"]
                ],
                "RemovedTeeth": [
                    (user_data["teeth"] - params_RemovedTeeth["mean"])
                    / params_RemovedTeeth["std"]
                ],
                "HadAngina": [user_data["had_angina"]],
                "HadStroke": [user_data["had_stroke"]],
                "DifficultyWalking": [user_data["difficulty_walking"]],
                "ChestScan": [user_data["chest_scan"]],
                "AgeCategory": [
                    (user_data["age"] - params_AgeCategory["mean"])
                    / params_AgeCategory["std"]
                ],
                "HeightInMeters": [
                    (user_data["height"] - params_HeightInMeters["mean"])
                    / params_HeightInMeters["std"]
                ],
                "WeightInKilograms": [
                    (user_data["weight"] - params_WeightInKilograms["mean"])
                    / params_WeightInKilograms["std"]
                ],
                "BMI": [(user_data["bmi"] - params_BMI["mean"]) / params_BMI["std"]],
            }
        )

        prediction = model.predict(data)[0]
        prediction_prob = model.predict_proba(data)[0]
        if prediction == 0:
            await message.answer(
                f"Ваши данные собраны. Предсказание модели:\nВам не о чем переживать! У Вас низкая вероятность сердечного приступа: {round(prediction_prob[1], 3)}!\n", reply_markup=start_help_cancel_kb
            )
        if prediction == 1:
            await message.answer(
                f"Ваши данные собраны. Предсказание модели:\nУ Вас высокая вероятность сердечного приступа: {round(prediction_prob[1], 3)}", reply_markup=start_help_cancel_kb
            )

        await state.finish()

    except ValueError:
        await message.answer("Пожалуйста, введите корректное значение.")


@dp.message_handler(commands="cancel", state="*")
@dp.message_handler(lambda message: message.text.lower() == "cancel", state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply(
        "Процесс сбора данных был отменен.", reply_markup=start_help_cancel_kb
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
