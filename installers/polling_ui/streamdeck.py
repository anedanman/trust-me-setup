import time

from PIL import ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from ui import create_ui, get_questions
from drivers import set_drivers

poll_names = [
    "emotions",
    "engagement",
    "low_fatigue",
    "physical_comfort",
    # "sufficient_sleep",
    "workplace_interactions",
    "stress",
    # "productivity"
]


def create_text_img(text, deck):
    image = PILHelper.create_image(deck)

    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except IOError:
        font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_pos = ((image.width - text_width) // 2, (image.height - text_height) // 2)

    draw.text(text_pos, text, font=font, fill="white")

    return PILHelper.to_native_format(deck, image)


def set_button_text(deck, key, text):
    image = create_text_img(text, deck)
    deck.set_key_image(key, image)


def open_poll(poll):
    questions = get_questions(poll)
    create_ui(questions)

    time.sleep(1)


def key_press(deck, key, state):
    if state:
        poll = poll_names[key]
        open_poll(poll)


def streamdeck_listener():
    streamdecks = DeviceManager().enumerate()

    if not streamdecks:
        print("Cannot find StreamDeck...")
        return None

    for deck in streamdecks:
        deck.open()
        deck.reset()
        deck.set_brightness(90)

        for i, poll_name in enumerate(poll_names):
            if i == 0:
                text = "Emotions"
            elif i == 1:
                text = "Engagement"
            elif i == 2:
                text = "Fatigue"
            elif i == 3:
                text = "Comfort"
            elif i == 4:
                text = "Interactions"
            elif i == 5:
                text = "Stress"
            set_button_text(deck, i, text)
        # Register callback
        deck.set_key_callback(key_press)

    return streamdecks


if __name__ == "__main__":
    set_drivers()

    streamdecks = streamdeck_listener()

    if streamdecks:
        try:
            while True:
                # Poll for StreamDeck events
                for deck in streamdecks:
                    deck._read()
                # Add a short sleep to avoid busy-waiting
                time.sleep(0.1)
        except KeyboardInterrupt:
            for deck in streamdecks:
                deck.close()
